"""
型品質チェックコマンド

pyproject.tomlで指定された基準に基づいて型定義の品質をチェックし、
アドバイス・警告・エラーレベルで結果を報告します。
"""

from pathlib import Path
from typing import TYPE_CHECKING

import click
from rich.console import Console
from rich.panel import Panel

from src.core.analyzer.quality_checker import QualityChecker
from src.core.analyzer.type_level_analyzer import TypeLevelAnalyzer
from src.core.schemas.pylay_config import PylayConfig

if TYPE_CHECKING:
    from src.core.analyzer.quality_models import QualityCheckResult
    from src.core.analyzer.type_level_models import TypeAnalysisReport

console = Console()


@click.command("quality")
@click.argument(
    "target",
    type=click.Path(exists=True),
    required=False,
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="設定ファイルのパス（デフォルト: pyproject.toml）",
)
@click.option(
    "--strict",
    is_flag=True,
    help="厳格モードで実行（エラーレベルで終了コード1を返す）",
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
    "--fail-on-error",
    is_flag=True,
    help="エラーが発生した場合に終了コード1で終了",
)
def quality(
    target: str | None,
    config: str | None,
    strict: bool,
    format: str,
    output: str | None,
    show_details: bool,
    export_details: str | None,
    fail_on_error: bool,
) -> None:
    """
    型定義の品質をチェックし、改善提案を提供します。

    TARGET: 解析対象のディレクトリまたはファイル（デフォルト: カレントディレクトリ）

    品質チェック基準はpyproject.tomlの[tool.pylay.quality_check]セクションで設定します。
    設定されていない場合はデフォルトの基準でチェックします。

    例:
        pylay quality src/
        pylay quality --strict --format markdown --output report.md
        pylay quality --config custom.toml --fail-on-error
    """
    # デフォルトはカレントディレクトリ
    if target is None:
        target_path = Path.cwd()
    else:
        target_path = Path(target)

    # 設定ファイルを読み込み
    try:
        if config:
            project_root = Path(config).parent
            config_obj = PylayConfig.from_pyproject_toml(project_root)
        else:
            project_root = target_path.parent if target_path.is_file() else target_path
            config_obj = PylayConfig.from_pyproject_toml(project_root)
    except Exception as e:
        if config:
            console.print(f"[red]Error: Failed to load config file: {e}[/red]")
        else:
            console.print(f"[red]Error: Failed to load pyproject.toml: {e}[/red]")
        return

    # 品質チェックが有効か確認
    if not config_obj.is_quality_check_enabled():
        console.print(
            "[yellow]Warning: Quality check is not configured in "
            "pyproject.toml[/yellow]"
        )
        console.print(
            "[yellow]Using default thresholds. Configure "
            "[tool.pylay.quality_check] section for custom settings.[/yellow]"
        )

    # 処理開始時のPanel表示
    config_text = f"Config: {config}" if config else "Config: pyproject.toml"
    strict_text = "On" if strict else "Off"
    quality_status = "Enabled" if config_obj.is_quality_check_enabled() else "Disabled"
    panel_content = (
        f"[bold cyan]Target:[/bold cyan] {target_path}\n"
        f"[bold cyan]{config_text}[/bold cyan]\n"
        f"[bold cyan]Format:[/bold cyan] {format}\n"
        f"[bold cyan]Strict Mode:[/bold cyan] {strict_text}\n"
        f"[bold cyan]Quality Check:[/bold cyan] {quality_status}"
    )
    start_panel = Panel(
        panel_content,
        title="[bold green]🔍 Type Quality Check[/bold green]",
        border_style="green",
    )
    console.print(start_panel)

    # アナライザを初期化
    analyzer = TypeLevelAnalyzer()

    # 品質チェッカーを初期化
    quality_checker = QualityChecker(config_obj)

    # 対象ディレクトリを決定（詳細表示用）
    if target_path.is_file():
        target_dirs = [str(target_path.parent)]
    else:
        target_dirs = [str(target_path)]

    # 解析を実行
    try:
        if target_path.is_file():
            # 単一ファイルの場合
            report = analyzer.analyze_file(target_path)
        else:
            # ディレクトリの場合はファイルリストを事前に取得してプログレス表示
            python_files = list(target_path.rglob("*.py"))

            with console.status(f"[bold green]Analyzing {len(python_files)} files..."):
                report = analyzer.analyze_directory(target_path)

    except Exception as e:
        # エラーメッセージのPanel
        error_panel = Panel(
            f"[red]Error: {e}[/red]",
            title="[bold red]❌ Analysis Error[/bold red]",
            border_style="red",
        )
        console.print(error_panel)
        if fail_on_error or strict:
            exit(1)
        return

    # 品質チェックを実行
    try:
        check_result = quality_checker.check_quality(report)

        # レポートを生成
        if format == "console":
            _output_console_report(
                quality_checker,
                check_result,
                report,
                show_details,
                target_dirs,
            )
        elif format == "markdown":
            _output_markdown_report(
                quality_checker,
                check_result,
                output,
            )
        elif format == "json":
            _output_json_report(
                quality_checker,
                check_result,
                output,
            )

        # 詳細情報をYAMLファイルにエクスポート
        if export_details:
            _export_details_to_yaml(
                quality_checker, check_result, export_details, target_dirs
            )

        # エラーレベル処理
        if check_result.has_errors:
            if fail_on_error or strict:
                console.print()
                console.print(
                    "[bold red]❌ Quality check failed with errors[/bold red]"
                )
                exit(1)
            else:
                console.print()
                console.print(
                    "[yellow]⚠️  Quality check completed with warnings/errors "
                    "(use --fail-on-error to exit with code 1)[/yellow]"
                )
        else:
            console.print()
            console.print("[bold green]✅ Quality check passed[/bold green]")

    except Exception as e:
        error_panel = Panel(
            f"[red]Error in quality check: {e}[/red]",
            title="[bold red]❌ Quality Check Error[/bold red]",
            border_style="red",
        )
        console.print(error_panel)
        if fail_on_error or strict:
            exit(1)


def _output_console_report(
    quality_checker: QualityChecker,
    check_result: "QualityCheckResult",
    report: "TypeAnalysisReport",
    show_details: bool,
    target_dirs: list[str],
) -> None:
    """コンソールにレポートを出力"""
    from src.core.analyzer.quality_reporter import QualityReporter

    reporter = QualityReporter(target_dirs=target_dirs)

    # 詳細レポートを生成
    reporter.generate_console_report(check_result, report, show_details)


def _output_markdown_report(
    quality_checker: QualityChecker,
    check_result: "QualityCheckResult",
    output_path: str | None,
) -> None:
    """Markdownレポートを出力"""
    from src.core.analyzer.quality_reporter import QualityReporter

    reporter = QualityReporter()

    markdown_report = reporter.generate_markdown_report(check_result)

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
    quality_checker: QualityChecker,
    check_result: "QualityCheckResult",
    output_path: str | None,
) -> None:
    """JSONレポートを出力"""
    from src.core.analyzer.quality_reporter import QualityReporter

    reporter = QualityReporter()

    json_report = reporter.generate_json_report(check_result)

    if output_path:
        # ファイルに書き込み
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(json_report)
        console.print(f"[bold green]✅ JSON report saved: {output_path}[/bold green]")
    else:
        # コンソールに出力
        console.print(json_report)


def _export_details_to_yaml(
    quality_checker: QualityChecker,
    check_result: "QualityCheckResult",
    output_path: str,
    target_dirs: list[str],
) -> None:
    """問題詳細をYAMLファイルにエクスポート"""
    import yaml

    try:
        problem_details = {
            "quality_check_results": {
                "summary": {
                    "total_issues": check_result.total_issues,
                    "error_count": check_result.error_count,
                    "warning_count": check_result.warning_count,
                    "advice_count": check_result.advice_count,
                    "has_errors": check_result.has_errors,
                    "overall_score": check_result.overall_score,
                },
                "issues": [
                    {
                        "type": issue.issue_type,
                        "severity": issue.severity,
                        "file": str(issue.location.file) if issue.location else "",
                        "line": issue.location.line if issue.location else 0,
                        "column": issue.location.column if issue.location else 0,
                        "message": issue.message,
                        "context": {
                            "before": issue.location.context_before
                            if issue.location
                            else [],
                            "code": issue.location.code if issue.location else "",
                            "after": issue.location.context_after
                            if issue.location
                            else [],
                        },
                        "suggestion": issue.suggestion,
                        "improvement_plan": issue.improvement_plan,
                    }
                    for issue in check_result.issues
                ],
                "statistics": {
                    "level1_ratio": check_result.statistics.level1_ratio,
                    "level2_ratio": check_result.statistics.level2_ratio,
                    "level3_ratio": check_result.statistics.level3_ratio,
                    "documentation_rate": (
                        check_result.statistics.documentation.implementation_rate
                    ),
                    "primitive_usage_ratio": (
                        check_result.statistics.primitive_usage_ratio
                    ),
                },
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
