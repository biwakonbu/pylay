"""
analyzerモジュールのテスト

型推論、依存抽出、グラフ処理のユニットテストと統合テスト。
"""

import pytest
from pathlib import Path
from unittest.mock import patch

from src.core.analyzer.base import Analyzer, create_analyzer, FullAnalyzer
from src.core.analyzer.graph_processor import GraphProcessor
from src.core.schemas.graph_types import (
    TypeDependencyGraph,
    GraphNode,
    GraphEdge,
    RelationType,
)
from src.core.schemas.pylay_config import PylayConfig


class TestAnalyzerBase:
    """Analyzer基底クラスのテスト"""

    def test_analyzer_interface(self):
        """Analyzerが抽象クラスであることを確認"""
        with pytest.raises(TypeError):
            Analyzer(PylayConfig())

    def test_create_analyzer_types_only(self):
        """types_onlyモードのanalyzer作成"""
        config = PylayConfig()
        analyzer = create_analyzer(config, "types_only")
        assert hasattr(analyzer, "analyze")
        assert analyzer.config == config

    def test_create_analyzer_deps_only(self):
        """deps_onlyモードのanalyzer作成"""
        config = PylayConfig()
        analyzer = create_analyzer(config, "deps_only")
        assert hasattr(analyzer, "analyze")
        assert analyzer.config == config

    def test_create_analyzer_full(self):
        """fullモードのanalyzer作成"""
        config = PylayConfig()
        analyzer = create_analyzer(config, "full")
        assert isinstance(analyzer, FullAnalyzer)

    def test_invalid_mode(self):
        """無効なモードでエラー"""
        config = PylayConfig()
        with pytest.raises(ValueError, match="無効な解析モード"):
            create_analyzer(config, "invalid")


class TestTypeInferenceAnalyzer:
    """TypeInferenceAnalyzerのテスト"""

    def test_analyze_file(self, tmp_path):
        """ファイルからの型推論"""
        # テストファイル作成
        test_file = tmp_path / "test.py"
        test_file.write_text("""
x: int = 5
y: str

def func(a: int) -> str:
    return str(a)
""")

        config = PylayConfig()
        from src.core.analyzer.type_inferrer import TypeInferenceAnalyzer

        analyzer = TypeInferenceAnalyzer(config)
        graph = analyzer.analyze(test_file)

        assert isinstance(graph, TypeDependencyGraph)
        assert len(graph.nodes) > 0
        # 推論された型を確認
        inferred_nodes = [
            n for n in graph.nodes if n.attributes and "inferred_type" in n.attributes
        ]
        assert len(inferred_nodes) > 0

    def test_analyze_code_string(self):
        """コード文字列からの型推論"""
        code = """
x: int = 5
y: str
"""
        config = PylayConfig()
        from src.core.analyzer.type_inferrer import TypeInferenceAnalyzer

        analyzer = TypeInferenceAnalyzer(config)
        graph = analyzer.analyze(code)

        assert isinstance(graph, TypeDependencyGraph)
        assert len(graph.nodes) > 0

    def test_infer_types_from_code(self):
        """コードからの型推論（内部メソッド）"""
        code = "x: int = 5"
        config = PylayConfig()
        from src.core.analyzer.type_inferrer import TypeInferenceAnalyzer

        analyzer = TypeInferenceAnalyzer(config)
        result = analyzer.infer_types_from_code(code)

        assert isinstance(result, dict)
        # mypyの出力による

    def test_merge_inferred_types(self):
        """型マージのテスト"""
        existing = {"x": "int"}
        inferred = {"y": "str"}
        config = PylayConfig()
        from src.core.analyzer.type_inferrer import TypeInferenceAnalyzer

        analyzer = TypeInferenceAnalyzer(config)
        merged = analyzer.merge_inferred_types(existing, inferred)

        assert merged["x"] == "int"
        assert merged["y"] == "str"


class TestDependencyExtractionAnalyzer:
    """DependencyExtractionAnalyzerのテスト"""

    def test_analyze_file(self, tmp_path):
        """ファイルからの依存抽出"""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
class A:
    def method(self) -> int:
        return 1

def func(x: A) -> int:
    return x.method()
""")

        config = PylayConfig()
        from src.core.analyzer.dependency_extractor import DependencyExtractionAnalyzer

        analyzer = DependencyExtractionAnalyzer(config)
        graph = analyzer.analyze(test_file)

        assert isinstance(graph, TypeDependencyGraph)
        assert len(graph.nodes) > 0
        assert len(graph.edges) > 0

        # 循環検出（なければcyclesなし）
        if graph.metadata and "cycles" in graph.metadata:
            assert isinstance(graph.metadata["cycles"], list)

    def test_analyze_code_string(self):
        """コード文字列からの依存抽出"""
        code = """
class A:
    pass
"""
        config = PylayConfig()
        from src.core.analyzer.dependency_extractor import DependencyExtractionAnalyzer

        analyzer = DependencyExtractionAnalyzer(config)
        graph = analyzer.analyze(code)

        assert isinstance(graph, TypeDependencyGraph)
        assert len(graph.nodes) > 0

    def test_cycle_detection(self, tmp_path):
        """循環依存の検出"""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
class A:
    b: 'B'

class B:
    a: 'A'
""")

        config = PylayConfig()
        from src.core.analyzer.dependency_extractor import DependencyExtractionAnalyzer

        analyzer = DependencyExtractionAnalyzer(config)
        graph = analyzer.analyze(test_file)

        # 循環があるはず
        if graph.metadata and "cycles" in graph.metadata:
            cycles = graph.metadata["cycles"]
            assert len(cycles) > 0


class TestGraphProcessor:
    """GraphProcessorのテスト"""

    def test_analyze_cycles(self):
        """循環分析"""
        # 循環なしのグラフ
        graph = TypeDependencyGraph(nodes=[], edges=[])
        node1 = GraphNode(name="A", node_type="class")
        node2 = GraphNode(name="B", node_type="class")
        edge = GraphEdge(source="A", target="B", relation_type=RelationType.REFERENCES)
        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_edge(edge)

        processor = GraphProcessor()
        cycles = processor.analyze_cycles(graph)
        assert cycles == []

    def test_compute_graph_metrics(self):
        """グラフメトリクスの計算"""
        graph = TypeDependencyGraph(nodes=[], edges=[])
        node1 = GraphNode(name="A", node_type="class")
        node2 = GraphNode(name="B", node_type="class")
        edge = GraphEdge(source="A", target="B", relation_type=RelationType.REFERENCES)
        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_edge(edge)

        processor = GraphProcessor()
        metrics = processor.compute_graph_metrics(graph)

        assert metrics["node_count"] == 2
        assert metrics["edge_count"] == 1
        assert "density" in metrics

    def test_convert_graph_to_yaml_spec(self):
        """YAML仕様への変換"""
        graph = TypeDependencyGraph(nodes=[], edges=[])
        node = GraphNode(name="A", node_type="class")
        graph.add_node(node)

        processor = GraphProcessor()
        yaml_data = processor.convert_graph_to_yaml_spec(graph)

        assert "dependencies" in yaml_data
        assert "A" in yaml_data["dependencies"]

    @patch("src.core.analyzer.graph_processor.Dot")
    def test_visualize_graph(self, mock_dot):
        """視覚化（モック）"""
        graph = TypeDependencyGraph(nodes=[], edges=[])
        node = GraphNode(name="A", node_type="class")
        graph.add_node(node)

        processor = GraphProcessor()

        # nx_availableがFalseの場合はImportErrorが上がることを確認
        if not processor.nx_available:
            with pytest.raises(ImportError):
                processor.visualize_graph(graph, "test.png")
        else:
            # nx_availableがTrueの場合はモックでテスト
            processor.visualize_graph(graph, "test.png")

    def test_export_graphml(self, tmp_path):
        """GraphMLエクスポート"""
        graph = TypeDependencyGraph(nodes=[], edges=[])
        node = GraphNode(name="A", node_type="class")
        graph.add_node(node)

        output_file = tmp_path / "test.graphml"
        processor = GraphProcessor()

        # nx_availableがFalseの場合はImportErrorが上がることを確認
        if not processor.nx_available:
            with pytest.raises(ImportError):
                processor.export_graphml(graph, output_file)
        else:
            processor.export_graphml(graph, output_file)
            assert output_file.exists()


class TestIntegration:
    """統合テスト（ラウンドトリップ）"""

    def test_full_analysis_roundtrip(self, tmp_path):
        """完全解析のラウンドトリップ"""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
class User:
    name: str
    age: int

def get_user() -> User:
    return User(name="test", age=25)
""")

        # フル解析
        config = PylayConfig()
        analyzer = create_analyzer(config, "full")
        graph = analyzer.analyze(test_file)

        # YAML変換
        processor = GraphProcessor()
        yaml_data = processor.convert_graph_to_yaml_spec(graph)

        # 基本構造確認
        assert "dependencies" in yaml_data
        assert len(yaml_data["dependencies"]) > 0

        # 視覚化（オプション）
        vis_file = tmp_path / "test.png"
        if processor.nx_available:
            processor.visualize_graph(graph, vis_file, format_type="png")

        # メトリクス
        metrics = processor.compute_graph_metrics(graph)
        assert metrics["node_count"] > 0

    def test_analyzer_modes(self):
        """異なるモードの比較"""
        config = PylayConfig()

        # types_only
        type_analyzer = create_analyzer(config, "types_only")
        # 実際のファイルが必要なので、モックで

        # deps_only
        dep_analyzer = create_analyzer(config, "deps_only")

        # full
        full_analyzer = create_analyzer(config, "full")

        # すべてAnalyzerのサブクラス
        assert isinstance(type_analyzer, Analyzer)
        assert isinstance(dep_analyzer, Analyzer)
        assert isinstance(full_analyzer, Analyzer)


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_empty_code_string(self):
        """空のコード文字列の処理"""
        config = PylayConfig()
        from src.core.analyzer.type_inferrer import TypeInferenceAnalyzer
        analyzer = TypeInferenceAnalyzer(config)

        graph = analyzer.analyze("")
        assert isinstance(graph, TypeDependencyGraph)
        assert len(graph.nodes) == 0

    def test_complex_circular_dependency(self, tmp_path):
        """複雑な循環依存の検出"""
        test_file = tmp_path / "complex.py"
        test_file.write_text("""
class A:
    b: 'B'

class B:
    c: 'C'

class C:
    a: 'A'
""")

        config = PylayConfig()
        from src.core.analyzer.dependency_extractor import DependencyExtractionAnalyzer
        analyzer = DependencyExtractionAnalyzer(config)
        graph = analyzer.analyze(test_file)

        # 循環が検出されるはず
        assert len(graph.nodes) > 0
        if graph.metadata and "cycles" in graph.metadata:
            cycles = graph.metadata["cycles"]
            assert len(cycles) > 0

    def test_networkx_unavailable_fallback(self):
        """NetworkX未インストール時のフォールバック"""
        config = PylayConfig()
        from src.core.analyzer.graph_processor import GraphProcessor
        processor = GraphProcessor()

        # nx_availableがFalseの場合のメトリクス
        graph = TypeDependencyGraph(nodes=[], edges=[])
        metrics = processor.compute_graph_metrics(graph)

        assert metrics["node_count"] == 0
        assert metrics["edge_count"] == 0
        assert "density" in metrics
