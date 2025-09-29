"""
解析エンジンの基底モジュール

Analyzerインターフェースとファクトリ関数を提供します。
解析部分を他のコンポーネントから疎結合に利用するための基盤です。
"""

from abc import ABC, abstractmethod
from pathlib import Path

from src.core.schemas.graph_types import TypeDependencyGraph, GraphEdge, RelationType
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


# 実装クラスは別ファイルで定義（循環import回避）


class FullAnalyzer(Analyzer):
    """
    型推論と依存抽出を組み合わせたAnalyzer

    完全な解析を実行します。
    """

    def __init__(self, config: PylayConfig) -> None:
        super().__init__(config)
        from src.core.analyzer.type_inferrer import (
            TypeInferenceAnalyzer as TypeInfAnalyzer,
        )
        from src.core.analyzer.dependency_extractor import (
            DependencyExtractionAnalyzer as DepAnalyzer,
        )

        self.type_analyzer = TypeInfAnalyzer(config)
        self.dep_analyzer = DepAnalyzer(config)

    def analyze(self, input_path: Path | str) -> TypeDependencyGraph:
        """完全解析を実行し、グラフを生成"""
        # 型推論
        inferred_graph = self.type_analyzer.analyze(input_path)

        # 依存抽出
        dep_graph = self.dep_analyzer.analyze(input_path)

        # マージ（依存グラフを基盤に推論ノードを追加）
        combined_nodes = list(dep_graph.nodes)
        combined_edges = list(dep_graph.edges)
        combined_metadata = dep_graph.metadata or {}

        # 推論ノードを追加
        for node in inferred_graph.nodes:
            if not any(n.name == node.name for n in combined_nodes):
                combined_nodes.append(node)

        # 推論エッジを追加（型依存）
        for node in inferred_graph.nodes:
            if node.attributes and "inferred_type" in node.attributes:
                type_str = node.attributes["inferred_type"]
                if type_str != "Any":
                    # 型参照を抽出してエッジ追加（簡易）
                    from src.core.analyzer.dependency_extractor import (
                        DependencyExtractionAnalyzer,
                    )

                    temp_analyzer = DependencyExtractionAnalyzer(self.config)
                    type_refs = temp_analyzer._extract_type_refs_from_string(
                        str(type_str)
                    )
                    for ref in type_refs:
                        if ref != node.name:
                            edge = GraphEdge(
                                source=node.name,
                                target=ref,
                                relation_type=RelationType.REFERENCES,
                                weight=0.5,
                            )
                            combined_edges.append(edge)

        # メタデータ更新
        combined_metadata.update(
            {
                "analysis_type": "full",
                "inferred_nodes_count": len(inferred_graph.nodes),
            }
        )

        return TypeDependencyGraph(
            nodes=combined_nodes,
            edges=combined_edges,
            metadata=combined_metadata,
        )


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
        from src.core.analyzer.type_inferrer import (
            TypeInferenceAnalyzer as TypeInfAnalyzer,
        )

        return TypeInfAnalyzer(config)
    elif mode == "deps_only":
        from src.core.analyzer.dependency_extractor import (
            DependencyExtractionAnalyzer as DepAnalyzer,
        )

        return DepAnalyzer(config)
    elif mode == "full":
        return FullAnalyzer(config)
    else:
        raise ValueError(
            f"無効な解析モード: {mode}. 'types_only', 'deps_only', 'full' のいずれかを指定してください。"
        )


def get_supported_modes() -> list[str]:
    """
    サポートされている解析モードのリストを返します。

    Returns:
        モードのリスト
    """
    return ["types_only", "deps_only", "full"]
