"""
NetworkXグラフアダプター。
TypeDependencyGraphをNetworkX DiGraphに変換し、視覚化やアルゴリズムを適用。
"""

from pathlib import Path
from typing import Any

import networkx as nx

from core.schemas.graph_types import TypeDependencyGraph


class NetworkXGraphAdapter:
    """
    TypeDependencyGraphをNetworkX DiGraphに変換するアダプター。
    視覚化、アルゴリズム適用、分析機能を追加。
    """

    def __init__(self, graph: TypeDependencyGraph):
        """アダプターを初期化"""
        self.graph = graph
        self.nx_graph: nx.DiGraph | None = None
        self._build_networkx_graph()

    def _build_networkx_graph(self) -> None:
        """TypeDependencyGraphからNetworkX DiGraphを構築"""
        self.nx_graph = nx.DiGraph()

        # ノードを追加
        for node in self.graph.nodes:
            self.nx_graph.add_node(
                node.name,
                node_type=node.node_type,
                attributes=node.attributes,
                qualified_name=node.qualified_name,
                is_external=node.is_external(),
            )

        # エッジを追加
        for edge in self.graph.edges:
            self.nx_graph.add_edge(
                edge.source,
                edge.target,
                relation_type=edge.relation_type,
                weight=edge.weight,
                metadata=edge.metadata,
                is_strong=edge.is_strong_dependency(),
            )

    def get_networkx_graph(self) -> nx.DiGraph:
        """NetworkXグラフを取得"""
        if self.nx_graph is None:
            self._build_networkx_graph()
        assert self.nx_graph is not None  # 型チェッカーのため
        return self.nx_graph

    def detect_cycles(self) -> list[list[str]]:
        """循環参照を検出"""
        assert self.nx_graph is not None
        try:
            return list(nx.simple_cycles(self.nx_graph))
        except nx.NetworkXNoCycle:
            return []

    def get_topological_sort(self) -> list[str]:
        """トポロジカルソートを取得（依存関係の解決順序）"""
        assert self.nx_graph is not None
        try:
            return list(nx.topological_sort(self.nx_graph))
        except nx.NetworkXError:
            # 循環がある場合はエラー
            return []

    def get_strongly_connected_components(self) -> list[set[str]]:
        """強連結成分を取得（循環のグループ化）"""
        assert self.nx_graph is not None
        return list(nx.strongly_connected_components(self.nx_graph))

    def calculate_centrality(self) -> dict[str, float]:
        """中心性（重要度）を計算"""
        assert self.nx_graph is not None
        if len(self.nx_graph.nodes) == 0:
            return {}

        # 次数中心性
        return dict(nx.degree_centrality(self.nx_graph))

    def calculate_betweenness_centrality(self) -> dict[str, float]:
        """媒介中心性を計算"""
        assert self.nx_graph is not None
        if len(self.nx_graph.nodes) == 0:
            return {}

        return dict(nx.betweenness_centrality(self.nx_graph))

    def get_dependency_paths(self, source: str, target: str) -> list[list[str]]:
        """2つのノード間の依存パスを取得"""
        assert self.nx_graph is not None
        try:
            paths = list(nx.all_simple_paths(self.nx_graph, source, target))
            return paths
        except nx.NetworkXNoPath:
            return []

    def get_subgraph_by_type(self, node_type: str) -> nx.DiGraph:
        """指定されたノードタイプのサブグラフを取得"""
        assert self.nx_graph is not None
        nodes_of_type = [
            node.name for node in self.graph.nodes if node.node_type == node_type
        ]
        return self.nx_graph.subgraph(nodes_of_type)

    def get_strong_dependency_subgraph(self) -> nx.DiGraph:
        """強い依存関係のみのサブグラフを取得"""
        assert self.nx_graph is not None
        strong_edges = [
            (edge.source, edge.target)
            for edge in self.graph.edges
            if edge.is_strong_dependency()
        ]
        return self.nx_graph.edge_subgraph(strong_edges)

    def export_to_graphml(self, output_path: Path) -> None:
        """GraphML形式でエクスポート"""
        assert self.nx_graph is not None
        nx.write_graphml(self.nx_graph, output_path)

    def export_to_dot(self, output_path: Path) -> None:
        """DOT形式でエクスポート（Graphviz用）"""
        assert self.nx_graph is not None
        nx.drawing.nx_pydot.write_dot(self.nx_graph, output_path)

    def generate_svg_from_dot(self, dot_path: Path, svg_path: Path) -> None:
        """DOTファイルからSVGを生成"""
        try:
            import subprocess

            # dotコマンドでSVGを生成
            result = subprocess.run(
                ["dot", "-Tsvg", str(dot_path), "-o", str(svg_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                print(f"⚠️  SVG生成エラー: {result.stderr}")
            else:
                print(f"✅ SVGファイルを生成: {svg_path}")
        except FileNotFoundError:
            print(
                "⚠️  Graphvizのdotコマンドが見つかりません。"
                "sudo apt install graphviz を実行してください。"
            )
        except subprocess.TimeoutExpired:
            print("⚠️  SVG生成がタイムアウトしました。")
        except Exception as e:
            print(f"⚠️  SVG生成エラー: {e}")

    def create_visualization_graph(self) -> nx.DiGraph:
        """視覚化用のグラフを作成（スタイル付き）"""
        assert self.nx_graph is not None
        vis_graph = self.nx_graph.copy()

        # ノードのスタイル設定
        for node_name in vis_graph.nodes:
            node_data = vis_graph.nodes[node_name]
            node_type = node_data.get("node_type", "unknown")

            # スタイル設定
            if node_type == "class":
                node_data["shape"] = "box"
                node_data["style"] = "filled"
                node_data["fillcolor"] = "lightblue"
            elif node_type == "function":
                node_data["shape"] = "ellipse"
                node_data["style"] = "filled"
                node_data["fillcolor"] = "lightgreen"
            elif node_type == "variable":
                node_data["shape"] = "diamond"
                node_data["style"] = "filled"
                node_data["fillcolor"] = "lightyellow"
            elif node_type == "module":
                node_data["shape"] = "hexagon"
                node_data["style"] = "filled"
                node_data["fillcolor"] = "lightgray"
            else:
                node_data["shape"] = "circle"
                node_data["style"] = "filled"
                node_data["fillcolor"] = "white"

        # エッジのスタイル設定
        for source, target, edge_data in vis_graph.edges(data=True):
            relation_type = edge_data.get("relation_type", "unknown")
            weight = edge_data.get("weight", 1.0)

            # 関係によるスタイル
            if relation_type == "inherits":
                edge_data["color"] = "blue"
                edge_data["style"] = "solid"
            elif relation_type == "references":
                edge_data["color"] = "green"
                edge_data["style"] = "dashed"
            elif relation_type == "calls":
                edge_data["color"] = "red"
                edge_data["style"] = "dotted"
            else:
                edge_data["color"] = "black"
                edge_data["style"] = "solid"

            # 重みによる太さ
            edge_data["penwidth"] = str(max(1.0, weight * 3))

        return vis_graph

    def export_visualization(
        self, dot_path: Path, svg_path: Path | None = None
    ) -> None:
        """視覚化用グラフをDOTとSVGでエクスポート"""
        vis_graph = self.create_visualization_graph()

        # DOT出力
        nx.drawing.nx_pydot.write_dot(vis_graph, dot_path)

        # SVG出力（オプション）
        if svg_path:
            self.generate_svg_from_dot(dot_path, svg_path)

    def get_graph_statistics(self) -> dict[str, Any]:
        """グラフの統計情報を取得"""
        assert self.nx_graph is not None
        if self.nx_graph is None:
            return {}

        return {
            "node_count": self.nx_graph.number_of_nodes(),
            "edge_count": self.nx_graph.number_of_edges(),
            "density": nx.density(self.nx_graph),
            "is_dag": nx.is_directed_acyclic_graph(self.nx_graph),
            "cycles_count": len(self.detect_cycles()),
            "components_count": nx.number_strongly_connected_components(self.nx_graph),
            "average_degree": sum(dict(self.nx_graph.degree()).values())
            / max(1, self.nx_graph.number_of_nodes()),
        }

    def get_node_statistics(self) -> dict[str, dict[str, Any]]:
        """各ノードの統計情報を取得"""
        assert self.nx_graph is not None
        stats = {}

        for node_name in self.nx_graph.nodes:
            node = self.graph.get_node_by_name(node_name)
            if node:
                in_edges = list(self.nx_graph.in_edges(node_name))
                out_edges = list(self.nx_graph.out_edges(node_name))

                stats[node_name] = {
                    "type": node.node_type,
                    "is_external": node.is_external(),
                    "in_degree": len(in_edges),
                    "out_degree": len(out_edges),
                    "total_degree": len(in_edges) + len(out_edges),
                }

        return stats

    def get_edge_statistics(self) -> dict[str, dict[str, Any]]:
        """各エッジの統計情報を取得"""
        assert self.nx_graph is not None
        stats = {}

        for source, target, data in self.nx_graph.edges(data=True):
            edge = self.graph.get_edges_by_source(source)[
                0
            ]  # 簡易的に最初のエッジを取得
            if edge:
                stats[f"{source}->{target}"] = {
                    "relation_type": edge.relation_type,
                    "weight": edge.weight,
                    "is_strong": edge.is_strong_dependency(),
                    "strength": edge.get_dependency_strength(),
                }

        return stats
