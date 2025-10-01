"""
解析エンジンのプロトコル定義

型チェック専用のProtocolを提供し、循環インポートを回避します。
実装クラスは `base.py` に配置されます。
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from src.core.schemas.graph_types import TypeDependencyGraph
from src.core.schemas.pylay_config import PylayConfig


class AnalyzerProtocol(Protocol):
    """
    解析エンジンのプロトコル定義

    型推論と依存関係抽出を統一的に扱うインターフェースを提供します。
    このProtocolは型チェック専用で、実行時の依存を持ちません。
    """

    config: PylayConfig

    def analyze(self, input_path: Path | str) -> TypeDependencyGraph:
        """
        指定された入力から型依存グラフを生成します。

        Args:
            input_path: 解析対象のファイルパスまたはコード文字列

        Returns:
            生成された型依存グラフ

        Raises:
            ValueError: 入力が無効な場合
            RuntimeError: 解析に失敗した場合
        """
        ...
