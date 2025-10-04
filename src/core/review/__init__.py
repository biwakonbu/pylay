"""
レビュープロバイダーモジュール

シンプルなコードレビュー機能を提供します。
"""

from .protocols import ReviewProvider, SystemPromptProvider, TaskGenerator
from .providers.claudecode import create_claude_review_provider
from .types import ReviewComment, ReviewTask, SystemPrompt

__all__ = [
    # コア機能
    "create_claude_review_provider",
    # 型定義とインターフェース
    "ReviewProvider",
    "TaskGenerator",
    "SystemPromptProvider",
    # 型定義
    "ReviewComment",
    "ReviewTask",
    "SystemPrompt",
]
