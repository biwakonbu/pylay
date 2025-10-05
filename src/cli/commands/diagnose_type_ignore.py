"""
type: ignore 診断コマンド

# type: ignore が使用されている箇所の原因を特定し、解決策を提案します。
"""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from src.core.analyzer.type_ignore_analyzer import TypeIgnoreAnalyzer
from src.core.analyzer.type_ignore_reporter import TypeIgnoreReporter

console = Console()


@click.command("diagnose-type-ignore")
@click.option(
    "--file",
    "-f",
    type=click.Path(exists=True),
    help="解析対象のファイル（指定しない場合はプロジェクト全体）",
)
@click.option(
    "--priority",
    "-p",
    type=click.Choice(["high", "medium", "low", "all"], case_sensitive=False),
    default="all",
    help="表示する優先度（デフォルト: all）",
)
@click.option(
    "--solutions",
    "-s",
    is_flag=True,
    help="解決策を表示",
)
@click.option(
    "--format",
    type=click.Choice(["console", "json"], case_sensitive=False),
    default="console",
    help="出力形式（デフォルト: console）",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="出力ファイルパス（format=jsonの場合に使用）",
)
def diagnose_type_ignore(
    file: str | None,
    priority: str,
    solutions: bool,
    format: str,
    output: str | None,
) -> None:
    """
    type: ignore の原因を診断し、解決策を提案します。

    例:
        # プロジェクト全体を診断
        pylay diagnose-type-ignore

        # 特定ファイルを診断
        pylay diagnose-type-ignore --file src/core/converters/type_to_yaml.py

        # 高優先度のみ表示
        pylay diagnose-type-ignore --priority high

        # 解決策を含む詳細表示
        pylay diagnose-type-ignore --solutions

        # JSON形式で出力
        pylay diagnose-type-ignore --format json --output report.json
    """
    # アナライザーとレポーターを初期化
    analyzer = TypeIgnoreAnalyzer()
    reporter = TypeIgnoreReporter()

    # 解析実行
    if file:
        # 特定ファイル
        file_path = Path(file).resolve()
        try:
            rel_path = file_path.relative_to(Path.cwd())
        except ValueError:
            rel_path = file_path
        console.print(f"[bold cyan]🔍 解析中: {rel_path}[/bold cyan]")
        issues = analyzer.analyze_file(file)
    else:
        # プロジェクト全体
        console.print("[bold cyan]🔍 プロジェクト全体を解析中...[/bold cyan]")
        project_path = Path.cwd()
        issues = analyzer.analyze_project(project_path)

    # 優先度フィルタリング
    if priority.lower() != "all":
        priority_upper = priority.upper()
        issues = [i for i in issues if i.priority == priority_upper]

    # サマリー生成
    summary = analyzer.generate_summary(issues)

    # 出力
    if format == "console":
        reporter.generate_console_report(issues, summary, show_solutions=solutions)
    elif format == "json":
        if not output:
            msg = (
                "[bold red]エラー: JSON形式の場合は --output を指定してください"
                "[/bold red]"
            )
            console.print(msg)
            return
        reporter.export_json_report(issues, output)

    # 結果サマリー表示（コンソール出力時）
    if format == "console":
        if not issues:
            console.print(
                "[bold green]✅ type: ignore は検出されませんでした！[/bold green]"
            )
        else:
            console.print(
                f"\n[bold]検出数:[/bold] {summary.total_count} 件 "
                f"(HIGH: {summary.high_priority_count}, "
                f"MEDIUM: {summary.medium_priority_count}, "
                f"LOW: {summary.low_priority_count})"
            )
