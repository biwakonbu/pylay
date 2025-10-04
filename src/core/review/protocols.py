"""
レビュープロバイダーのシンプルなインターフェース定義

複雑なプロトコルではなく、シンプルな関数ベースのインターフェースを提供します。
"""

from collections.abc import Callable
from pathlib import Path

from .types import ReviewComment, ReviewTask, SystemPrompt

# 型エイリアスでシンプルなインターフェースを定義
ReviewProvider = Callable[[Path], list[ReviewComment]]
TaskGenerator = Callable[[list[ReviewComment]], list[ReviewTask]]
SystemPromptProvider = Callable[[], SystemPrompt]
