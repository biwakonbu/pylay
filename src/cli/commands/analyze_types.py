"""
型定義レベル分析コマンド

型定義レベル（Level 1/2/3）とドキュメント品質を分析し、改善推奨を提供します。
"""

from pathlib import Path

import click
from rich.console import Console

from src.core.analyzer.type_level_analyzer import TypeLevelAnalyzer
from src.core.analyzer.type_level_models import TypeAnalysisReport

console = Console()


@click.command("analyze-types")
@click.argument(
    "target",
    type=click.Path(exists=True),
    required=False,
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["console", "markdown", "json"]),
    default="console",
    help="出力形式（デフォルト: console）",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="出力ファイルパス（format=markdown/jsonの場合に使用）",
)
@click.option(
    "--recommendations",
    "-r",
    is_flag=True,
    help="型レベルアップ推奨を表示",
)
@click.option(
    "--docstring-recommendations",
    "-d",
    is_flag=True,
    help="docstring改善推奨を表示",
)
@click.option(
    "--all-recommendations",
    "-a",
    is_flag=True,
    help="すべての推奨事項を表示（--recommendations --docstring-recommendations と同等）",
)
def analyze_types(
    target: str | None,
    format: str,
    output: str | None,
    recommendations: bool,
    docstring_recommendations: bool,
    all_recommendations: bool,
) -> None:
    """
    型定義レベルとドキュメント品質を分析します。

    TARGET: 解析対象のディレクトリまたはファイル（デフォルト: カレントディレクトリ）

    例:
        pylay analyze-types src/
        pylay analyze-types src/core/schemas/types.py --recommendations
        pylay analyze-types --format markdown --output report.md
        pylay analyze-types --all-recommendations
    """
    # デフォルトはカレントディレクトリ
    if target is None:
        target_path = Path.cwd()
    else:
        target_path = Path(target)

    # すべての推奨事項を表示
    if all_recommendations:
        recommendations = True
        docstring_recommendations = True

    console.print("[bold blue]🔍 型定義レベル分析を開始します...[/bold blue]")
    console.print(f"対象: {target_path}\n")

    # アナライザを初期化
    analyzer = TypeLevelAnalyzer()

    # 解析を実行
    try:
        if target_path.is_file():
            report = analyzer.analyze_file(target_path)
        else:
            report = analyzer.analyze_directory(target_path)
    except Exception as e:
        console.print(f"[bold red]エラー: 解析中にエラーが発生しました: {e}[/bold red]")
        return

    # レポートを生成
    if format == "console":
        _output_console_report(
            analyzer, report, recommendations, docstring_recommendations
        )
    elif format == "markdown":
        _output_markdown_report(analyzer, report, output)
    elif format == "json":
        _output_json_report(analyzer, report, output)


def _output_console_report(
    analyzer: TypeLevelAnalyzer,
    report: TypeAnalysisReport,
    show_upgrade_recs: bool,
    show_docstring_recs: bool,
) -> None:
    """コンソールにレポートを出力

    Args:
        analyzer: TypeLevelAnalyzer
        report: TypeAnalysisReport
        show_upgrade_recs: 型レベルアップ推奨を表示するか
        show_docstring_recs: docstring改善推奨を表示するか
    """
    # 基本レポート
    console_report = analyzer.reporter.generate_console_report(report)
    console.print(console_report)

    # 型レベルアップ推奨
    if show_upgrade_recs and report.upgrade_recommendations:
        upgrade_report = analyzer.reporter.generate_upgrade_recommendations_report(
            report.upgrade_recommendations
        )
        console.print(upgrade_report)

    # docstring改善推奨
    if show_docstring_recs and report.docstring_recommendations:
        docstring_report = analyzer.reporter.generate_docstring_recommendations_report(
            report.docstring_recommendations
        )
        console.print(docstring_report)


def _output_markdown_report(
    analyzer: TypeLevelAnalyzer, report: TypeAnalysisReport, output_path: str | None
) -> None:
    """Markdownレポートを出力

    Args:
        analyzer: TypeLevelAnalyzer
        report: TypeAnalysisReport
        output_path: 出力ファイルパス
    """
    markdown_report = analyzer.reporter.generate_markdown_report(report)

    if output_path:
        # ファイルに書き込み
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_report)
        console.print(
            f"[bold green]✅ Markdownレポートを保存しました: {output_path}[/bold green]"
        )
    else:
        # コンソールに出力
        console.print(markdown_report)


def _output_json_report(
    analyzer: TypeLevelAnalyzer, report: TypeAnalysisReport, output_path: str | None
) -> None:
    """JSONレポートを出力

    Args:
        analyzer: TypeLevelAnalyzer
        report: TypeAnalysisReport
        output_path: 出力ファイルパス
    """
    json_report = analyzer.reporter.generate_json_report(report)

    if output_path:
        # ファイルに書き込み
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(json_report)
        console.print(
            f"[bold green]✅ JSONレポートを保存しました: {output_path}[/bold green]"
        )
    else:
        # コンソールに出力
        console.print(json_report)
