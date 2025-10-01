"""
複雑なジェネリック型のテスト
"""

from src.core.converters.extract_deps import extract_dependencies_from_code
from src.core.schemas.graph_types import TypeDependencyGraph


class TestGenericTypes:
    """ジェネリック型のテストクラス"""

    def test_nested_generic_types(self):
        """ネストされたジェネリック型のテスト"""
        code = """
from typing import Dict, List

def process(data: Dict[str, List[int]]) -> Dict[str, str]:
    return {}
"""
        graph = extract_dependencies_from_code(code)

        assert isinstance(graph, TypeDependencyGraph)
        node_names = [node.name for node in graph.nodes]
        assert "Dict" in node_names
        assert "Dict[str, List[int]]" in node_names
        assert "List" in node_names

    def test_union_types(self):
        """Union型のテスト

        Union[str, int] などの型が正しく依存グラフに含まれることを確認します。
        """
        code = """
from typing import Union

def handle(value: Union[str, int]) -> Union[List[str], Dict[str, int]]:
    return []
"""
        graph = extract_dependencies_from_code(code)

        assert isinstance(graph, TypeDependencyGraph)
        node_names = [node.name for node in graph.nodes]
        assert "Union" in node_names
        assert "Union[str, int]" in node_names
        assert "Union[List[str], Dict[str, int]]" in node_names

    def test_optional_types(self):
        """Optional型のテスト

        Optional[Dict[str, int]] などの型が正しく依存グラフに含まれることを確認します。
        """
        code = """
from typing import Optional

def find(key: str) -> Optional[Dict[str, int]]:
    return None
"""
        graph = extract_dependencies_from_code(code)

        assert isinstance(graph, TypeDependencyGraph)
        node_names = [node.name for node in graph.nodes]
        assert "Optional" in node_names
        assert "Optional[Dict[str, int]]" in node_names

    def test_complex_nested_types(self):
        """複雑なネストされた型のテスト"""
        code = """
from typing import Dict, List, Union

data: Dict[str, List[Dict[str, Union[int, str]]]] = {}
"""
        graph = extract_dependencies_from_code(code)

        assert isinstance(graph, TypeDependencyGraph)
        node_names = [node.name for node in graph.nodes]
        assert "Dict[str, List[Dict[str, Union[int, str]]]]" in node_names

    def test_python_310_union_syntax(self):
        """Python 3.10+ のUnion構文（str | int）のテスト

        Python 3.10+ の新しいUnion構文（str | int）が正しく処理されることを確認します。
        """
        code = """
def combine(a: str | int) -> list[str] | dict[str, int]:
    return []
"""
        graph = extract_dependencies_from_code(code)

        assert isinstance(graph, TypeDependencyGraph)
        node_names = [node.name for node in graph.nodes]
        assert "str | int" in node_names
        assert "list[str] | dict[str, int]" in node_names

    def test_union_in_generic_types(self):
        """Generic型内のUnionテスト（List[str | int]など）

        ジェネリック型内にUnionが含まれる場合の処理をテストします。
        """
        code = """
from typing import List

def process_items(items: List[str | int]) -> List[str]:
    return [str(item) for item in items]
"""
        graph = extract_dependencies_from_code(code)

        assert isinstance(graph, TypeDependencyGraph)
        node_names = [node.name for node in graph.nodes]
        assert "List" in node_names
        assert "List[str | int]" in node_names
