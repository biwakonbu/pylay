"""
依存関係抽出機能のテストモジュール。
AST抽出、ドキュメント生成、YAML統合を検証。
"""

import tempfile
import pytest
from pathlib import Path

from converters.ast_dependency_extractor import ASTDependencyExtractor
from doc_generators.graph_doc_generator import GraphDocGenerator
from src.schemas.graph_types import TypeDependencyGraph, GraphNode, GraphEdge
from converters.type_to_yaml import type_to_yaml


class TestASTDependencyExtractor:
    """ASTDependencyExtractorのテスト"""

    def test_extract_from_simple_class(self):
        """シンプルなクラス定義からの抽出をテスト"""
        # テスト用のPythonコード
        code = '''
class User:
    def __init__(self, name: str):
        self.name = name

class Address:
    pass

user = User("test")
'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()

            extractor = ASTDependencyExtractor()
            graph = extractor.extract_dependencies(f.name)

            # ノードの存在確認
            node_names = {node.name for node in graph.nodes}
            assert 'User' in node_names
            assert 'Address' in node_names
            assert 'user' in node_names

            # エッジの確認（参照関係）
            edge_relations = {(edge.source, edge.target, edge.relation_type) for edge in graph.edges}
            # User.__init__ -> str (references)
            assert ('User.__init__', 'str', 'references') in edge_relations
            # user -> User (calls)

    def test_extract_from_inheritance(self):
        """継承関係からの抽出をテスト"""
        code = '''
class Base:
    pass

class Derived(Base):
    pass
'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()

            extractor = ASTDependencyExtractor()
            graph = extractor.extract_dependencies(f.name)

            # エッジの確認（継承関係）
            edge_relations = {(edge.source, edge.target, edge.relation_type) for edge in graph.edges}
            assert ('Derived', 'Base', 'inherits') in edge_relations


class TestGraphDocGenerator:
    """GraphDocGeneratorのテスト"""

    def test_generate_basic_graph_docs(self):
        """基本的なグラフドキュメント生成をテスト"""
        # サンプルグラフ
        nodes = [
            GraphNode(name='User', node_type='class'),
            GraphNode(name='str', node_type='type_alias')
        ]
        edges = [
            GraphEdge(source='User', target='str', relation_type='references')
        ]
        graph = TypeDependencyGraph(
            nodes=nodes,
            edges=edges,
            metadata={'node_count': 2, 'edge_count': 1}
        )

        generator = GraphDocGenerator()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            output_path = Path(f.name)
            generator.generate(output_path, graph=graph)

            # 出力ファイルの確認
            content = output_path.read_text(encoding='utf-8')
            assert '型依存関係グラフ' in content
            assert 'ノード一覧' in content
            assert 'エッジ一覧' in content
            assert 'User' in content
            assert 'references' in content


class TestYAMLIntegration:
    """YAML統合のテスト"""

    def test_type_to_yaml_with_dependencies(self):
        """依存情報を含むYAML出力をテスト"""

        # サンプル依存グラフ
        nodes = [GraphNode(name='User', node_type='class')]
        edges = [GraphEdge(source='User', target='str', relation_type='references')]
        graph = TypeDependencyGraph(nodes=nodes, edges=edges)

        # 依存付きYAML出力
        yaml_output = type_to_yaml(list, dependencies=graph, as_root=True)

        # 依存情報が含まれていることを確認
        assert 'dependencies' in yaml_output
        assert 'User' in str(yaml_output)
        assert 'references' in str(yaml_output)


def test_end_to_end_dependency_extraction():
    """エンドツーエンドの依存抽出テスト"""
    code = '''

class User:
    name: str
    addresses: list[str]

class Address:
    pass

def get_user() -> User:
    return User()
'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        f.flush()

        # 1. 依存抽出
        extractor = ASTDependencyExtractor()
        graph = extractor.extract_dependencies(f.name)

        # 2. ドキュメント生成
        generator = GraphDocGenerator()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as md_file:
            generator.generate(Path(md_file.name), graph=graph)

        # 3. YAML統合テスト
        class User:
            name: str
            addresses: list[str]

        yaml_output = type_to_yaml(User, dependencies=graph)

        # 基本的な検証
        assert len(graph.nodes) > 0
        assert len(graph.edges) > 0

        md_content = Path(md_file.name).read_text()
        assert '型依存関係グラフ' in md_content

        assert 'dependencies' in yaml_output
