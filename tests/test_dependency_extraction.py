"""
依存関係抽出機能のテスト
"""

import networkx as nx
from core.converters.extract_deps import (
    extract_dependencies_from_code,
    convert_graph_to_yaml_spec,
)


class TestDependencyExtraction:
    """依存関係抽出機能のテストクラス"""

    def test_extract_function_dependencies(self):
        """関数依存関係の抽出テスト"""
        code = """
def func(x: int) -> str:
    return str(x)

y: int = 5
"""
        graph = extract_dependencies_from_code(code)

        assert isinstance(graph, nx.DiGraph)
        # ノードとエッジが存在することを確認
        assert len(graph.nodes) > 0

    def test_extract_class_dependencies(self):
        """クラス依存関係の抽出テスト"""
        code = """
class MyClass:
    def method(self) -> int:
        return 42
"""
        graph = extract_dependencies_from_code(code)

        assert isinstance(graph, nx.DiGraph)

    def test_convert_graph_to_yaml_spec(self):
        """グラフからYAML仕様への変換テスト"""
        code = """
x: int = 5
"""
        graph = extract_dependencies_from_code(code)
        yaml_spec = convert_graph_to_yaml_spec(graph)

        assert "dependencies" in yaml_spec
        assert isinstance(yaml_spec["dependencies"], dict)

    def test_empty_code(self):
        """空のコードに対するテスト"""
        graph = extract_dependencies_from_code("")
        assert isinstance(graph, nx.DiGraph)
        assert len(graph.nodes) == 0
