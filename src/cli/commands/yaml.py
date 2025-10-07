"""型からYAMLへの変換コマンド

Pythonの型定義をYAML形式に変換するCLIコマンドです。
"""

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


def _generate_metadata_section(source_file: str) -> str:
    """YAMLメタデータセクションを生成

    Args:
        source_file: ソースファイルのパス

    Returns:
        _metadataセクションのYAML文字列
    """
    import importlib.metadata
    from datetime import datetime

    try:
        pylay_version = importlib.metadata.version("pylay")
    except importlib.metadata.PackageNotFoundError:
        pylay_version = "dev"

    generated_at = datetime.now(UTC).isoformat()

    return f"""_metadata:
  generated_by: pylay yaml
  source: {source_file}
  generated_at: {generated_at}
  pylay_version: {pylay_version}

"""


def run_yaml(input_file: str, output_file: str, root_key: str | None = None) -> None:
    """Python型をYAML仕様に変換

    Args:
        input_file: Pythonモジュールファイルのパス
        output_file: 出力YAMLファイルのパス
        root_key: YAML構造のルートキー
    """
    console = Console()

    try:
        # 設定を読み込み
        try:
            config = PylayConfig.from_pyproject_toml()
        except (FileNotFoundError, ValueError):
            # pyproject.tomlがない場合はデフォルト設定
            config = PylayConfig()

        # 処理開始時のPanel表示
        input_path = Path(input_file)
        output_path = Path(output_file)

        # .lay.yaml拡張子を自動付与
        if str(output_path).endswith(config.generation.lay_yaml_suffix):
            # 既に.lay.yamlで終わっている場合はそのまま
            pass
        elif not output_path.suffix:
            # 拡張子がない場合は.lay.yamlを追加
            output_path = output_path.with_suffix(config.generation.lay_yaml_suffix)
        else:
            # 他の拡張子がある場合は.lay.yamlに置き換え
            output_path = output_path.with_suffix(config.generation.lay_yaml_suffix)

        start_panel = Panel(
            f"[bold cyan]入力ファイル:[/bold cyan] {input_path.name}\n"
            f"[bold cyan]出力ファイル:[/bold cyan] {output_path}\n"
            f"[bold cyan]ルートキー:[/bold cyan] {root_key or '自動設定'}",
            title="[bold green]🚀 型からYAML変換開始[/bold green]",
            border_style="green",
        )
        console.print(start_panel)

        # モジュールをインポート
        sys.path.insert(0, str(input_path.parent))
        module_name = input_path.stem

        # モジュールをインポート dynamically
        import importlib

        # モジュールインポート中のプログレス表示
        with console.status(
            f"[bold green]モジュール '{module_name}' をインポート中..."
        ):
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
                    is_pydantic_model = (
                        hasattr(obj, "__annotations__")
                        and hasattr(obj, "__pydantic_core_schema__")  # Pydantic v2
                    )
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
                input_file,
                add_header=config.generation.add_generation_header,
                include_source=config.generation.include_source_path,
            )

            # メタデータセクションを生成
            metadata = ""
            if config.output.include_metadata:
                metadata = _generate_metadata_section(input_file)

            # ファイルに書き込み
            with open(output_path, "w", encoding="utf-8") as f:
                if header:
                    f.write(header)
                    f.write("\n")
                if metadata:
                    f.write(metadata)
                f.write(yaml_content)

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
        result_table.add_row("出力ファイル", output_path.name)
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

    except Exception as e:
        # エラーメッセージのPanel
        error_panel = Panel(
            f"[red]エラー: {e}[/red]",
            title="[bold red]❌ 処理エラー[/bold red]",
            border_style="red",
        )
        console.print(error_panel)
        sys.exit(1)
