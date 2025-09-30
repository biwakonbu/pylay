"""
解析エンジンの抽象基底クラス

Analyzerの抽象基底クラスのみを提供します。
循環インポートを回避するため、基底クラスのみをこのファイルに配置しています。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from src.core.schemas.graph_types import TypeDependencyGraph
from src.core.schemas.pylay_config import PylayConfig


class Analyzer(ABC):
    """
    解析エンジンの抽象基底クラス

    型推論と依存関係抽出を統一的に扱うインターフェースを提供します。
    """

    def __init__(self, config: PylayConfig) -> None:
        """
        Analyzerを初期化します。

        Args:
            config: pylayの設定オブジェクト
        """
        self.config = config

    @abstractmethod
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
