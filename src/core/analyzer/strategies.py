"""
型推論戦略

InferStrategyの抽象基底クラスと実装を提供します。
"""

from abc import ABC, abstractmethod
from pathlib import Path

from src.core.schemas.pylay_config import PylayConfig
from src.core.schemas.analyzer_types import InferResult


class InferStrategy(ABC):
    """
    型推論戦略の抽象基底クラス
    """

    def __init__(self, config: PylayConfig):
        self.config = config

    @abstractmethod
    def infer(self, file_path: Path) -> dict[str, InferResult]:
        """
        ファイルから型を推論します。

        Args:
            file_path: 推論対象のファイルパス

        Returns:
            推論結果の辞書
        """
        pass


class LooseStrategy(InferStrategy):
    """
    Looseモードの型推論戦略

    ASTのみを使用し、mypyを統合しない。
    """

    def infer(self, file_path: Path) -> dict[str, InferResult]:
        # AST解析のみ
        from src.core.analyzer.type_inferrer import TypeInferenceAnalyzer

        analyzer = TypeInferenceAnalyzer(self.config)
        # 簡易的に空を返す（実際にはAST推論を実装）
        return {}


class NormalStrategy(InferStrategy):
    """
    Normalモードの型推論戦略

    AST + mypyの基本統合。
    """

    def infer(self, file_path: Path) -> dict[str, InferResult]:
        from src.core.analyzer.type_inferrer import TypeInferenceAnalyzer

        analyzer = TypeInferenceAnalyzer(self.config)
        return analyzer.infer_types_from_file(str(file_path))


class StrictStrategy(InferStrategy):
    """
    Strictモードの型推論戦略

    AST + mypyの完全統合、厳密な型チェック。
    """

    def infer(self, file_path: Path) -> dict[str, InferResult]:
        from src.core.analyzer.type_inferrer import TypeInferenceAnalyzer

        analyzer = TypeInferenceAnalyzer(self.config)
        # 厳密モードではエラーを厳しく扱う
        try:
            return analyzer.infer_types_from_file(str(file_path))
        except RuntimeError:
            raise ValueError(f"Strictモードで型推論に失敗: {file_path}")


def create_infer_strategy(config: PylayConfig) -> InferStrategy:
    """
    設定に基づいてInferStrategyを作成します。

    Args:
        config: pylayの設定

    Returns:
        対応するInferStrategyインスタンス
    """
    if config.infer_level == "loose":
        return LooseStrategy(config)
    elif config.infer_level == "normal":
        return NormalStrategy(config)
    elif config.infer_level == "strict":
        return StrictStrategy(config)
    else:
        raise ValueError(f"無効なinfer_level: {config.infer_level}")
