"""
解析エンジンの基底モジュール

Analyzerインターフェースとファクトリ関数を提供します。
解析部分を他のコンポーネントから疎結合に利用するための基盤です。
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from src.core.analyzer.abc_base import Analyzer
from src.core.analyzer.exceptions import AnalysisError
from src.core.schemas.graph_types import TypeDependencyGraph
from src.core.schemas.pylay_config import PylayConfig


class FullAnalyzer(Analyzer):
    """
    完全解析を実行するAnalyzer

    戦略パターンを活用して型推論と依存抽出を統合します。
    """

    def __init__(self, config: PylayConfig) -> None:
        """
        FullAnalyzerを初期化します。

        Args:
            config: pylay設定オブジェクト
        """
        super().__init__(config)
        from src.core.analyzer.strategies import create_analysis_strategy

        # 設定に基づいて戦略を選択
        self.strategy = create_analysis_strategy(config)

    def analyze(self, input_path: Path | str) -> TypeDependencyGraph:
        """
        完全解析を実行し、グラフを生成します。

        Args:
            input_path: 解析対象のファイルパスまたはコード文字列

        Returns:
            生成された型依存グラフ

        Raises:
            ValueError: 入力が無効な場合
            AnalysisError: 解析に失敗した場合
        """
        # 戦略に解析を委譲
        try:
            file_path, cleanup = self._prepare_input(input_path)
        except OSError as e:
            raise AnalysisError("入力の準備に失敗しました") from e

        try:
            return self.strategy.analyze(file_path)
        finally:
            # 一時ファイルが作成された場合は確実にクリーンアップ
            cleanup()

    def _prepare_input(self, input_path: Path | str) -> tuple[Path, Callable[[], None]]:
        """
        入力をファイルパスに変換し、クリーンアップ関数を返します。

        Args:
            input_path: ファイルパスまたはコード文字列

        Returns:
            (ファイルパス, クリーンアップ関数) のタプル
            クリーンアップ関数は一時ファイルを削除します（一時ファイルでない場合は何もしません）

        Raises:
            ValueError: input_pathが無効な型の場合
        """
        if isinstance(input_path, str):
            # コード文字列の場合、一時ファイルを作成
            from pydantic import ValidationError

            from src.core.schemas.analyzer_types import TempFileConfig
            from src.core.utils.io_helpers import cleanup_temp_file, create_temp_file

            try:
                temp_config = TempFileConfig(code=input_path, suffix=".py", mode="w")
            except ValidationError as e:
                raise ValueError(f"無効な入力: {e}") from e
            temp_path = create_temp_file(temp_config)

            # クリーンアップ関数を返す
            def cleanup() -> None:
                """一時ファイルをクリーンアップします。"""
                cleanup_temp_file(temp_path)

            return temp_path, cleanup
        elif isinstance(input_path, Path):
            # 既存ファイルの場合、何もしないクリーンアップ関数を返す
            def noop_cleanup() -> None:
                """何も実行しないクリーンアップ関数です。"""
                pass

            return input_path, noop_cleanup
        else:
            raise ValueError("input_path は Path または str でなければなりません")


def create_analyzer(config: PylayConfig, mode: str = "full") -> Analyzer:
    """
    指定されたモードに基づいてAnalyzerインスタンスを作成します。

    Args:
        config: pylayの設定オブジェクト
        mode: 解析モード ("types_only", "deps_only", "full")

    Returns:
        対応するAnalyzerインスタンス

    Raises:
        ValueError: 無効なmodeが指定された場合
    """
    if mode == "types_only":
        from src.core.analyzer.type_inferrer import TypeInferenceAnalyzer

        return TypeInferenceAnalyzer(config)
    elif mode == "deps_only":
        from src.core.analyzer.dependency_extractor import (
            DependencyExtractionAnalyzer,
        )

        return DependencyExtractionAnalyzer(config)
    elif mode == "full":
        return FullAnalyzer(config)
    else:
        raise ValueError(
            f"無効な解析モード: {mode}. "
            "'types_only', 'deps_only', 'full' のいずれかを指定してください。"
        )


def get_supported_modes() -> list[str]:
    """
    サポートされている解析モードのリストを返します。

    Returns:
        モードのリスト
    """
    return ["types_only", "deps_only", "full"]
