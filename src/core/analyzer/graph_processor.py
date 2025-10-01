"""
グラフ処理モジュール

NetworkXを活用したグラフ分析、視覚化、YAML変換を提供します。
TypeDependencyGraphを基盤に高度なグラフ操作を実行します。
"""

from pathlib import Path
from typing import Any, Union, TYPE_CHECKING

try:
    import networkx as nx
except ImportError:
    nx = None

if TYPE_CHECKING:
    from pydot import Dot, Node, Edge
else:
    try:
        from pydot import Dot, Node, Edge
    except ImportError:
        Dot, Node, Edge = None, None, None  # type: ignore[assignment, misc]

from src.core.schemas.graph_types import TypeDependencyGraph


class GraphProcessor:
    """
    TypeDependencyGraphの処理と分析を行うクラス

    NetworkXを内部で使用し、視覚化や分析を提供します。
    """

    def __init__(self) -> None:
        """プロセッサを初期化"""
        self.nx_available = nx is not None
        if not self.nx_available:
            print(
                "警告: networkxがインストールされていません。一部の機能が制限されます。"
            )

    def analyze_cycles(self, graph: TypeDependencyGraph) -> list[list[str]]:
        """
        グラフから循環依存を検出します。

        Args:
            graph: 分析対象のTypeDependencyGraph

        Returns:
            循環パスのリスト（各パスはノード名のリスト）
        """
        if nx is None:
            return []
        nx_graph = graph.to_networkx()
        cycles = list(nx.simple_cycles(nx_graph))
        return cycles

    def compute_graph_metrics(self, graph: TypeDependencyGraph) -> dict[str, Any]:
        """
        グラフのメトリクスを計算します。

        Args:
            graph: 分析対象のTypeDependencyGraph

        Returns:
            メトリクスの辞書（ノード数、エッジ数、密度など）
        """
        if nx is None:
            return {
                "node_count": len(graph.nodes),
                "edge_count": len(graph.edges),
                "density": 0.0,
                "is_directed": True,  # 仮定
            }
        nx_graph = graph.to_networkx()
        metrics = {
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
            "density": nx.density(nx_graph),
            "is_directed": nx_graph.is_directed(),
        }
        if nx_graph.is_directed():
            metrics["strongly_connected_components"] = list(
                nx.strongly_connected_components(nx_graph)
            )
            metrics["weakly_connected_components"] = list(
                nx.weakly_connected_components(nx_graph)
            )
        else:
            metrics["connected_components"] = list(nx.connected_components(nx_graph))
        return metrics

    def visualize_graph(
        self,
        graph: TypeDependencyGraph,
        output_path: Union[Path, str],
        format_type: str = "png",
        layout: str = "spring",
    ) -> None:
        """
        グラフを視覚化して画像ファイルに保存します。

        Args:
            graph: 視覚化対象のTypeDependencyGraph
            output_path: 出力ファイルパス
            format_type: 出力形式（png, pdf, dotなど）
            layout: レイアウトアルゴリズム（spring, circularなど）

        Raises:
            ImportError: 必要なライブラリがインストールされていない場合
            ValueError: 無効なformat_typeの場合
        """
        if nx is None:
            raise ImportError("networkx is required for visualization")
        if TYPE_CHECKING:
            # 型チェック時はpydotは常に利用可能
            pass
        elif Dot is None or Node is None or Edge is None:  # type: ignore[unreachable]
            raise ImportError("pydot is required for visualization")

        nx_graph = graph.to_networkx()

        # Pydotグラフ作成
        dot_graph = Dot(graph_type="digraph", rankdir="TB")

        # ノード追加
        for node_id, node_data in nx_graph.nodes(data=True):
            node_label = f"{node_id}\\n({node_data.get('node_type', 'unknown')})"
            dot_node = Node(
                node_id,
                label=node_label,
                shape="box" if node_data.get("node_type") == "class" else "ellipse",
                color="red"
                if node_data.get("node_type") == "inferred_variable"
                else "black",
            )
            dot_graph.add_node(dot_node)

        # エッジ追加
        for source, target, edge_data in nx_graph.edges(data=True):
            edge_label = f"{edge_data.get('relation_type', 'unknown')} ({edge_data.get('weight', 1.0)})"
            dot_edge = Edge(
                source, target, label=edge_label, color="blue", fontcolor="blue"
            )
            dot_graph.add_edge(dot_edge)

        # ファイル保存
        output_path = Path(output_path)
        if format_type == "png":
            dot_graph.write_png(str(output_path))
        elif format_type == "pdf":
            dot_graph.write_pdf(str(output_path))
        elif format_type == "dot":
            dot_graph.write_dot(str(output_path))
        else:
            raise ValueError(f"サポートされていない形式: {format_type}")

    def convert_graph_to_yaml_spec(self, graph: TypeDependencyGraph) -> dict[str, Any]:
        """
        依存グラフをYAML型仕様に変換します。

        Args:
            graph: 依存関係のTypeDependencyGraph

        Returns:
            YAML型仕様の辞書
        """
        dependencies = {}

        for node in graph.nodes:
            if not node.id:
                continue  # idがないノードはスキップ
            node_type = node.node_type
            predecessors = [e.source for e in graph.get_edges_to(node.id)]
            successors = [e.target for e in graph.get_edges_from(node.id)]

            dependencies[node.name] = {
                "type": node_type,
                "depends_on": predecessors,
                "used_by": successors,
                "relations": [e.relation_type for e in graph.get_edges_to(node.id)],
                "attributes": node.attributes,
            }

        return {"dependencies": dependencies}

    def export_graphml(
        self, graph: TypeDependencyGraph, output_path: Union[Path, str]
    ) -> None:
        """
        グラフをGraphML形式でエクスポートします。

        Args:
            graph: エクスポート対象のTypeDependencyGraph
            output_path: 出力ファイルパス
        """
        if nx is None:
            raise ImportError("networkx is required for export_graphml")
        nx_graph = graph.to_networkx()
        nx.write_graphml(nx_graph, str(output_path))

    def import_graphml(self, file_path: Union[Path, str]) -> TypeDependencyGraph:
        """
        GraphMLファイルからグラフをインポートします。

        Args:
            file_path: GraphMLファイルパス

        Returns:
            インポートされたTypeDependencyGraph
        """
        if nx is None:
            raise ImportError("networkx is required for import_graphml")

        nx_graph = nx.read_graphml(str(file_path))
        return TypeDependencyGraph.from_networkx(nx_graph)
