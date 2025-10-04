"""
コードレビューのシンプルなコマンド

指定されたファイルに対して基本的なコードレビューを実行します。
"""

import click
from pathlib import Path
from rich.console import Console

from ...core.review.providers.claudecode import create_claude_review_provider

console = Console()


@click.command("review")
@click.argument("target", type=click.Path(exists=True))
@click.option(
    "--verbose", "-v", is_flag=True, help="詳細なログを出力"
)
def review(target: str, verbose: bool) -> None:
    """
    指定されたファイルに対してコードレビューを実行します。

    Args:
        target: レビュー対象のファイルパス
        verbose: 詳細ログを出力するかどうか
    """
    file_path = Path(target)

    if not file_path.is_file():
        console.print(f"[red]エラー: {target} はファイルではありません[/red]")
        return

    if verbose:
        console.print(f"[blue]レビュー対象: {file_path}[/blue]")

    # レビュープロバイダーを作成
    review_provider = create_claude_review_provider()

    try:
        # レビューを実行
        comments = review_provider(file_path)

        # 結果を表示
        _display_results(comments, verbose)

    except Exception as e:
        console.print(f"[red]レビュー中にエラーが発生しました: {e}[/red]")
        if verbose:
            import traceback
            console.print(traceback.format_exc())


def _display_results(comments: list, verbose: bool) -> None:
    """レビュー結果を表示"""
    if not comments:
        console.print("[green]レビュー完了: 問題が見つかりませんでした[/green]")
        return

    console.print(
        f"[yellow]レビュー完了: {len(comments)}件の問題が見つかりました[/yellow]"
    )

    for comment in comments:
        # 重要度に応じた色分け
        color = {
            "error": "red",
            "warning": "yellow",
            "info": "blue",
            "suggestion": "cyan"
        }.get(comment.severity, "white")

        console.print(
            f"[{color}]{comment.severity.upper()}: {comment.location}[/{color}]"
        )
        console.print(f"  メッセージ: {comment.message}")
        if comment.suggestion:
            console.print(f"  提案: {comment.suggestion}")
        console.print()
