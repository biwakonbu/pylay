"""型からYAMLへの変換コマンド

Pythonの型定義をYAML形式に変換するCLIコマンドです。
"""

import importlib
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
from src.core.converters.type_to_yaml import types_to_yaml
from src.core.schemas.pylay_config import PylayConfig


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
        # 例: type UserId = str
        has_type_alias = bool(re.search(r"^type\s+\w+\s*=", content, re.MULTILINE))

        # 3. NewType
        # 例: UserId = NewType('UserId', str)
        has_newtype = "NewType" in content and "NewType(" in content

        # 4. dataclass
        # 例: @dataclass class User:
        has_dataclass = "@dataclass" in content

        # 5. Enum
        # 例: class Status(Enum):
        has_enum = "Enum" in content and "class " in content

        return any(
            [has_basemodel, has_type_alias, has_newtype, has_dataclass, has_enum]
        )
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
        if (
            py_file.name.startswith("test_")
            or "__pycache__" in str(py_file)
            or py_file.name == "__init__.py"
        ):
            continue

        if _has_type_definitions(py_file):
            python_files.append(py_file)

    return python_files


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


def _validate_metadata(
    source_file: str, generated_at: str, pylay_version: str
) -> list[str]:
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
    import importlib.metadata
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
        source_modified_at = datetime.fromtimestamp(
            source_path.stat().st_mtime, tz=UTC
        ).isoformat()

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

    # モジュールインポート中のプログレス表示
    with console.status(f"[bold green]モジュール '{module_name}' をインポート中..."):
        module = importlib.import_module(module_name)

    # モジュール内の全型アノテーションを検索
    types_dict = {}

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
                # Pydanticモデルかどうかをチェック
                # （BaseModelのサブクラスでアノテーションを持つ）
                is_pydantic_model = hasattr(obj, "__annotations__") and hasattr(
                    obj, "__pydantic_core_schema__"
                )  # Pydantic v2
                is_enum = issubclass(obj, Enum)
                is_user_defined = getattr(obj, "__module__", None) == module_name

                if (is_pydantic_model or is_enum) and is_user_defined:
                    try:
                        types_dict[name] = obj
                    except Exception as e:
                        console.print(
                            f"[yellow]⚠️ 警告: {name}の処理に失敗しました[/yellow]"
                        )
                        console.print(f"[dim]詳細: {e}[/dim]")

            progress.advance(task)

    if not types_dict:
        console.rule("[bold red]エラー[/bold red]")
        console.print("[red]変換可能な型がモジュール内に見つかりませんでした[/red]")
        console.print(
            "[dim]PydanticモデルまたはEnumが定義されていることを確認してください[/dim]"
        )
        return

    # 型をYAMLに変換
    with console.status("[bold green]YAMLファイル生成中..."):
        yaml_content = types_to_yaml(types_dict)

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
                    "[bold cyan]引数が指定されていません。\n"
                    "pyproject.tomlのtarget_dirsを使用します。[/bold cyan]",
                    title="[bold green]📋 設定ファイル使用モード[/bold green]",
                    border_style="green",
                )
            )

            # pyproject.tomlからtarget_dirsを取得
            if not config.target_dirs:
                console.print(
                    "[red]エラー: pyproject.tomlにtarget_dirsが設定されていません[/red]"
                )
                return

            # 各target_dirを処理
            for target_dir_str in config.target_dirs:
                target_dir = Path(target_dir_str)
                if not target_dir.exists():
                    console.print(
                        f"[yellow]警告: ディレクトリが存在しません: "
                        f"{target_dir}[/yellow]"
                    )
                    continue

                # ディレクトリ内の型定義を含むファイルを検索
                py_files = _find_python_files_with_type_definitions(target_dir)

                for py_file in py_files:
                    # 絶対パスに変換
                    py_file = py_file.resolve()

                    # 出力パスを計算（ディレクトリ構造を保持）
                    # 例: src/core/schemas/yaml_spec.py →
                    #     docs/pylay/src/core/schemas/yaml_spec.lay.yaml
                    try:
                        relative_path = py_file.relative_to(Path.cwd())
                    except ValueError:
                        # 現在のディレクトリの外の場合は、ファイル名のみを使用
                        relative_path = Path(py_file.name)

                    output_path = (
                        Path(config.output_dir)
                        / relative_path.parent
                        / f"{py_file.stem}{config.generation.lay_yaml_suffix}"
                    )

                    # 単一ファイル処理
                    _process_single_file(
                        py_file, output_path, config, console, root_key
                    )

            return

        # パターン2: ファイル指定
        input_path = Path(input_file)

        if input_path.is_file():
            # 絶対パスに変換
            input_path = input_path.resolve()

            # 出力先の決定
            if output_file is None:
                # 出力先が未指定の場合、ディレクトリ構造を保持してdocs/pylay/に出力
                try:
                    relative_path = input_path.relative_to(Path.cwd())
                except ValueError:
                    # 現在のディレクトリの外の場合は、ファイル名のみを使用
                    relative_path = Path(input_path.name)

                output_path = (
                    Path(config.output_dir)
                    / relative_path.parent
                    / f"{input_path.stem}{config.generation.lay_yaml_suffix}"
                )
            else:
                output_path = Path(output_file)
                # .lay.yaml拡張子を自動付与
                if not str(output_path).endswith(config.generation.lay_yaml_suffix):
                    if not output_path.suffix:
                        output_path = output_path.with_suffix(
                            config.generation.lay_yaml_suffix
                        )
                    else:
                        output_path = output_path.with_suffix(
                            config.generation.lay_yaml_suffix
                        )

            _process_single_file(input_path, output_path, config, console, root_key)

        # パターン3: ディレクトリ指定
        elif input_path.is_dir():
            console.print(
                Panel(
                    f"[bold cyan]ディレクトリ:[/bold cyan] {input_path}\n"
                    "[bold cyan]モード:[/bold cyan] 再帰的YAML生成",
                    title="[bold green]📁 ディレクトリ処理モード[/bold green]",
                    border_style="green",
                )
            )

            # ディレクトリ内の型定義を含むファイルを検索
            py_files = _find_python_files_with_type_definitions(input_path)

            if not py_files:
                console.print(
                    "[yellow]警告: 型定義を含むPythonファイルが"
                    "見つかりませんでした[/yellow]"
                )
                return

            console.print(f"[green]検出ファイル数: {len(py_files)} 個[/green]\n")

            # 各ファイルを処理
            for py_file in py_files:
                # 絶対パスに変換
                py_file = py_file.resolve()
                input_path_resolved = input_path.resolve()

                # 出力パスを計算（ディレクトリ構造を保持）
                if output_file is None:
                    # 出力先が未指定の場合、ディレクトリ構造を保持してdocs/pylay/に出力
                    try:
                        relative_path = py_file.relative_to(Path.cwd())
                    except ValueError:
                        # 現在のディレクトリの外の場合は、ファイル名のみを使用
                        relative_path = Path(py_file.name)

                    output_path = (
                        Path(config.output_dir)
                        / relative_path.parent
                        / f"{py_file.stem}{config.generation.lay_yaml_suffix}"
                    )
                else:
                    # 出力先が指定されている場合は、そのディレクトリ配下に構造を保持
                    try:
                        relative_path = py_file.relative_to(input_path_resolved)
                    except ValueError:
                        # ディレクトリ外の場合は、ファイル名のみを使用
                        relative_path = Path(py_file.name)

                    output_path = (
                        Path(output_file)
                        / relative_path.parent
                        / f"{py_file.stem}{config.generation.lay_yaml_suffix}"
                    )

                # 単一ファイル処理
                _process_single_file(py_file, output_path, config, console, root_key)

        else:
            console.print(
                f"[red]エラー: 指定されたパスが存在しません: {input_path}[/red]"
            )

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
