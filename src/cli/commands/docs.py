"""Documentation generation command"""

import sys
from pathlib import Path

from rich.box import SIMPLE
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.core.converters.yaml_to_type import yaml_to_spec
from src.core.doc_generators.yaml_doc_generator import YamlDocGenerator
from src.core.schemas.pylay_config import PylayConfig
from src.core.schemas.yaml_spec import TypeRoot


def run_docs(
    input_file: str, output_dir: str | None = None, format_type: str = "single"
) -> None:
    """Generate documentation from YAML specification

    Args:
        input_file: Path to input YAML file
        output_dir: Output directory for documentation
                   (Noneの場合はYAMLと同じディレクトリ)
        format_type: Output format ("single" or "multiple")
    """
    console = Console()

    try:
        # 設定を読み込み
        try:
            config = PylayConfig.from_pyproject_toml()
        except FileNotFoundError:
            config = PylayConfig()

        # 処理開始時のPanel表示
        input_path = Path(input_file).resolve()

        # 出力先の決定
        if output_dir is None:
            # 設定ファイルから読み込み
            if config.output.markdown_output_dir is None:
                # Noneの場合：YAMLと同じディレクトリに出力
                output_path = input_path.parent
            else:
                # 指定がある場合：指定ディレクトリに出力
                output_path = Path(config.output.markdown_output_dir)
        else:
            # 引数で指定されている場合
            output_path = Path(output_dir)

        start_panel = Panel(
            f"[bold cyan]入力ファイル:[/bold cyan] {input_path.name}\n"
            f"[bold cyan]出力ディレクトリ:[/bold cyan] {output_path}\n"
            f"[bold cyan]フォーマット:[/bold cyan] {format_type}",
            title="[bold green]🚀 ドキュメント生成開始[/bold green]",
            border_style="green",
        )
        console.print(start_panel)

        # YAMLファイル読み込み
        with console.status("[bold green]YAMLファイル読み込み中..."):
            with open(input_file, encoding="utf-8") as f:
                yaml_str = f.read()

        # YAMLパース
        with console.status("[bold green]型情報解析中..."):
            spec = yaml_to_spec(yaml_str)

        # Handle TypeRoot (multi-type) by using the first type
        if spec is not None and isinstance(spec, TypeRoot) and spec.types:
            spec = next(iter(spec.types.values()))

        # Create output directory
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate documentation
        generator = YamlDocGenerator()

        if format_type == "single":
            # Single file output
            output_file = output_path / "types.md"

            # ドキュメント生成中のステータス表示
            with console.status("[bold green]ドキュメント生成中..."):
                generator.generate(output_file, spec=spec)

        else:
            # Multiple files output (not implemented yet)
            console.rule("[bold yellow]警告[/bold yellow]")
            console.print(
                "[yellow]複数ファイル形式は未実装のため、単一ファイル形式を使用します[/yellow]"
            )
            output_file = output_path / "types.md"
            generator.generate(output_file, spec=spec)

        # 結果表示用のTable
        result_table = Table(
            title="生成結果サマリー",
            show_header=True,
            border_style="green",
            width=80,
            header_style="",
            box=SIMPLE,
        )
        result_table.add_column("項目", style="cyan", no_wrap=True, width=40)
        result_table.add_column("結果", style="green", justify="right", width=30)

        result_table.add_row("入力ファイル", input_path.name)
        result_table.add_row("出力ファイル", output_file.name)
        result_table.add_row("出力ディレクトリ", str(output_path))
        result_table.add_row("生成形式", format_type)

        console.print(result_table)

        # 完了メッセージのPanel
        complete_panel = Panel(
            f"[bold green]✅ ドキュメント生成が完了しました[/bold green]\n\n"
            f"[bold cyan]出力ファイル:[/bold cyan] {output_file}",
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
