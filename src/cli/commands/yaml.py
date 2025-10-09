"""型からYAMLへの変換コマンド

Pythonの型定義をYAML形式に変換するCLIコマンドです。
"""

import importlib
import importlib.metadata
import sys
from datetime import UTC
from enum import Enum
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

from src.core.converters.generation_header import generate_yaml_header
from src.core.converters.type_to_yaml import (
    PROJECT_ROOT_PACKAGE,
    types_to_yaml_simple,
)
from src.core.schemas.pylay_config import PylayConfig


def _path_to_module_path(file_path: Path) -> str | None:
    """ファイルパスからPythonモジュールパスを構築

    Args:
        file_path: Pythonファイルのパス

    Returns:
        モジュールパス（例: "src.core.analyzer.models"）、変換できない場合はNone
    """
    try:
        # 絶対パスに変換
        abs_path = file_path.resolve()

        # プロジェクトルートを見つける（src/が含まれる最初のパス）
        parts = abs_path.parts
        if PROJECT_ROOT_PACKAGE not in parts:
            return None

        # srcから始まるパスを抽出
        src_index = parts.index(PROJECT_ROOT_PACKAGE)
        module_parts = parts[src_index:]

        # .pyを除去
        if module_parts[-1].endswith(".py"):
            module_parts_list = list(module_parts[:-1]) + [module_parts[-1][:-3]]
            module_parts = tuple(module_parts_list)

        return ".".join(module_parts)
    except (ValueError, IndexError):
        return None


def _has_type_definitions(file_path: Path) -> bool:
    """ファイルに型定義が含まれているかチェック

    以下の型定義構文を検出:
    - BaseModel (Pydantic)
    - type文（型エイリアス）
    - NewType
    - dataclass
    - Enum

    Args:
        file_path: チェック対象のPythonファイル

    Returns:
        型定義が含まれている場合True
    """
    try:
        import re

        # ファイルを読み込んで型定義構文をチェック
        content = file_path.read_text(encoding="utf-8")

        # 1. BaseModel
        has_basemodel = (
            ("from pydantic import" in content and "BaseModel" in content)
            or "from pydantic.main import BaseModel" in content
        ) and "class " in content

        # 2. type文（型エイリアス）
        # 例: type UserId = str, type Alias[T] = dict[str, T]
        has_type_alias = bool(re.search(r"^type\s+\w+(?:\[[^\]]+\])?\s*=", content, re.MULTILINE))

        # 3. NewType
        # 例: UserId = NewType('UserId', str)
        has_newtype = "NewType" in content and "NewType(" in content

        # 4. dataclass
        # 例: @dataclass class User:
        has_dataclass = "@dataclass" in content

        # 5. Enum
        # 例: class Status(Enum):
        has_enum = "Enum" in content and "class " in content

        return any([has_basemodel, has_type_alias, has_newtype, has_dataclass, has_enum])
    except Exception:
        return False


def _find_python_files_with_type_definitions(directory: Path) -> list[Path]:
    """ディレクトリ内の型定義を含むPythonファイルを再帰的に検索

    Args:
        directory: 検索対象のディレクトリ

    Returns:
        型定義を含むPythonファイルのリスト
    """
    python_files = []

    for py_file in directory.rglob("*.py"):
        # テストファイルや__pycache__は除外
        if py_file.name.startswith("test_") or "__pycache__" in str(py_file) or py_file.name == "__init__.py":
            continue

        if _has_type_definitions(py_file):
            python_files.append(py_file)

    return python_files


def _find_python_files_in_directory_only(directory: Path) -> list[Path]:
    """ディレクトリ直下のPythonファイルのみを検索（サブディレクトリは除外）

    Args:
        directory: 検索対象のディレクトリ

    Returns:
        型定義を含むPythonファイルのリスト（直下のみ）
    """
    python_files = []

    for py_file in directory.glob("*.py"):
        # テストファイルは除外
        if py_file.name.startswith("test_") or py_file.name == "__init__.py":
            continue

        if _has_type_definitions(py_file):
            python_files.append(py_file)

    return python_files


def _find_all_subdirectories(directory: Path) -> list[Path]:
    """ディレクトリ内の全サブディレクトリを取得（再帰的）

    Args:
        directory: 検索対象のディレクトリ

    Returns:
        サブディレクトリのリスト（自身も含む）
    """
    directories = [directory]

    for item in directory.rglob("*"):
        if item.is_dir() and "__pycache__" not in str(item) and "tests" not in str(item):
            directories.append(item)

    return sorted(directories)


def _calculate_file_hash(file_path: Path) -> str:
    """ファイルのSHA256ハッシュ値を計算

    Args:
        file_path: ハッシュ計算対象のファイル

    Returns:
        SHA256ハッシュ値（16進数文字列）
    """
    import hashlib

    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # ファイルをチャンク単位で読み込んでハッシュ計算
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def _validate_metadata(source_file: str, generated_at: str, pylay_version: str) -> list[str]:
    """メタデータのバリデーション

    Args:
        source_file: ソースファイルのパス
        generated_at: 生成時刻（ISO形式）
        pylay_version: pylayバージョン

    Returns:
        バリデーションエラーのリスト（空の場合は正常）
    """
    from datetime import datetime

    errors = []

    # ソースファイルの存在確認
    if not Path(source_file).exists():
        errors.append(f"Source file does not exist: {source_file}")

    # 生成時刻の形式チェック
    try:
        datetime.fromisoformat(generated_at)
    except ValueError:
        errors.append(f"Invalid generated_at format: {generated_at}")

    # バージョン形式の簡易チェック
    if not pylay_version:
        errors.append("pylay_version is empty")

    return errors


def _generate_metadata_section(source_file: str, validate: bool = True) -> str:
    """YAMLメタデータセクションを生成

    Args:
        source_file: ソースファイルのパス
        validate: バリデーションを実行するかどうか

    Returns:
        _metadataセクションのYAML文字列

    Raises:
        ValueError: バリデーションエラーが発生した場合
    """
    from datetime import datetime

    # pylayバージョン取得
    try:
        pylay_version = importlib.metadata.version("pylay")
    except importlib.metadata.PackageNotFoundError:
        pylay_version = "dev"

    # 生成時刻
    generated_at = datetime.now(UTC).isoformat()

    # ソースファイル情報
    source_path = Path(source_file)
    source_hash = ""
    source_size = 0
    source_modified_at = ""

    if source_path.exists():
        # ファイルハッシュ
        source_hash = _calculate_file_hash(source_path)

        # ファイルサイズ（バイト）
        source_size = source_path.stat().st_size

        # 最終更新日時
        source_modified_at = datetime.fromtimestamp(source_path.stat().st_mtime, tz=UTC).isoformat()

    # バリデーション
    if validate:
        errors = _validate_metadata(source_file, generated_at, pylay_version)
        if errors:
            error_msg = "\n".join(errors)
            raise ValueError(f"Metadata validation failed:\n{error_msg}")

    # YAML生成
    return f"""_metadata:
  generated_by: pylay yaml
  source: {source_file}
  source_hash: {source_hash}
  source_size: {source_size}
  source_modified_at: {source_modified_at}
  generated_at: {generated_at}
  pylay_version: {pylay_version}

"""


def _process_directory(
    directory: Path,
    output_path: Path,
    config: PylayConfig,
    console: Console,
) -> None:
    """ディレクトリ内の全ファイルから型を収集してschema.lay.yamlに集約

    Args:
        directory: 処理対象のディレクトリ
        output_path: 出力YAMLファイルパス（schema.lay.yaml）
        config: pylay設定
        console: Richコンソール
    """
    # 処理開始時のPanel表示
    start_panel = Panel(
        f"[bold cyan]ディレクトリ:[/bold cyan] {directory}\n" f"[bold cyan]出力先:[/bold cyan] {output_path}",
        title="[bold green]🚀 ディレクトリ型収集開始[/bold green]",
        border_style="green",
    )
    console.print(start_panel)

    # ディレクトリ直下のPythonファイルのみを検索（サブディレクトリは除外）
    py_files = _find_python_files_in_directory_only(directory)

    if not py_files:
        console.print(f"[yellow]警告: {directory} " "内に型定義を含むファイルが見つかりませんでした[/yellow]")
        return

    # 全ファイルから型を収集
    all_types = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("型定義を収集中...", total=len(py_files))

        for py_file in py_files:
            progress.update(task, description=f"処理中: {py_file.name}")

            try:
                # モジュールをインポート
                sys.path.insert(0, str(py_file.parent))
                module_name = py_file.stem
                module = importlib.import_module(module_name)  # noqa: F823

                # 型を抽出
                for name, obj in module.__dict__.items():
                    if isinstance(obj, type):
                        is_pydantic_model = hasattr(obj, "__annotations__") and hasattr(obj, "__pydantic_core_schema__")
                        is_enum = issubclass(obj, Enum)
                        is_user_defined = getattr(obj, "__module__", None) == module_name

                        if (is_pydantic_model or is_enum) and is_user_defined:
                            all_types[name] = obj

            except Exception as e:
                console.print(f"[yellow]⚠️ 警告: {py_file.name}の処理に失敗しました[/yellow]")
                console.print(f"[dim]詳細: {e}[/dim]")

            progress.advance(task)

    if not all_types:
        console.print("[yellow]警告: 変換可能な型が見つかりませんでした[/yellow]")
        return

    # 型をYAMLに変換（シンプル形式）
    with console.status("[bold green]YAMLファイル生成中..."):
        # ディレクトリからモジュールパスを構築
        # （複数ファイルの型が混在するため、ディレクトリレベルで指定）
        source_module_path = _path_to_module_path(directory)
        yaml_content = types_to_yaml_simple(all_types, source_module_path)

        # 警告ヘッダーを追加
        header = generate_yaml_header(
            str(directory),
            add_header=config.generation.add_generation_header,
            include_source=config.generation.include_source_path,
        )

        # メタデータセクションを生成（ディレクトリの情報）
        metadata = ""
        if config.output.include_metadata:
            # ディレクトリの場合は、ファイルハッシュやサイズは計算しない
            from datetime import datetime

            # pylayバージョン取得
            try:
                pylay_version = importlib.metadata.version("pylay")
            except importlib.metadata.PackageNotFoundError:
                pylay_version = "dev"

            # 生成時刻
            generated_at = datetime.now(UTC).isoformat()

            # ディレクトリ情報
            directory_str = str(directory)
            file_count = len(py_files)

            # YAML生成
            metadata = f"""_metadata:
  generated_by: pylay yaml
  source: {directory_str}
  source_type: directory
  file_count: {file_count}
  generated_at: {generated_at}
  pylay_version: {pylay_version}

"""

        # 出力内容を組み立て
        output_content_parts = []
        if header:
            output_content_parts.append(header)
            output_content_parts.append("\n")
        if metadata:
            output_content_parts.append(metadata)
        output_content_parts.append(yaml_content)
        output_content = "".join(output_content_parts)

        # 出力ディレクトリを作成
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # ファイルに書き込み
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output_content)

    # 完了メッセージ
    complete_panel = Panel(
        f"[bold green]✅ ディレクトリ型収集が完了しました[/bold green]\n\n"
        f"[bold cyan]出力ファイル:[/bold cyan] {output_path}\n"
        f"[bold cyan]収集型数:[/bold cyan] {len(all_types)} 個\n"
        f"[bold cyan]処理ファイル数:[/bold cyan] {len(py_files)} ファイル",
        title="[bold green]🎉 処理完了[/bold green]",
        border_style="green",
    )
    console.print(complete_panel)


def _process_single_file(
    input_path: Path,
    output_path: Path,
    config: PylayConfig,
    console: Console,
    root_key: str | None = None,
) -> None:
    """単一ファイルをYAMLに変換

    Args:
        input_path: 入力Pythonファイル
        output_path: 出力YAMLファイル
        config: pylay設定
        console: Richコンソール
        root_key: YAML構造のルートキー
    """
    # 処理開始時のPanel表示
    start_panel = Panel(
        f"[bold cyan]入力ファイル:[/bold cyan] {input_path.name}\n"
        f"[bold cyan]出力先:[/bold cyan] {output_path}\n"
        f"[bold cyan]ルートキー:[/bold cyan] {root_key or '自動設定'}",
        title="[bold green]🚀 型からYAML変換開始[/bold green]",
        border_style="green",
    )
    console.print(start_panel)

    # モジュールをインポート
    sys.path.insert(0, str(input_path.parent))
    module_name = input_path.stem

    # 同名モジュールの再利用を防ぐため、インポート前にsys.modulesから削除
    sys.modules.pop(module_name, None)

    # モジュールインポート中のプログレス表示
    with console.status(f"[bold green]モジュール '{module_name}' をインポート中..."):
        module = importlib.import_module(module_name)

    # モジュール内の全型アノテーションを検索
    types_dict: dict[str, type[object]] = {}

    # モジュール内のアイテム数を取得
    module_items = list(module.__dict__.items())

    # 型抽出中のプログレス表示
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("型定義を検索中...", total=len(module_items))

        for name, obj in module_items:
            # ユーザ定義クラスをフィルタリング:
            # このモジュールで定義されたPydanticモデルまたはEnum
            if isinstance(obj, type):
                # Pydanticモデルかどうかをチェック（BaseModelのサブクラス判定）
                try:
                    from pydantic import BaseModel

                    is_pydantic_model = issubclass(obj, BaseModel)
                except (TypeError, ImportError):
                    is_pydantic_model = False

                try:
                    is_enum = issubclass(obj, Enum)
                except TypeError:
                    is_enum = False

                is_user_defined = getattr(obj, "__module__", None) == module_name

                if (is_pydantic_model or is_enum) and is_user_defined:
                    try:
                        types_dict[name] = obj
                    except Exception as e:
                        console.print(f"[yellow]⚠️ 警告: {name}の処理に失敗しました[/yellow]")
                        console.print(f"[dim]詳細: {e}[/dim]")

            progress.advance(task)

    if not types_dict:
        console.rule("[bold red]エラー[/bold red]")
        console.print("[red]変換可能な型がモジュール内に見つかりませんでした[/red]")
        console.print("[dim]PydanticモデルまたはEnumが定義されていることを確認してください[/dim]")
        return

    # 型をYAMLに変換（シンプル形式）
    with console.status("[bold green]YAMLファイル生成中..."):
        # ファイルパスからモジュールパスを構築
        source_module_path = _path_to_module_path(input_path)
        yaml_content = types_to_yaml_simple(types_dict, source_module_path, input_path)

        # 警告ヘッダーを追加
        header = generate_yaml_header(
            str(input_path),
            add_header=config.generation.add_generation_header,
            include_source=config.generation.include_source_path,
        )

        # メタデータセクションを生成
        metadata = ""
        if config.output.include_metadata:
            metadata = _generate_metadata_section(str(input_path))

        # 出力内容を組み立て
        output_content_parts = []
        if header:
            output_content_parts.append(header)
            output_content_parts.append("\n")
        if metadata:
            output_content_parts.append(metadata)
        output_content_parts.append(yaml_content)
        output_content = "".join(output_content_parts)

        # 出力ディレクトリを作成
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # ファイルに書き込み
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

    result_table.add_row("入力モジュール", input_path.name)
    result_table.add_row("出力ファイル", str(output_path))
    result_table.add_row("検出型数", f"{len(types_dict)} 個")
    type_names = ", ".join(types_dict.keys())
    truncated_types = type_names[:50] + ("..." if len(type_names) > 50 else "")
    result_table.add_row("型一覧", truncated_types)

    console.print(result_table)

    # 完了メッセージのPanel
    complete_panel = Panel(
        f"[bold green]✅ 型からYAMLへの変換が完了しました[/bold green]\n\n"
        f"[bold cyan]出力ファイル:[/bold cyan] {output_path}\n"
        f"[bold cyan]変換型数:[/bold cyan] {len(types_dict)} 個",
        title="[bold green]🎉 処理完了[/bold green]",
        border_style="green",
    )
    console.print(complete_panel)

    # sys.pathとsys.modulesのクリーンアップ
    if str(input_path.parent) in sys.path:
        sys.path.remove(str(input_path.parent))
    # 同名モジュールの再利用を防ぐため、処理完了後もsys.modulesから削除
    sys.modules.pop(module_name, None)


def run_yaml(
    input_file: str | None = None,
    output_file: str | None = None,
    root_key: str | None = None,
) -> None:
    """Python型をYAML仕様に変換

    Args:
        input_file: Pythonモジュールファイルまたはディレクトリのパス
                    （Noneの場合はpyproject.toml使用）
        output_file: 出力YAMLファイルのパス または "-" で標準出力
        root_key: YAML構造のルートキー
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

        # パターン1: 引数なし → pyproject.tomlのtarget_dirsを使用
        if input_file is None:
            console.print(
                Panel(
                    "[bold cyan]引数が指定されていません。\n" "pyproject.tomlのtarget_dirsを使用します。[/bold cyan]",
                    title="[bold green]📋 設定ファイル使用モード[/bold green]",
                    border_style="green",
                )
            )

            # pyproject.tomlからtarget_dirsを取得
            if not config.target_dirs:
                console.print("[red]エラー: pyproject.tomlにtarget_dirsが設定されていません[/red]")
                return

            # 各target_dirを処理
            for target_dir_str in config.target_dirs:
                target_dir = Path(target_dir_str).resolve()
                if not target_dir.exists():
                    console.print(f"[yellow]警告: ディレクトリが存在しません: " f"{target_dir}[/yellow]")
                    continue

                # 全サブディレクトリを取得（階層ごとに処理）
                all_dirs = _find_all_subdirectories(target_dir)

                for current_dir in all_dirs:
                    # 出力パスを計算（schema.lay.yamlに集約）
                    if config.output.yaml_output_dir is None:
                        # Noneの場合：Pythonソースと同じディレクトリに出力
                        # 例: src/core/schemas/ → src/core/schemas/schema.lay.yaml
                        output_path = current_dir / f"schema{config.generation.lay_yaml_suffix}"
                    else:
                        # 指定がある場合：指定ディレクトリに構造をミラーリングして出力
                        # 例: src/core/schemas/ →
                        #     docs/pylay/src/core/schemas/schema.lay.yaml
                        try:
                            relative_path = current_dir.relative_to(Path.cwd())
                        except ValueError:
                            # 現在のディレクトリの外の場合は、ディレクトリ名のみを使用
                            relative_path = Path(current_dir.name)

                        output_path = (
                            Path(config.output.yaml_output_dir)
                            / relative_path
                            / f"schema{config.generation.lay_yaml_suffix}"
                        )

                    # 各ディレクトリを処理（直下のファイルのみ）
                    _process_directory(current_dir, output_path, config, console)

            return

        # パターン2: ファイル指定
        input_path = Path(input_file)

        if input_path.is_file():
            # 絶対パスに変換
            input_path = input_path.resolve()

            # 出力先の決定
            if output_file is None:
                # 出力先が未指定の場合の処理
                if config.output.yaml_output_dir is None:
                    # Noneの場合：Pythonソースと同じディレクトリに出力
                    output_path = input_path.parent / f"{input_path.stem}{config.generation.lay_yaml_suffix}"
                else:
                    # 指定がある場合：指定ディレクトリに構造をミラーリングして出力
                    try:
                        relative_path = input_path.relative_to(Path.cwd())
                    except ValueError:
                        # 現在のディレクトリの外の場合は、ファイル名のみを使用
                        relative_path = Path(input_path.name)

                    output_path = (
                        Path(config.output.yaml_output_dir)
                        / relative_path.parent
                        / f"{input_path.stem}{config.generation.lay_yaml_suffix}"
                    )
            else:
                output_path = Path(output_file)
                # .lay.yaml拡張子を自動付与
                if not str(output_path).endswith(config.generation.lay_yaml_suffix):
                    if not output_path.suffix:
                        output_path = output_path.with_suffix(config.generation.lay_yaml_suffix)
                    else:
                        output_path = output_path.with_suffix(config.generation.lay_yaml_suffix)

            _process_single_file(input_path, output_path, config, console, root_key)

        # パターン3: ディレクトリ指定
        elif input_path.is_dir():
            console.print(
                Panel(
                    f"[bold cyan]ディレクトリ:[/bold cyan] {input_path}\n"
                    "[bold cyan]モード:[/bold cyan] "
                    "ディレクトリ型集約（schema.lay.yaml）",
                    title="[bold green]📁 ディレクトリ処理モード[/bold green]",
                    border_style="green",
                )
            )

            # 絶対パスに変換
            input_path_resolved = input_path.resolve()

            # 出力パスを計算（schema.lay.yamlに集約）
            if output_file is None:
                # 出力先が未指定の場合の処理
                if config.output.yaml_output_dir is None:
                    # Noneの場合：Pythonソースと同じディレクトリに出力
                    output_path = input_path_resolved / f"schema{config.generation.lay_yaml_suffix}"
                else:
                    # 指定がある場合：指定ディレクトリに構造をミラーリングして出力
                    try:
                        relative_path = input_path_resolved.relative_to(Path.cwd())
                    except ValueError:
                        # 現在のディレクトリの外の場合は、ディレクトリ名のみを使用
                        relative_path = Path(input_path_resolved.name)

                    output_path = (
                        Path(config.output.yaml_output_dir)
                        / relative_path
                        / f"schema{config.generation.lay_yaml_suffix}"
                    )
            else:
                # 出力先が指定されている場合
                output_path = Path(output_file)
                # schema.lay.yaml拡張子を自動付与
                if not str(output_path).endswith(config.generation.lay_yaml_suffix):
                    if output_path.is_dir() or not output_path.suffix:
                        # ディレクトリまたは拡張子なし → schema.lay.yamlを追加
                        output_path = output_path / f"schema{config.generation.lay_yaml_suffix}"
                    else:
                        # 拡張子あり → .lay.yamlに変更
                        output_path = output_path.with_suffix(config.generation.lay_yaml_suffix)

            # 全サブディレクトリを取得（階層ごとに処理）
            all_dirs = _find_all_subdirectories(input_path_resolved)

            for current_dir in all_dirs:
                # 出力パスを計算
                if output_file is None:
                    # 出力先が未指定の場合の処理
                    if config.output.yaml_output_dir is None:
                        # Noneの場合：Pythonソースと同じディレクトリに出力
                        dir_output_path = current_dir / f"schema{config.generation.lay_yaml_suffix}"
                    else:
                        # 指定がある場合：指定ディレクトリに構造をミラーリングして出力
                        try:
                            relative_path = current_dir.relative_to(Path.cwd())
                        except ValueError:
                            # 現在のディレクトリの外の場合は、ディレクトリ名のみを使用
                            relative_path = Path(current_dir.name)

                        dir_output_path = (
                            Path(config.output.yaml_output_dir)
                            / relative_path
                            / f"schema{config.generation.lay_yaml_suffix}"
                        )
                else:
                    # 出力先が明示的に指定されている場合は従来の動作
                    # （全階層を1つのファイルに集約）
                    dir_output_path = output_path

                # 各ディレクトリを処理（直下のファイルのみ）
                _process_directory(current_dir, dir_output_path, config, console)

                # 出力先が指定されている場合は1回だけ処理
                if output_file is not None:
                    break

        else:
            console.print(f"[red]エラー: 指定されたパスが存在しません: {input_path}[/red]")

    except Exception as e:
        # エラーメッセージのPanel
        error_panel = Panel(
            f"[red]エラー: {e}[/red]",
            title="[bold red]❌ 処理エラー[/bold red]",
            border_style="red",
        )
        console.print(error_panel)
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)
