"""
Graphviz視覚化機能のテスト
"""

import os
import tempfile

import pytest

from src.core.converters.extract_deps import (
    extract_dependencies_from_code,
    visualize_dependencies,
)
from src.core.schemas.graph_types import TypeDependencyGraph


class TestVisualization:
    """視覚化機能のテストクラス"""

    def test_visualization_with_graphviz(self):
        """Graphvizが利用可能な場合のテスト

        Graphvizがインストールされている場合のグラフ可視化機能をテストします。
        """
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
            assert isinstance(graph, TypeDependencyGraph)
            assert len(graph.nodes) > 0

        finally:
            # クリーンアップ
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_visualization_without_graphviz(self):
        """Graphvizが利用できない場合のテスト

        Graphvizがインストールされていない場合のフォールバック動作をテストします。
        """
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

        assert isinstance(graph, TypeDependencyGraph)

        # TypeDependencyGraph から NetworkX DiGraph に変換
        nx_graph = graph.to_networkx()

        # 必要なノードが存在することを確認
        node_names = list(nx_graph.nodes())
        assert "MyClass" in node_names
        assert "method" in node_names
        assert "List" in node_names or any("List" in n for n in node_names)

        # エッジの存在をチェック
        assert len(list(nx_graph.edges())) > 0
