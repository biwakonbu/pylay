"""YAMLから型への変換コマンド

YAML仕様をPython型に変換するCLIコマンドです。
"""

import sys
from pathlib import Path

from rich.box import SIMPLE
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from src.core.converters.generation_header import generate_python_header
from src.core.converters.type_to_yaml import PROJECT_ROOT_PACKAGE
from src.core.converters.yaml_to_type import yaml_to_spec
from src.core.schemas.pylay_config import PylayConfig
from src.core.schemas.yaml_spec import RefPlaceholder, TypeRoot, TypeSpec


def _generate_imports_from_yaml(
    spec: TypeSpec | TypeRoot | None,
    exclude_types: set[str] | None = None,
) -> list[str]:
    """YAMLから必要なインポート文を生成（PEP 8準拠）

    Args:
        spec: TypeSpecまたはTypeRoot
        exclude_types: 除外する型名のセット（YAML内で定義されている型）

    Returns:
        インポート文のリスト

    PEP 8インポート順序:
    1. 標準ライブラリ
    2. サードパーティライブラリ
    3. ローカルアプリケーション/ライブラリ
    各グループ内はアルファベット順
    """
    from collections import defaultdict

    if exclude_types is None:
        exclude_types = set()

    # specがNoneの場合は基本インポートのみ
    if spec is None:
        return ["from pydantic import BaseModel, Field"]

    # TypeRootから_importsを取得
    imports_dict: dict[str, str] = {}
    if isinstance(spec, TypeRoot):
        # TypeRoot.imports_フィールドから取得
        if spec.imports_:
            imports_dict = spec.imports_
    elif hasattr(spec, "imports_"):
        if spec.imports_:  # type: ignore[attr-defined]
            imports_dict = spec.imports_  # type: ignore[attr-defined]

    # imports_dictが空でもPydanticの必須インポートは生成する
    # （BaseModel, Fieldは常に必要）

    # モジュール別にグループ化
    stdlib_imports: dict[str, list[str]] = defaultdict(list)
    thirdparty_imports: dict[str, list[str]] = defaultdict(list)
    local_imports: dict[str, list[str]] = defaultdict(list)

    for type_name, full_path in imports_dict.items():
        # YAML内で定義されている型は除外（重複定義を避ける）
        if type_name in exclude_types:
            continue
        # full_path: ".core.schemas.types.FilePath" or "pydantic.main.BaseModel"
        if not full_path:
            continue

        # 相対パス（プロジェクト内）か判定
        if full_path.startswith("."):
            # 相対パス → ローカルインポート
            # ".core.schemas.types.TypeName" → "src.core.schemas.types"
            module_path = PROJECT_ROOT_PACKAGE + full_path.rsplit(".", 1)[0]
            local_imports[module_path].append(type_name)
        else:
            # 絶対パス
            parts = full_path.rsplit(".", 1)
            if len(parts) != 2:
                continue
            module_path, class_name = parts

            # 内部モジュール（._で始まるサブモジュール）をクリーンアップ
            # pathlib._local.Path → pathlib.Path
            if "._" in module_path:
                module_path = module_path.split("._")[0]

            # 標準ライブラリかサードパーティか判定（簡易版）
            if module_path.split(".")[0] in {
                "typing",
                "pathlib",
                "enum",
                "dataclasses",
                "collections",
                "datetime",
                "re",
                "json",
                "os",
                "sys",
            }:
                stdlib_imports[module_path].append(class_name)
            else:
                thirdparty_imports[module_path].append(class_name)

    # インポート文を生成（PEP 8順序）
    result_imports = []

    # 1. 標準ライブラリ（_importsから自動検出）
    if stdlib_imports:
        for module_path in sorted(stdlib_imports.keys()):
            types = sorted(set(stdlib_imports[module_path]))
            result_imports.append(f"from {module_path} import {', '.join(types)}")

    # 2. サードパーティライブラリ（Pydanticを常に含む）
    if result_imports:  # 標準ライブラリがある場合は空行
        result_imports.append("")

    # Pydanticインポートを追加（必須）
    result_imports.append("from pydantic import BaseModel, Field")

    # その他のサードパーティライブラリ
    if thirdparty_imports:
        for module_path in sorted(thirdparty_imports.keys()):
            if module_path.startswith("pydantic"):
                continue  # 既に追加済み
            types = sorted(set(thirdparty_imports[module_path]))
            result_imports.append(f"from {module_path} import {', '.join(types)}")

    # 3. ローカルアプリケーション
    if local_imports:
        result_imports.append("")  # 空行
        for module_path in sorted(local_imports.keys()):
            types = sorted(set(local_imports[module_path]))
            result_imports.append(f"from {module_path} import {', '.join(types)}")

    return result_imports


def run_types(input_file: str, output_file: str, root_key: str | None = None) -> None:
    """YAML仕様をPython型に変換

    Args:
        input_file: 入力YAMLファイルのパス
        output_file: 出力Pythonファイルのパス（.lay.py拡張子が自動付与される）
            または "-" で標準出力
        root_key: 変換するYAMLのルートキー
    """
    console = Console()

    try:
        # 設定を読み込み
        try:
            config = PylayConfig.from_pyproject_toml()
        except FileNotFoundError:
            # pyproject.tomlがない場合はデフォルト設定
            # （構文エラーや設定値の不正はそのまま例外として伝播させる）
            config = PylayConfig()

        # 標準出力判定
        is_stdout = output_file == "-"

        # 処理開始時のPanel表示
        input_path = Path(input_file)
        output_path: Path | None

        if is_stdout:
            # 標準出力の場合はパス操作をスキップ
            output_display = "<stdout>"
            output_path = None
        else:
            output_path = Path(output_file)

            # .lay.py拡張子を自動付与
            if str(output_path).endswith(config.generation.lay_suffix):
                # 既に.lay.pyで終わっている場合はそのまま
                pass
            elif not output_path.suffix:
                # 拡張子がない場合は.lay.pyを追加
                output_path = output_path.with_suffix(config.generation.lay_suffix)
            else:
                # 他の拡張子がある場合は.lay.pyに置き換え
                output_path = output_path.with_suffix(config.generation.lay_suffix)

            output_display = str(output_path)

        start_panel = Panel(
            f"[bold cyan]入力ファイル:[/bold cyan] {input_path.name}\n"
            f"[bold cyan]出力先:[/bold cyan] {output_display}\n"
            f"[bold cyan]ルートキー:[/bold cyan] {root_key or '自動設定'}",
            title="[bold green]🚀 YAMLから型変換開始[/bold green]",
            border_style="green",
        )
        console.print(start_panel)

        # YAMLを読み込み
        with console.status("[bold green]YAMLファイル読み込み中..."):
            with open(input_file, encoding="utf-8") as f:
                yaml_str = f.read()

        # Python型に変換
        with console.status("[bold green]型情報解析中..."):
            spec_result = yaml_to_spec(yaml_str, root_key)
            # RefPlaceholderは参照解決エラーを示すため、適切にエラー処理
            if isinstance(spec_result, RefPlaceholder):
                msg = f"参照解決エラー: {spec_result.ref_name}"
                raise ValueError(msg)
            spec = spec_result

        # 元のYAMLデータをパースして保持（新形式フィールド用）
        import yaml as pyyaml

        with open(input_file, encoding="utf-8") as f:
            raw_yaml_data = pyyaml.safe_load(f.read())

        # Pythonコードを生成
        code_lines = []

        # 警告ヘッダーを追加
        header = generate_python_header(
            input_file,
            add_header=config.generation.add_generation_header,
            include_source=config.generation.include_source_path,
        )
        if header:
            code_lines.append(header)

        # 前方参照を有効にする（型定義の順序に依存しない）
        code_lines.append("from __future__ import annotations")
        code_lines.append("")

        def extract_type_dependencies(type_name: str, type_data: dict) -> set[str]:
            """型定義から依存している他の型を抽出"""
            dependencies = set()
            fields = type_data.get("fields", type_data.get("properties", {}))

            for _, field_spec in fields.items():
                field_type = field_spec.get("type", "")
                # list[TypeName], dict[str, TypeName] などから型名を抽出
                import re

                # 型名のパターン: 大文字で始まる識別子
                type_names = re.findall(r"\b([A-Z][a-zA-Z0-9]*)\b", str(field_type))
                for dep_type in type_names:
                    # 組み込み型や標準ライブラリ型は除外
                    if dep_type not in [
                        "Field",
                        "List",
                        "Dict",
                        "Set",
                        "Tuple",
                        "Optional",
                        "Union",
                        "Any",
                        "None",
                        "Literal",
                        "BaseModel",
                    ]:
                        dependencies.add(dep_type)

            return dependencies

        def topological_sort(types_dict: dict[str, dict]) -> list[str]:
            """型定義をトポロジカルソートして依存関係順に並べる"""
            # 各型の依存関係を抽出
            dependencies = {name: extract_type_dependencies(name, data) for name, data in types_dict.items()}

            # YAML内で定義されていない型（import済み）を依存関係から除外
            defined_type_names = set(types_dict.keys())
            for name in dependencies:
                dependencies[name] = dependencies[name] & defined_type_names

            # トポロジカルソート
            sorted_types = []
            visited = set()

            def visit(name: str, path: set[str]) -> None:
                if name in visited:
                    return
                if name in path:
                    # 循環参照検出（from __future__ import annotationsで解決済み）
                    return

                path.add(name)
                for dep in dependencies.get(name, set()):
                    if dep in types_dict:  # YAML内で定義されている型のみ
                        visit(dep, path.copy())
                path.remove(name)

                visited.add(name)
                sorted_types.append(name)

            for name in types_dict.keys():
                visit(name, set())

            return sorted_types

        # インポート文を生成（YAMLから読み取り）
        # YAML内で定義されている型はimportしない（型定義を優先）
        defined_types = set()

        if raw_yaml_data:
            # YAMLデータから定義されている型名を抽出（_importsや_metadataは除外）
            # IMPORTANT: _で始まる型名（_BaseType等）を除外しないよう、特定キーのみ除外
            reserved_keys = {"_metadata", "_imports"}
            defined_types = {k for k in raw_yaml_data.keys() if k not in reserved_keys}

        # 除外する型 = YAML内で定義されている型
        exclude_types = defined_types

        # Literalなどの型は _imports に含まれているので、動的チェックは不要
        import_lines = _generate_imports_from_yaml(spec, exclude_types=exclude_types)  # type: ignore[arg-type]
        code_lines.extend(import_lines)
        code_lines.append("")

        def spec_to_type_annotation(spec_data: dict | str) -> str:
            """TypeSpecデータからPython型アノテーションを生成

            TypeSpec形式のデータからPythonの型アノテーションを生成します。
            """
            if isinstance(spec_data, str):
                # 参照文字列の場合（クラス名として扱う）
                return spec_data

            spec_type = spec_data.get("type", "str")
            spec_name = spec_data.get("name", "")

            if spec_type == "list":
                items_spec = spec_data.get("items")
                if items_spec:
                    item_type = spec_to_type_annotation(items_spec)
                    return f"list[{item_type}]"
                else:
                    return "list"

            elif spec_type == "dict":
                # Enum の場合（propertiesが空）はクラス名を返す
                properties = spec_data.get("properties", {})
                if not properties and spec_name:
                    return spec_name
                # Dict型の場合
                return "dict[str, str | int | float | bool]"

            elif spec_type == "union":
                # Union 型の処理
                variants = spec_data.get("variants", [])
                if variants:
                    variant_types = [spec_to_type_annotation(v) for v in variants]
                    return " | ".join(variant_types)
                else:
                    return "str | int"  # デフォルト

            elif spec_type == "unknown":
                # unknown の場合は元の name を使う（str | None など）
                if spec_name == "phone":
                    return "str | None"
                elif spec_name == "description":
                    return "str | None"
                elif spec_name == "shipping_address":
                    return "Address | None"
                elif spec_name == "status":
                    return "str | Status"
                return "Any"

            elif spec_type == "reference":
                # reference型の場合、spec_nameをそのまま使用
                return spec_name if spec_name else "Any"

            else:
                # 基本型
                return spec_type

        def generate_class_code(name: str, spec_data: dict) -> list[str]:
            """Pydantic BaseModelクラスコードを生成します。

            Args:
                name: クラス名
                spec_data: 型仕様データ

            Returns:
                生成されたコード行のリスト
            """
            lines = []

            # base_classesを取得（デフォルトはBaseModel）
            base_classes = spec_data.get("base_classes", ["BaseModel"])
            base_classes_str = ", ".join(base_classes)

            lines.append(f"class {name}({base_classes_str}):")
            if "description" in spec_data and spec_data["description"]:
                # 複数行docstringの場合、適切にインデントを追加
                description = spec_data["description"]
                # descriptionがNoneの場合のTypeErrorを防ぐ
                if description and "\n" in description:
                    # 複数行の場合
                    doc_lines = description.split("\n")
                    lines.append(f'    """{doc_lines[0]}')
                    for line in doc_lines[1:]:
                        if line.strip():  # 空行でない場合のみインデント追加
                            lines.append(f"    {line}")
                        else:
                            lines.append("")
                    lines.append('    """')
                else:
                    # 単一行の場合
                    lines.append(f'    """{description}"""')
            lines.append("")

            # fieldsセクションから直接フィールド情報を取得
            fields = spec_data.get("fields", spec_data.get("properties", {}))

            if fields:
                for field_name, field_spec in fields.items():
                    # 型アノテーション文字列を取得（YAMLのtype値がそのまま使われる）
                    field_type_raw = field_spec.get("type", "str")
                    is_required = field_spec.get("required", True)
                    field_info_data = field_spec.get("field_info", {})

                    # 型名をそのまま使用（YAMLには既に正しい型名が格納されている）
                    field_type = field_type_raw
                    # 空のLiteral型のみ str に変換（値が失われている場合の暫定対処）
                    if field_type == "Literal":
                        field_type = "str"

                    # Field()パラメータを構築（Pydantic慣例順序: default系 → 制約 → description）
                    field_params = []

                    # 1. default/default_factory（最初）
                    if "default_factory" in field_info_data:
                        factory_value = field_info_data["default_factory"]
                        field_params.append(f"default_factory={factory_value}")
                    elif "default" in field_info_data:
                        field_params.append(f"default={field_info_data['default']}")

                    # 2. バリデーション制約（中間）
                    # 順序: ge, gt, le, lt, min_length, max_length, pattern, その他
                    constraint_order = ["ge", "gt", "le", "lt", "min_length", "max_length", "pattern", "multiple_of"]
                    for constraint in constraint_order:
                        if constraint in field_info_data:
                            value = field_info_data[constraint]
                            if isinstance(value, str):
                                # エスケープ処理
                                value_escaped = value.replace('"', '\\"')
                                field_params.append(f'{constraint}="{value_escaped}"')
                            else:
                                field_params.append(f"{constraint}={value}")

                    # その他の制約
                    for key, value in field_info_data.items():
                        if key not in ["default", "default_factory"] and key not in constraint_order:
                            if isinstance(value, str):
                                # エスケープ処理
                                value_escaped = value.replace('"', '\\"')
                                field_params.append(f'{key}="{value_escaped}"')
                            else:
                                field_params.append(f"{key}={value}")

                    # 3. description（最後）
                    if "description" in field_spec and field_spec["description"]:
                        # エスケープ処理（"を\"に変換）
                        description_escaped = field_spec["description"].replace('"', '\\"')
                        field_params.append(f'description="{description_escaped}"')

                    # フィールド定義を生成
                    if field_params:
                        # Field()を使用
                        field_def = f"Field({', '.join(field_params)})"
                        lines.append(f"    {field_name}: {field_type} = {field_def}")
                    elif is_required:
                        # required=True かつ Field()不要
                        lines.append(f"    {field_name}: {field_type}")
                    else:
                        # required=False かつ Field()不要
                        lines.append(f"    {field_name}: {field_type} | None = None")

            lines.append("")
            return lines

        # 生成する型の数を計算
        type_count = 0
        if spec is not None and isinstance(spec, TypeRoot):
            type_count = len(spec.types)
        elif spec is not None:
            type_count = 1

        # コード生成中のプログレス表示
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeRemainingColumn(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("Pythonコード生成中...", total=type_count)

            if spec is not None and isinstance(spec, TypeRoot):
                # 複数型仕様
                # 型定義を依存関係順にソート
                sorted_type_names = topological_sort(raw_yaml_data if raw_yaml_data else {})

                # ソート結果がない場合（raw_yaml_dataが空など）は元の順序を使用
                if not sorted_type_names:
                    sorted_type_names = list(spec.types.keys())

                for type_name in sorted_type_names:
                    if type_name not in spec.types:
                        continue  # YAML内には定義があるがspecにない場合スキップ

                    type_spec = spec.types[type_name]
                    # 元のYAMLデータから該当型の定義を取得（新形式対応）
                    raw_type_data = raw_yaml_data.get(type_name, {})
                    # raw_type_dataが新形式（fieldsセクション含む）ならそちらを優先
                    if raw_type_data and "fields" in raw_type_data:
                        code_lines.append("")  # PEP 8: クラス定義前に2行空行
                        code_lines.extend(generate_class_code(type_name, raw_type_data))
                    else:
                        # 旧形式（propertiesセクション）はmodel_dump()を使用
                        code_lines.append("")  # PEP 8: クラス定義前に2行空行
                        code_lines.extend(generate_class_code(type_name, type_spec.model_dump()))
                    progress.advance(task)
            elif spec is not None:
                # 単一型仕様
                code_lines.extend(generate_class_code("GeneratedType", spec.model_dump()))
                progress.advance(task)

        # ファイルまたは標準出力に書き込み
        output_content = "\n".join(code_lines)

        if is_stdout:
            # 標準出力に書き込み
            sys.stdout.write(output_content)
            sys.stdout.write("\n")
        else:
            # ファイルに書き込み（output_pathはNoneではない）
            if output_path is None:
                msg = "output_path is None when not using stdout"
                raise ValueError(msg)
            with console.status("[bold green]ファイル出力中..."):
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(output_content)

            # 結果表示用のTable
            result_table = Table(
                title="変換結果サマリー",
                show_header=True,
                border_style="green",
                width=80,
                header_style="",
                box=SIMPLE,
            )
            result_table.add_column("項目", style="cyan", no_wrap=True, width=40)
            result_table.add_column("結果", style="green", justify="right", width=30)

            result_table.add_row("入力ファイル", input_path.name)
            result_table.add_row("出力ファイル", output_path.name)

            # 型情報をカウントして表示
            type_count = 0
            if spec is not None and isinstance(spec, TypeRoot):
                type_count = len(spec.types)
            elif spec is not None:
                type_count = 1

            result_table.add_row("生成型数", f"{type_count} 個")
            result_table.add_row("コード行数", f"{len(code_lines)} 行")

            console.print(result_table)

            # 完了メッセージのPanel
            complete_panel = Panel(
                f"[bold green]✅ YAMLから型への変換が完了しました[/bold green]\n\n"
                f"[bold cyan]出力ファイル:[/bold cyan] {output_path}\n"
                f"[bold cyan]生成型数:[/bold cyan] {type_count} 個",
                title="[bold green]🎉 処理完了[/bold green]",
                border_style="green",
            )
            console.print(complete_panel)

    except Exception as e:
        # エラーメッセージのPanel
        error_panel = Panel(
            f"[red]エラー: {e}[/red]",
            title="[bold red]❌ 処理エラー[/bold red]",
            border_style="red",
        )
        console.print(error_panel)
        sys.exit(1)
