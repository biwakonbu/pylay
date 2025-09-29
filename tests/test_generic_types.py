"""
複雑なジェネリック型のテスト
"""

import networkx as nx
from core.converters.extract_deps import extract_dependencies_from_code


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

        assert isinstance(graph, nx.DiGraph)
        assert "Dict" in graph.nodes()
        assert "Dict[str, List[int]]" in graph.nodes()
        assert "List" in graph.nodes()

    def test_union_types(self):
        """Union型のテスト"""
        code = """
from typing import Union

def handle(value: Union[str, int]) -> Union[List[str], Dict[str, int]]:
    return []
"""
        graph = extract_dependencies_from_code(code)

        assert isinstance(graph, nx.DiGraph)
        assert "Union" in graph.nodes()
        assert "Union[str, int]" in graph.nodes()
        assert "Union[List[str], Dict[str, int]]" in graph.nodes()

    def test_optional_types(self):
        """Optional型のテスト"""
        code = """
from typing import Optional

def find(key: str) -> Optional[Dict[str, int]]:
    return None
"""
        graph = extract_dependencies_from_code(code)

        assert isinstance(graph, nx.DiGraph)
        assert "Optional" in graph.nodes()
        assert "Optional[Dict[str, int]]" in graph.nodes()

    def test_complex_nested_types(self):
        """複雑なネストされた型のテスト"""
        code = """
from typing import Dict, List, Union

data: Dict[str, List[Dict[str, Union[int, str]]]] = {}
"""
        graph = extract_dependencies_from_code(code)

        assert isinstance(graph, nx.DiGraph)
        assert "Dict[str, List[Dict[str, Union[int, str]]]]" in graph.nodes()

    def test_python_310_union_syntax(self):
        """Python 3.10+ のUnion構文（str | int）のテスト"""
        code = """
def combine(a: str | int) -> list[str] | dict[str, int]:
    return []
"""
        graph = extract_dependencies_from_code(code)

        assert isinstance(graph, nx.DiGraph)
        assert "str | int" in graph.nodes()
        assert "list[str] | dict[str, int]" in graph.nodes()

    def test_union_in_generic_types(self):
        """Generic型内のUnionテスト（List[str | int]など）"""
        code = """
from typing import List

def process_items(items: List[str | int]) -> List[str]:
    return [str(item) for item in items]
"""
        graph = extract_dependencies_from_code(code)

        assert isinstance(graph, nx.DiGraph)
        assert "List" in graph.nodes()
        assert "List[str | int]" in graph.nodes()
