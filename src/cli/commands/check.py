"""
プロジェクト品質チェックコマンド

型定義レベル、type: ignore、品質チェックを統合した診断コマンド。
"""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from .analyze_types import analyze_types
from .diagnose_type_ignore import diagnose_type_ignore
from .quality import quality

console = Console()


@click.command("check")
@click.argument("target", type=click.Path(exists=True), required=False)
@click.option(
    "--focus",
    type=click.Choice(["types", "ignore", "quality", "all"], case_sensitive=False),
    default="all",
    help="チェック対象を指定（デフォルト: all）",
)
@click.option(
    "-f",
    "--format",
    type=click.Choice(["console", "markdown", "json"], case_sensitive=False),
    default="console",
    help="出力形式（デフォルト: console）",
)
@click.option("-o", "--output", type=click.Path(), help="出力ファイルパス")
@click.option("-v", "--verbose", is_flag=True, help="詳細なログを出力")
def check(
    target: str | None,
    focus: str,
    format: str,
    output: str | None,
    verbose: bool,
) -> None:
    """
    プロジェクトの品質をチェックし、改善提案を表示します。

    型定義レベル、type: ignore診断、品質チェックを統合した診断コマンドです。

    TARGET: 解析対象のディレクトリまたはファイル（デフォルト: カレントディレクトリ）

    使用例:
        # 全てのチェックを実行（推奨）
        uv run pylay check

        # 型定義レベル統計のみ
        uv run pylay check --focus types

        # type: ignore 診断のみ
        uv run pylay check --focus ignore

        # 品質チェックのみ
        uv run pylay check --focus quality

        # 特定のディレクトリをチェック
        uv run pylay check src/core

        # Markdown形式で出力
        uv run pylay check --format markdown --output report.md
    """
    target_path = Path(target) if target else Path.cwd()

    if focus == "all":
        # 全てのチェックを実行
        console.print()
        console.rule("[bold cyan]🔍 プロジェクト品質チェック[/bold cyan]")
        console.print()

        # 1. 型定義レベル統計
        console.print("[bold blue]1/3: 型定義レベル統計[/bold blue]")
        console.print()
        ctx = click.Context(analyze_types)
        ctx.invoke(
            analyze_types,
            target=str(target_path),
            format=format,
            output=output,
            recommendations=False,
            docstring_recommendations=False,
            all_recommendations=False,
            show_details=False,
            export_details=None,
            show_stats=True,
        )

        console.print()
        console.rule()
        console.print()

        # 2. type-ignore 診断
        console.print("[bold yellow]2/3: type: ignore 診断[/bold yellow]")
        console.print()
        ctx = click.Context(diagnose_type_ignore)
        ctx.invoke(
            diagnose_type_ignore,
            file=str(target_path) if target_path.is_file() else None,
            priority="all",
            solutions=False,
            format=format,
            output=None,  # 統合レポートに含めるため個別出力なし
        )

        console.print()
        console.rule()
        console.print()

        # 3. 品質チェック
        console.print("[bold green]3/3: 品質チェック[/bold green]")
        console.print()
        ctx = click.Context(quality)
        ctx.invoke(
            quality,
            target=str(target_path),
            config=None,
            strict=False,
            show_details=False,
            severity=None,
            issue_type=None,
            fail_on_error=False,
        )

        console.print()
        console.rule("[bold cyan]✅ チェック完了[/bold cyan]")
        console.print()

    elif focus == "types":
        # 型定義レベル統計のみ
        ctx = click.Context(analyze_types)
        ctx.invoke(
            analyze_types,
            target=str(target_path),
            format=format,
            output=output,
            recommendations=True,
            docstring_recommendations=True,
            all_recommendations=False,
            show_details=verbose,
            export_details=None,
            show_stats=True,
        )

    elif focus == "ignore":
        # type-ignore 診断のみ
        ctx = click.Context(diagnose_type_ignore)
        ctx.invoke(
            diagnose_type_ignore,
            file=str(target_path) if target_path.is_file() else None,
            priority="all",
            solutions=verbose,
            format=format,
            output=output,
        )

    elif focus == "quality":
        # 品質チェックのみ
        ctx = click.Context(quality)
        ctx.invoke(
            quality,
            target=str(target_path),
            config=None,
            strict=False,
            show_details=verbose,
            severity=None,
            issue_type=None,
            fail_on_error=False,
        )
