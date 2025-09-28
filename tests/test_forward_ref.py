"""
ForwardRefと循環参照のテスト
"""

import pytest
import networkx as nx
from core.converters.extract_deps import extract_dependencies_from_code


class TestForwardRef:
    """ForwardRefと循環参照のテストクラス"""

    def test_forward_ref_extraction(self):
        """ForwardRefの抽出テスト"""
        code = """
from typing import Optional

class Node:
    def __init__(self, value: int, next_node: "Node" = None) -> None:
        self.value = value
        self.next = next_node
"""
        graph = extract_dependencies_from_code(code)

        assert isinstance(graph, nx.DiGraph)
        assert "Node" in graph.nodes()
        # ForwardRef "Node" が適切に処理されていることを確認

    def test_circular_reference_detection(self):
        """循環参照の検出テスト"""
        code = """
class A:
    def __init__(self, b: "B") -> None:
        self.b = b

class B:
    def __init__(self, a: "A") -> None:
        self.a = a
"""
        graph = extract_dependencies_from_code(code)

        assert isinstance(graph, nx.DiGraph)
        # 循環参照が無限ループを起こさないことを確認
        assert len(graph.nodes()) > 0

    def test_union_type_with_forward_ref(self):
        """ForwardRefを含むUnion型のテスト"""
        code = """
from typing import Union

class Parent:
    def __init__(self, child: Union["Child", None]) -> None:
        self.child = child

class Child:
    def __init__(self, parent: "Parent") -> None:
        self.parent = parent
"""
        graph = extract_dependencies_from_code(code)

        assert isinstance(graph, nx.DiGraph)
        assert "Parent" in graph.nodes()
        assert "Child" in graph.nodes()

    def test_no_infinite_loop(self):
        """無限ループが発生しないことを確認"""
        code = """
class SelfRef:
    def __init__(self, other: "SelfRef") -> None:
        self.other = other
"""
        graph = extract_dependencies_from_code(code)

        assert isinstance(graph, nx.DiGraph)
        # 処理が完了することを確認（無限ループでハングしない）
        assert "SelfRef" in graph.nodes()
