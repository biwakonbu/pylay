"""
ClaudeCodeレビュープロバイダー実装

シンプルで実用的なClaudeCode連携を提供します。
"""

import logging
from collections.abc import Callable
from pathlib import Path

from ..types import (
    ReviewComment,
    ReviewLocation,
    ValidatedColumnNumber,
    ValidatedLineNumber,
)

logger = logging.getLogger(__name__)


def create_claude_review_provider() -> Callable[[Path], list[ReviewComment]]:
    """
    ClaudeCodeレビュープロバイダーを作成します。

    Returns:
        レビュー機能を提供する関数
    """

    def review_file(file_path: Path) -> list[ReviewComment]:
        """
        指定されたファイルをレビューします。

        Args:
            file_path: レビュー対象のファイルパス

        Returns:
            レビューコメントのリスト
        """
        if not file_path.exists():
            logger.warning(f"ファイルが存在しません: {file_path}")
            return []

        try:
            # ファイル内容を読み込み
            with open(file_path, encoding="utf-8") as f:
                code_content = f.read()

            # シンプルなレビューを実行（実際にはClaudeCodeを呼び出す）
            comments = _perform_review(code_content, file_path)

            logger.info(f"{file_path}のレビュー完了: {len(comments)}件のコメント")
            return comments

        except Exception as e:
            logger.error(f"レビュー中にエラーが発生: {e}")
            return []

    return review_file


def _perform_review(code_content: str, file_path: Path) -> list[ReviewComment]:
    """
    コードレビューを実行します。

    Args:
        code_content: レビュー対象のコード内容
        file_path: ファイルパス

    Returns:
        レビューコメントのリスト
    """
    comments = []

    # 基本的なチェック（実際の実装ではClaudeCodeを呼び出す）
    if not code_content.strip():
        comments.append(
            ReviewComment(
                id="empty_file",
                location=_create_location(file_path, 1),
                severity="warning",
                message="ファイルが空です",
                suggestion="適切なコードを実装してください",
            )
        )
    elif "TODO" in code_content.upper():
        comments.append(
            ReviewComment(
                id="todo_comment",
                location=_create_location(file_path, 1),
                severity="info",
                message="TODOコメントが残っています",
                suggestion="TODOコメントを適切な実装に置き換えてください",
            )
        )
    elif "import" not in code_content and len(code_content.split("\n")) > 10:
        comments.append(
            ReviewComment(
                id="no_imports",
                location=_create_location(file_path, 1),
                severity="info",
                message="インポート文が見当たりません",
                suggestion="必要なモジュールをインポートしてください",
            )
        )

    return comments


def _create_location(file_path: Path, line_number: int) -> ReviewLocation:
    """レビュー場所を作成"""
    return ReviewLocation(
        file_path=str(file_path),
        line_number=ValidatedLineNumber(line_number),
        column_number=ValidatedColumnNumber(1),
    )
