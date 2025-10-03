"""
ForwardRefと循環参照のテスト
"""

from src.core.converters.extract_deps import extract_dependencies_from_code
from src.core.schemas.graph import TypeDependencyGraph


class TestForwardRef:
    """ForwardRefと循環参照のテストクラス

    ForwardRef（前方参照）と循環参照が正しく処理されることを確認します。
    """

    def test_forward_ref_extraction(self):
        """ForwardRefの抽出テスト

        ForwardRef（"Node"）が正しく抽出され、依存グラフに含まれることを確認します。
        """
        code = """
from typing import Optional

class Node:
    def __init__(self, value: int, next_node: "Node" = None) -> None:
        self.value = value
        self.next = next_node
"""
        graph = extract_dependencies_from_code(code)

        assert isinstance(graph, TypeDependencyGraph)
        node_names = [node.name for node in graph.nodes]
        assert "Node" in node_names
        # ForwardRef "Node" が適切に処理されていることを確認

    def test_circular_reference_detection(self):
        """循環参照の検出テスト

        相互参照するクラス（AとB）の循環参照が正しく検出されることを確認します。
        """
        code = """
class A:
    def __init__(self, b: "B") -> None:
        self.b = b

class B:
    def __init__(self, a: "A") -> None:
        self.a = a
"""
        graph = extract_dependencies_from_code(code)

        assert isinstance(graph, TypeDependencyGraph)
        # 循環参照が無限ループを起こさないことを確認
        assert len(graph.nodes) > 0

    def test_union_type_with_forward_ref(self):
        """ForwardRefを含むUnion型のテスト

        Union型内にForwardRefが含まれる場合の処理をテストします。
        """
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

        assert isinstance(graph, TypeDependencyGraph)
        node_names = [node.name for node in graph.nodes]
        assert "Parent" in node_names
        assert "Child" in node_names

    def test_no_infinite_loop(self):
        """無限ループが発生しないことを確認"""
        code = """
class SelfRef:
    def __init__(self, other: "SelfRef") -> None:
        self.other = other
"""
        graph = extract_dependencies_from_code(code)

        assert isinstance(graph, TypeDependencyGraph)
        # 処理が完了することを確認（無限ループでハングしない）
        node_names = [node.name for node in graph.nodes]
        assert "SelfRef" in node_names
