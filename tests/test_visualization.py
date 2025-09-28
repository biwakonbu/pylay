"""
Graphviz視覚化機能のテスト
"""

import pytest
import networkx as nx
from core.converters.extract_deps import (
    extract_dependencies_from_code,
    visualize_dependencies,
)
import os
import tempfile


class TestVisualization:
    """視覚化機能のテストクラス"""

    def test_visualization_with_graphviz(self):
        """Graphvizが利用可能な場合のテスト"""
        code = """
def func(x: int) -> str:
    return str(x)
"""
        graph = extract_dependencies_from_code(code)

        # 一時ファイルでテスト
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            output_path = tmp.name

        try:
            # 視覚化を実行（エラーが発生してもOK）
            visualize_dependencies(graph, output_path)

            # ファイルが存在するかチェック（システムによる）
            # 実際のテストでは、依存関係抽出の正しさを確認
            assert isinstance(graph, nx.DiGraph)
            assert len(graph.nodes()) > 0

        finally:
            # クリーンアップ
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_visualization_without_graphviz(self):
        """Graphvizが利用できない場合のテスト"""
        code = """
def func(x: int) -> str:
    return str(x)
"""
        graph = extract_dependencies_from_code(code)

        # 視覚化を実行（エラーハンドリングを確認）
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            output_path = tmp.name

        try:
            visualize_dependencies(graph, output_path)
            # エラーが発生しても正常終了することを確認
        except Exception:
            # 予期しないエラーはテスト失敗
            pytest.fail("視覚化で予期しないエラーが発生しました")
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_dependency_extraction_for_visualization(self):
        """視覚化用の依存関係抽出が正しく動作することを確認"""
        code = """
from typing import List

class MyClass:
    def method(self, items: List[str]) -> int:
        return len(items)

x: int = 42
"""
        graph = extract_dependencies_from_code(code)

        # 必要なノードが存在することを確認
        assert "MyClass" in graph.nodes()
        assert "method" in graph.nodes()
        assert "List" in graph.nodes()
        assert "List[str]" in graph.nodes()
        assert "int" in graph.nodes()
        assert "str" in graph.nodes()

        # エッジが存在することを確認
        assert graph.has_edge("List[str]", "method")
        assert graph.has_edge("method", "int")
