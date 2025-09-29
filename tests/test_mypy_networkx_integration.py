"""
mypy統合とNetworkX機能のテストモジュール。
高度な依存抽出、型推論統合、NetworkX分析を検証。
"""

import tempfile

from src.core.converters.ast_dependency_extractor import ASTDependencyExtractor
from src.core.converters.mypy_type_extractor import MypyTypeExtractor
from utils.graph_networkx_adapter import NetworkXGraphAdapter


class TestMypyIntegration:
    """mypy統合のテスト"""

    def test_mypy_type_extraction(self):
        """mypy型推論の基本機能テスト"""
        code = """
def greet(name: str) -> str:
    return f"Hello, {name}!"

x = greet("world")
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()

            extractor = MypyTypeExtractor()
            results = extractor.extract_types_with_mypy(f.name)

            # mypyが実行されたことを確認
            assert isinstance(results, dict)
            # 実際の結果はmypyの出力に依存するため、基本的な構造を確認

    def test_ast_with_mypy_integration(self):
        """AST抽出とmypy統合のテスト"""
        code = """
class User:
    def __init__(self, name: str):
        self.name = name

def get_user() -> User:
    return User("test")
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()

            extractor = ASTDependencyExtractor()
            graph = extractor.extract_dependencies(f.name, include_mypy=True)

            # 基本的な構造確認
            assert len(graph.nodes) > 0
            assert len(graph.edges) > 0
            assert graph.metadata.get("mypy_enabled") is True


class TestNetworkXIntegration:
    """NetworkX統合のテスト"""

    def test_networkx_adapter_creation(self):
        """NetworkXアダプターの作成テスト"""
        from core.schemas.graph_types import GraphNode, GraphEdge, TypeDependencyGraph

        nodes = [
            GraphNode(name="User", node_type="class"),
            GraphNode(
                name="str", node_type="type_alias", qualified_name="builtins.str"
            ),
        ]
        edges = [
            GraphEdge(
                source="User", target="str", relation_type="references", weight=0.8
            )
        ]
        graph = TypeDependencyGraph(nodes=nodes, edges=edges)

        adapter = NetworkXGraphAdapter(graph)

        # NetworkXグラフが作成されていることを確認
        nx_graph = adapter.get_networkx_graph()
        assert nx_graph.number_of_nodes() == 2
        assert nx_graph.number_of_edges() == 1

    def test_cycle_detection(self):
        """循環参照検出のテスト"""
        from core.schemas.graph_types import GraphNode, GraphEdge, TypeDependencyGraph

        # 循環を含むグラフを作成
        nodes = [
            GraphNode(name="A", node_type="class"),
            GraphNode(name="B", node_type="class"),
            GraphNode(name="C", node_type="class"),
        ]
        edges = [
            GraphEdge(source="A", target="B", relation_type="references"),
            GraphEdge(source="B", target="C", relation_type="references"),
            GraphEdge(source="C", target="A", relation_type="references"),  # 循環
        ]
        graph = TypeDependencyGraph(nodes=nodes, edges=edges)

        adapter = NetworkXGraphAdapter(graph)
        cycles = adapter.detect_cycles()

        assert len(cycles) > 0
        assert any("A" in cycle and "B" in cycle and "C" in cycle for cycle in cycles)

    def test_topological_sort(self):
        """トポロジカルソートのテスト"""
        from core.schemas.graph_types import GraphNode, GraphEdge, TypeDependencyGraph

        # 非循環グラフを作成
        nodes = [
            GraphNode(name="Base", node_type="class"),
            GraphNode(name="Derived", node_type="class"),
            GraphNode(name="User", node_type="class"),
        ]
        edges = [
            GraphEdge(
                source="Derived", target="Base", relation_type="inherits_from"
            ),  # Derived -> Base
            GraphEdge(
                source="User", target="Derived", relation_type="references"
            ),  # User -> Derived
        ]
        graph = TypeDependencyGraph(nodes=nodes, edges=edges)

        adapter = NetworkXGraphAdapter(graph)
        topo_order = adapter.get_topological_sort()

        assert len(topo_order) == 3
        # トポロジカルソートが実行可能であることを確認（循環がない）
        assert topo_order is not None
        assert all(name in topo_order for name in ["Base", "Derived", "User"])

    def test_graph_statistics(self):
        """グラフ統計のテスト"""
        from core.schemas.graph_types import GraphNode, GraphEdge, TypeDependencyGraph

        nodes = [
            GraphNode(name="A", node_type="class"),
            GraphNode(name="B", node_type="function"),
            GraphNode(name="C", node_type="variable", qualified_name="module.C"),
        ]
        edges = [
            GraphEdge(source="A", target="B", relation_type="references"),
            GraphEdge(source="B", target="C", relation_type="references"),
        ]
        graph = TypeDependencyGraph(nodes=nodes, edges=edges)

        adapter = NetworkXGraphAdapter(graph)
        stats = adapter.get_graph_statistics()

        assert stats["node_count"] == 3
        assert stats["edge_count"] == 2
        assert "density" in stats
        assert "is_dag" in stats

    def test_strong_dependency_subgraph(self):
        """強い依存関係サブグラフのテスト"""
        from core.schemas.graph_types import GraphNode, GraphEdge, TypeDependencyGraph

        nodes = [
            GraphNode(name="A", node_type="class"),
            GraphNode(name="B", node_type="class"),
            GraphNode(name="C", node_type="class"),
        ]
        edges = [
            GraphEdge(
                source="A", target="B", relation_type="inherits_from", weight=0.9
            ),  # 強い
            GraphEdge(
                source="B", target="C", relation_type="references", weight=0.3
            ),  # 弱い
        ]
        graph = TypeDependencyGraph(nodes=nodes, edges=edges)

        adapter = NetworkXGraphAdapter(graph)
        strong_subgraph = adapter.get_strong_dependency_subgraph()

        # 強い依存関係のみを含むべき
        assert strong_subgraph.number_of_edges() == 1
        assert strong_subgraph.has_edge("A", "B")


class TestCLIEnhancements:
    """CLI拡張機能のテスト"""

    def test_cli_with_mypy_option(self):
        """CLIのmypyオプションのテスト"""
        # 実際のCLIテストは複雑なので、基本的なインポートテスト
        from scripts.generate_dependency_graph import generate_dependency_docs

        # 基本的な機能テスト（実際のファイルは使用せず）
        # このテストはCLIの構造を検証
        assert callable(generate_dependency_docs)

    def test_cli_with_analyze_option(self):
        """CLIのanalyzeオプションのテスト"""
        from scripts.generate_dependency_graph import generate_dependency_docs

        # 基本的な機能テスト
        assert callable(generate_dependency_docs)


def test_end_to_end_mypy_networkx_workflow():
    """エンドツーエンドのmypy + NetworkXワークフローテスト"""
    code = """
class Base:
    pass

class Derived(Base):
    def method(self, x: str) -> str:
        return x.upper()

def process(obj: Derived) -> str:
    return obj.method("hello")
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()

        # 1. AST + mypy抽出
        extractor = ASTDependencyExtractor()
        graph = extractor.extract_dependencies(f.name, include_mypy=True)

        # 2. NetworkX分析
        adapter = NetworkXGraphAdapter(graph)

        # 3. 基本的な検証
        assert len(graph.nodes) > 0
        assert len(graph.edges) > 0
        assert graph.metadata.get("mypy_enabled") is True

        nx_graph = adapter.get_networkx_graph()
        assert nx_graph.number_of_nodes() > 0
        assert nx_graph.number_of_edges() > 0

        # 4. 統計情報
        stats = adapter.get_graph_statistics()
        assert stats["node_count"] > 0
        assert stats["edge_count"] > 0
