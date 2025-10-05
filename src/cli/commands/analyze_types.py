"""
型定義レベル分析コマンド

型定義レベル（Level 1/2/3）とドキュメント品質を分析し、改善推奨を提供します。
"""

from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)

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
    help=(
        "すべての推奨事項を表示（--recommendations --docstring-recommendations と同等）"
    ),
)
@click.option(
    "--show-details",
    is_flag=True,
    default=False,
    help="問題箇所の詳細（ファイルパス、行番号、コード内容）を表示",
)
@click.option(
    "--export-details",
    type=click.Path(),
    default=None,
    help="問題詳細をYAMLファイルにエクスポート（指定したパスに保存）",
)
@click.option(
    "--show-stats/--no-stats",
    default=True,
    help="型レベル統計情報を表示するかどうか（デフォルト: 表示）",
)
def analyze_types(
    target: str | None,
    format: str,
    output: str | None,
    recommendations: bool,
    docstring_recommendations: bool,
    all_recommendations: bool,
    show_details: bool,
    export_details: str | None,
    show_stats: bool,
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

    # 処理開始時のPanel表示
    rec_text = "On" if recommendations else "Off"
    doc_rec_text = "On" if docstring_recommendations else "Off"
    panel_content = (
        f"[bold cyan]Target:[/bold cyan] {target_path}\n"
        f"[bold cyan]Format:[/bold cyan] {format}\n"
        f"[bold cyan]Type Level Recommendations:[/bold cyan] {rec_text}\n"
        f"[bold cyan]Docstring Recommendations:[/bold cyan] {doc_rec_text}"
    )
    start_panel = Panel(
        panel_content,
        title="[bold green]🔍 Type Definition Level Analysis[/bold green]",
        border_style="green",
    )
    console.print(start_panel)

    # アナライザを初期化
    analyzer = TypeLevelAnalyzer()

    # 対象ディレクトリを決定（詳細表示用）
    if target_path.is_file():
        target_dirs = [str(target_path.parent)]
    else:
        target_dirs = [str(target_path)]

    # 解析を実行
    try:
        if target_path.is_file():
            # 単一ファイルの場合
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeRemainingColumn(),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task("Analyzing file...", total=1)
                report = analyzer.analyze_file(target_path)
                progress.advance(task)
        else:
            # ディレクトリの場合はファイルリストを事前に取得してプログレス表示
            python_files = list(target_path.rglob("*.py"))

            # プログレスバーを表示しながらファイルを処理
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeRemainingColumn(),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task(
                    "Analyzing directory...", total=len(python_files)
                )

                # 各ファイルを処理してプログレスを更新
                for py_file in python_files:
                    progress.update(task, description=f"Analyzing: {py_file.name}")
                    progress.advance(task)

            # 実際の解析はanalyze_directoryで実行（統計計算等も含む）
            with console.status("[bold green]Calculating statistics..."):
                report = analyzer.analyze_directory(
                    target_path, include_upgrade_recommendations=recommendations
                )

    except Exception as e:
        # エラーメッセージのPanel
        error_panel = Panel(
            f"[red]Error: {e}[/red]",
            title="[bold red]❌ Analysis Error[/bold red]",
            border_style="red",
        )
        console.print(error_panel)
        return

    # レポートを生成
    if format == "console":
        _output_console_report(
            analyzer,
            report,
            recommendations,
            docstring_recommendations,
            show_details,
            show_stats,
            target_dirs,
        )
    elif format == "markdown":
        _output_markdown_report(
            analyzer,
            report,
            output,
            show_upgrade_recs=recommendations,
            show_docstring_recs=docstring_recommendations,
        )
    elif format == "json":
        _output_json_report(
            analyzer,
            report,
            output,
            show_upgrade_recs=recommendations,
            show_docstring_recs=docstring_recommendations,
        )

    # 詳細情報をYAMLファイルにエクスポート
    if export_details:
        _export_details_to_yaml(analyzer, report, export_details, target_dirs)


def _output_console_report(
    analyzer: TypeLevelAnalyzer,
    report: TypeAnalysisReport,
    show_upgrade_recs: bool,
    show_docstring_recs: bool,
    show_details: bool,
    show_stats: bool,
    target_dirs: list[str],
) -> None:
    """コンソールにレポートを出力

    Args:
        analyzer: TypeLevelAnalyzer
        report: TypeAnalysisReport
        show_upgrade_recs: 型レベルアップ推奨を表示するか
        show_docstring_recs: docstring改善推奨を表示するか
        show_details: 詳細情報を表示するか
        target_dirs: 解析対象ディレクトリ
    """
    # 詳細表示用のreporterを初期化
    from src.core.analyzer.type_reporter import TypeReporter

    reporter = TypeReporter(target_dirs=target_dirs)

    # 詳細レポートを生成
    reporter.generate_detailed_report(report, show_details, show_stats)

    # 推奨事項を条件付きで表示
    if show_upgrade_recs and report.upgrade_recommendations:
        console.print()
        console.print(
            reporter.generate_upgrade_recommendations_report(
                report.upgrade_recommendations
            )
        )

    if show_docstring_recs and report.docstring_recommendations:
        console.print()
        console.print(
            reporter.generate_docstring_recommendations_report(
                report.docstring_recommendations
            )
        )


def _output_markdown_report(
    analyzer: TypeLevelAnalyzer,
    report: TypeAnalysisReport,
    output_path: str | None,
    *,
    show_upgrade_recs: bool,
    show_docstring_recs: bool,
) -> None:
    """Markdownレポートを出力

    Args:
        analyzer: TypeLevelAnalyzer
        report: TypeAnalysisReport
        output_path: 出力ファイルパス
        show_upgrade_recs: 型レベルアップ推奨を表示するか
        show_docstring_recs: docstring改善推奨を表示するか
    """
    # フィルタリング用にレポートをコピー
    render_report = report
    if not show_upgrade_recs or not show_docstring_recs:
        render_report = report.model_copy(deep=True)
        if not show_upgrade_recs:
            render_report.upgrade_recommendations = []
        if not show_docstring_recs:
            render_report.docstring_recommendations = []

    markdown_report = analyzer.reporter.generate_markdown_report(render_report)

    if output_path:
        # ファイルに書き込み
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_report)
        console.print(
            f"[bold green]✅ Markdown report saved: {output_path}[/bold green]"
        )
    else:
        # コンソールに出力
        console.print(markdown_report)


def _output_json_report(
    analyzer: TypeLevelAnalyzer,
    report: TypeAnalysisReport,
    output_path: str | None,
    *,
    show_upgrade_recs: bool,
    show_docstring_recs: bool,
) -> None:
    """JSONレポートを出力

    Args:
        analyzer: TypeLevelAnalyzer
        report: TypeAnalysisReport
        output_path: 出力ファイルパス
        show_upgrade_recs: 型レベルアップ推奨を表示するか
        show_docstring_recs: docstring改善推奨を表示するか
    """
    # フィルタリング用にレポートをコピー
    render_report = report
    if not show_upgrade_recs or not show_docstring_recs:
        render_report = report.model_copy(deep=True)
        if not show_upgrade_recs:
            render_report.upgrade_recommendations = []
        if not show_docstring_recs:
            render_report.docstring_recommendations = []

    json_report = analyzer.reporter.generate_json_report(render_report)

    if output_path:
        # ファイルに書き込み
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(json_report)
        console.print(f"[bold green]✅ JSON report saved: {output_path}[/bold green]")
    else:
        # コンソールに出力
        console.print(json_report)


def _export_details_to_yaml(
    analyzer: TypeLevelAnalyzer,
    report: TypeAnalysisReport,
    output_path: str,
    target_dirs: list[str],
) -> None:
    """問題詳細をYAMLファイルにエクスポート

    Args:
        analyzer: TypeLevelAnalyzer
        report: TypeAnalysisReport
        output_path: 出力ファイルパス
        target_dirs: 解析対象ディレクトリ
    """
    from src.core.analyzer.code_locator import CodeLocator

    try:
        # CodeLocatorで詳細情報を収集
        code_locator = CodeLocator([Path(d) for d in target_dirs])

        problem_details = {
            "problem_details": {
                "primitive_usage": [
                    {
                        "file": str(detail.location.file),
                        "line": detail.location.line,
                        "column": detail.location.column,
                        "type": detail.kind,
                        "primitive_type": detail.primitive_type,
                        "function_name": detail.function_name,
                        "class_name": detail.class_name,
                        "context": {
                            "before": detail.location.context_before,
                            "code": detail.location.code,
                            "after": detail.location.context_after,
                        },
                        "suggestion": (
                            f"primitive型 '{detail.primitive_type}' を使用しています。"
                            "ドメイン型への移行を検討してください。"
                        ),
                    }
                    for detail in code_locator.find_primitive_usages()
                ],
                "level1_types": [
                    {
                        "type_name": detail.type_name,
                        "definition": detail.definition,
                        "file": str(detail.location.file),
                        "line": detail.location.line,
                        "usage_count": detail.usage_count,
                        "docstring": detail.docstring,
                        "usage_examples": [
                            {
                                "file": str(ex.location.file),
                                "line": ex.location.line,
                                "context": ex.context,
                                "kind": ex.kind,
                            }
                            for ex in detail.usage_examples
                        ],
                        "recommendation": detail.recommendation,
                    }
                    for detail in code_locator.find_level1_types(
                        report.type_definitions
                    )
                ],
                "unused_types": [
                    {
                        "type_name": detail.type_name,
                        "definition": detail.definition,
                        "file": str(detail.location.file),
                        "line": detail.location.line,
                        "level": detail.level,
                        "docstring": detail.docstring,
                        "reason": detail.reason,
                        "recommendation": detail.recommendation,
                    }
                    for detail in code_locator.find_unused_types(
                        report.type_definitions
                    )
                ],
                "deprecated_typing": [
                    {
                        "file": str(detail.location.file),
                        "line": detail.location.line,
                        "imports": detail.imports,
                        "context": {
                            "code": detail.location.code,
                        },
                        "suggestion": detail.suggestion,
                    }
                    for detail in code_locator.find_deprecated_typing()
                ],
            }
        }

        # YAMLファイルに書き込み
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(
                problem_details,
                f,
                allow_unicode=True,
                indent=2,
                default_flow_style=False,
            )

        console.print(
            f"[bold green]✅ Problem details exported to YAML file: "
            f"{output_path}[/bold green]"
        )
    except OSError as e:
        console.print(f"[bold red]Error: Failed to write YAML file: {e}[/bold red]")
    except yaml.YAMLError as e:
        console.print(f"[bold red]Error: YAML serialization failed: {e}[/bold red]")
