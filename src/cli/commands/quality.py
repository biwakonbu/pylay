"""
型品質チェックコマンド

pyproject.tomlで指定された基準に基づいて型定義の品質をチェックし、
アドバイス・警告・エラーレベルで結果を報告します。
"""

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click
from rich.console import Console
from rich.panel import Panel

from src.cli.utils import load_config, resolve_target_path
from src.core.analyzer.quality_checker import QualityChecker
from src.core.analyzer.type_level_analyzer import TypeLevelAnalyzer

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
    "--show-details",
    is_flag=True,
    default=False,
    help="問題箇所の詳細（ファイルパス、行番号、コード内容）を表示",
)
@click.option(
    "--severity",
    type=click.Choice(["error", "warning", "advice"], case_sensitive=False),
    default=None,
    help="深刻度でフィルタ（error/warning/advice）",
)
@click.option(
    "--issue-type",
    type=str,
    default=None,
    help="問題タイプでフィルタ（例: primitive_usage, level1_ratio_high）",
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
    show_details: bool,
    severity: str | None,
    issue_type: str | None,
    fail_on_error: bool,
) -> None:
    """
    型定義の品質をチェックし、改善提案を提供します。

    TARGET: 解析対象のディレクトリまたはファイル（デフォルト: カレントディレクトリ）

    品質チェック基準はpyproject.tomlの[tool.pylay.quality_check]セクションで設定します。
    設定されていない場合はデフォルトの基準でチェックします。

    例:
        pylay quality src/
        pylay quality --strict --show-details
        pylay quality --severity error src/
        pylay quality --issue-type primitive_usage src/
        pylay quality --severity error --issue-type level1_ratio_high src/
        pylay quality --config custom.toml --fail-on-error
    """
    # 設定ファイルを読み込み（target_dirs参照のため先に読み込む）
    try:
        config_obj = load_config(config)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    # 解析対象を決定
    target_path = resolve_target_path(target, config_obj)

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
        title="[bold green]Type Quality Check[/bold green]",
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

    # 品質チェッカーのロケータを解析対象に合わせる
    from src.core.analyzer.code_locator import CodeLocator

    quality_checker.code_locator = CodeLocator([Path(d) for d in target_dirs])

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
            title="[bold red]Analysis Error[/bold red]",
            border_style="red",
        )
        console.print(error_panel)
        if fail_on_error or strict:
            sys.exit(1)
        return

    # 品質チェックを実行
    try:
        check_result = quality_checker.check_quality(report)

        # フィルタを適用
        if severity or issue_type:
            check_result = _apply_filters(check_result, severity, issue_type)

        # レポートを生成（コンソール出力のみ）
        _output_console_report(
            quality_checker,
            check_result,
            report,
            show_details,
            target_dirs,
        )

        # エラーレベル処理
        if check_result.has_errors:
            if fail_on_error or strict:
                console.print()
                console.print("[bold red]Quality check failed with errors[/bold red]")
                sys.exit(1)
            else:
                console.print()
                console.print(
                    "[yellow]Quality check completed with warnings/errors "
                    "(use --fail-on-error to exit with code 1)[/yellow]"
                )
        else:
            console.print()
            console.print("[bold green]Quality check passed[/bold green]")

    except Exception as e:
        error_panel = Panel(
            f"[red]Error in quality check: {e}[/red]",
            title="[bold red]Quality Check Error[/bold red]",
            border_style="red",
        )
        console.print(error_panel)
        if fail_on_error or strict:
            sys.exit(1)


def _apply_filters(
    check_result: "QualityCheckResult",
    severity: str | None,
    issue_type: str | None,
) -> "QualityCheckResult":
    """品質チェック結果にフィルタを適用

    Args:
        check_result: 元の品質チェック結果
        severity: 深刻度フィルタ（error/warning/advice）
        issue_type: 問題タイプフィルタ

    Returns:
        フィルタ適用後の品質チェック結果
    """
    from src.core.analyzer.quality_models import QualityCheckResult

    filtered_issues = check_result.issues

    # 深刻度でフィルタ
    if severity:
        filtered_issues = [i for i in filtered_issues if i.severity == severity]

    # 問題タイプでフィルタ
    if issue_type:
        filtered_issues = [i for i in filtered_issues if i.issue_type == issue_type]

    # フィルタ後のカウントを再計算
    error_count = sum(1 for i in filtered_issues if i.severity == "error")
    warning_count = sum(1 for i in filtered_issues if i.severity == "warning")
    advice_count = sum(1 for i in filtered_issues if i.severity == "advice")
    total_issues = len(filtered_issues)
    has_errors = error_count > 0

    # 新しいQualityCheckResultを作成
    return QualityCheckResult(
        issues=filtered_issues,
        statistics=check_result.statistics,
        overall_score=check_result.overall_score,
        thresholds=check_result.thresholds,
        severity_levels=check_result.severity_levels,
        total_issues=total_issues,
        error_count=error_count,
        warning_count=warning_count,
        advice_count=advice_count,
        has_errors=has_errors,
    )


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
