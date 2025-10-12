"""
グラフ理論関連の型定義テストモジュール。
GraphNode, GraphEdge, TypeDependencyGraphの基本機能とYAML変換を検証。
"""

import pytest
from pydantic import ValidationError

from src.core.schemas.graph import GraphEdge, GraphNode, TypeDependencyGraph


class TestGraphNode:
    """GraphNodeのテスト"""

    def test_valid_node_creation(self):
        """有効なノードの作成をテスト"""
        node = GraphNode(name="TestClass", node_type="class", attributes={"line": 10})
        assert node.name == "TestClass"
        assert node.node_type == "class"
        assert node.attributes == {"line": 10}

    def test_node_without_attributes(self):
        """属性なしのノード作成をテスト"""
        node = GraphNode(name="TestFunc", node_type="function")
        assert node.attributes is None

    def test_invalid_node_type(self):
        """unknown node_typeがデフォルトとして機能することをテスト"""
        node = GraphNode(name="Test", node_type="unknown")
        assert node.node_type == "unknown"


class TestGraphEdge:
    """GraphEdgeのテスト"""

    def test_valid_edge_creation(self):
        """有効なエッジの作成をテスト"""
        edge = GraphEdge(source="A", target="B", relation_type="inherits_from", weight=0.9)
        assert edge.source == "A"
        assert edge.target == "B"
        assert edge.relation_type == "inherits_from"
        assert edge.weight == 0.9

    def test_edge_default_weight(self):
        """デフォルトのweightをテスト"""
        edge = GraphEdge(source="X", target="Y", relation_type="references")
        assert edge.weight == 1.0

    def test_invalid_relation_type(self):
        """無効なrelation_typeでのエラーをテスト"""
        with pytest.raises(ValidationError):
            GraphEdge(source="A", target="B", relation_type="invalid_relation")


class TestTypeDependencyGraph:
    """TypeDependencyGraphのテスト"""

    def test_valid_graph_creation(self):
        """有効なグラフの作成をテスト"""
        nodes = [
            GraphNode(name="User", node_type="class"),
            GraphNode(name="Address", node_type="class"),
        ]
        edges = [GraphEdge(source="User", target="Address", relation_type="references")]
        metadata = {"generated_by": "AST_parser", "timestamp": "2025-09-27"}

        graph = TypeDependencyGraph(nodes=nodes, edges=edges, metadata=metadata)
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1
        assert graph.metadata == metadata

    def test_graph_without_metadata(self):
        """メタデータなしのグラフ作成をテスト"""
        nodes = [GraphNode(name="Test", node_type="class")]
        edges = []
        graph = TypeDependencyGraph(nodes=nodes, edges=edges)
        assert graph.metadata is None  # metadata は None がデフォルト

    def test_empty_graph(self):
        """空のグラフ作成をテスト"""
        graph = TypeDependencyGraph(nodes=[], edges=[])
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_graph_serialization(self):
        """グラフのYAMLシリアライズ/デシリアライズをテスト"""
        original_graph = TypeDependencyGraph(
            nodes=[GraphNode(name="Test", node_type="class")],
            edges=[],
            metadata={"version": "1.0"},
        )

        # model_dumpでシリアライズ
        data = original_graph.model_dump()

        # model_validateでデシリアライズ
        restored_graph = TypeDependencyGraph.model_validate(data)
        assert restored_graph.nodes[0].name == "Test"
        assert restored_graph.metadata == {"version": "1.0"}
