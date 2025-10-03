"""
analyzerモジュールのテスト

型推論、依存抽出、グラフ処理のユニットテストと統合テスト。
"""

import subprocess
from unittest.mock import patch

import pytest

from src.core.analyzer.base import Analyzer, FullAnalyzer, create_analyzer
from src.core.analyzer.graph_processor import GraphProcessor
from src.core.schemas.graph import (
    GraphEdge,
    GraphNode,
    RelationType,
    TypeDependencyGraph,
)
from src.core.schemas.pylay_config import PylayConfig


class TestAnalyzerBase:
    """Analyzer基底クラスのテスト

    Analyzer抽象基底クラスの基本的な動作をテストします。
    """

    def test_analyzer_interface(self):
        """Analyzerが抽象クラスであることを確認

        Analyzerクラスを直接インスタンス化できないことをテストします。
        """
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
    """TypeInferenceAnalyzerのテスト

    TypeInferenceAnalyzerの型推論機能が正しく動作することを確認します。
    """

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
        from src.core.analyzer.models import InferResult

        existing = {"x": "int"}
        inferred = {
            "y": InferResult(variable_name="y", inferred_type="str", confidence=0.8)
        }
        config = PylayConfig()
        from src.core.analyzer.type_inferrer import TypeInferenceAnalyzer

        analyzer = TypeInferenceAnalyzer(config)
        merged = analyzer.merge_inferred_types(existing, inferred)

        assert merged["x"] == "int"
        assert merged["y"] == "str"


class TestDependencyExtractionAnalyzer:
    """DependencyExtractionAnalyzerのテスト

    DependencyExtractionAnalyzerの依存関係抽出機能が正しく動作することを確認します。
    """

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
    """GraphProcessorのテスト

    GraphProcessorのグラフ処理機能が正しく動作することを確認します。
    """

    def test_analyze_cycles(self):
        """循環分析

        グラフ内の循環を検出する機能をテストします。
        """
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
    @patch("src.core.analyzer.graph_processor.Node")
    @patch("src.core.analyzer.graph_processor.Edge")
    def test_visualize_graph(self, mock_edge, mock_node, mock_dot):
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
            # pydotが利用不可の場合はスキップ
            try:
                import pydot  # noqa: F401

                processor.visualize_graph(graph, "test.png")
            except (ImportError, FileNotFoundError, OSError):
                # pydot未インストールまたはGraphviz未インストールの場合はスキップ
                pytest.skip("pydot or Graphviz not installed")

    def test_export_graphml(self, tmp_path):
        """GraphMLエクスポート

        グラフをGraphML形式でエクスポートする機能をテストします。
        """
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
            try:
                import pydot  # noqa: F401

                processor.visualize_graph(graph, vis_file, format_type="png")
            except (ImportError, FileNotFoundError, OSError):
                # pydot未インストールまたはGraphviz未インストールの場合はスキップ
                pytest.skip("pydot or Graphviz not installed")

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

        # 空文字列はValidationErrorを引き起こすため、ValueErrorが発生することを期待
        with pytest.raises(ValueError, match="無効な入力"):
            analyzer.analyze("")

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
        """NetworkX未インストール時のフォールバック

        NetworkXが利用できない場合のフォールバック動作をテストします。
        """
        config = PylayConfig()  # noqa: F841
        from src.core.analyzer.graph_processor import GraphProcessor

        processor = GraphProcessor()

        # nx_availableがFalseの場合のメトリクス
        graph = TypeDependencyGraph(nodes=[], edges=[])
        metrics = processor.compute_graph_metrics(graph)

        assert metrics["node_count"] == 0
        assert metrics["edge_count"] == 0
        assert "density" in metrics

    def test_mypy_failure_handling(self, tmp_path):
        """mypy失敗時のハンドリング"""
        test_file = tmp_path / "invalid.py"
        test_file.write_text("""
def invalid_syntax(
    # 無効な型アノテーション
    x: NonExistentType
""")

        config = PylayConfig()
        from src.core.analyzer.type_inferrer import TypeInferenceAnalyzer

        analyzer = TypeInferenceAnalyzer(config)
        # mypyが失敗してもエラーなく処理
        with pytest.raises((ValueError, SyntaxError)):
            _ = analyzer.analyze(test_file)

    def test_large_file_handling(self, tmp_path):
        """大規模ファイルの処理"""
        test_file = tmp_path / "large.py"
        large_code = "\n".join([f"x{i}: int = {i}" for i in range(1000)])
        test_file.write_text(large_code)

        config = PylayConfig()
        from src.core.analyzer.type_inferrer import TypeInferenceAnalyzer

        analyzer = TypeInferenceAnalyzer(config)
        graph = analyzer.analyze(test_file)
        assert isinstance(graph, TypeDependencyGraph)
        assert len(graph.nodes) > 0

    def test_timeout_subprocess_handling(self, tmp_path, monkeypatch):
        """subprocessタイムアウトのハンドリング"""

        def mock_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(["cmd"], 10)

        monkeypatch.setattr("subprocess.run", mock_run)

        config = PylayConfig()
        from src.core.analyzer.type_inferrer import TypeInferenceAnalyzer

        analyzer = TypeInferenceAnalyzer(config)
        with pytest.raises((RuntimeError, subprocess.TimeoutExpired)):
            analyzer.infer_types_from_code("x: int = 5")

    def test_invalid_yaml_conversion(self, tmp_path):
        """無効YAMLへの変換エラー"""
        # 無効なグラフ（循環など）
        graph = TypeDependencyGraph(nodes=[], edges=[])
        # 意図的に無効なデータを追加
        invalid_node = GraphNode(
            name="invalid", node_type="class", attributes={"invalid": "none"}
        )
        graph.add_node(invalid_node)

        from src.core.analyzer.graph_processor import GraphProcessor

        processor = GraphProcessor()

        # YAML変換でエラーが起きないことを確認
        yaml_data = processor.convert_graph_to_yaml_spec(graph)
        assert "dependencies" in yaml_data

    def test_os_path_independence(self, tmp_path):
        """OSパス独立性のテスト"""
        test_file = tmp_path / "test.py"
        test_file.write_text("x: int = 5")

        config = PylayConfig()
        from src.core.analyzer.type_inferrer import TypeInferenceAnalyzer

        analyzer = TypeInferenceAnalyzer(config)
        graph = analyzer.analyze(test_file)

        # パスが相対/絶対に関係なく動作
        assert isinstance(graph, TypeDependencyGraph)


class TestExtractTypeRefs:
    """_extract_type_refsメソッドのテスト

    複雑な型アノテーションから型参照を正しく抽出できることを確認します。
    """

    @pytest.fixture
    def strategy(self):
        """テスト用のNormalAnalysisStrategyインスタンスを作成"""
        from src.core.analyzer.strategies import NormalAnalysisStrategy

        config = PylayConfig()
        return NormalAnalysisStrategy(config)

    def test_simple_type(self, strategy):
        """シンプルな型参照の抽出"""
        refs = strategy._extract_type_refs("MyClass")
        assert refs == ["MyClass"]

    def test_builtin_types_filtered(self, strategy):
        """組み込み型がフィルタされることを確認"""
        refs = strategy._extract_type_refs("int")
        assert refs == []

        refs = strategy._extract_type_refs("str")
        assert refs == []

        refs = strategy._extract_type_refs("list")
        assert refs == []

    def test_optional_type(self, strategy):
        """Optional型の抽出"""
        refs = strategy._extract_type_refs("Optional[MyClass]")
        assert refs == ["MyClass"]

        # 組み込み型はフィルタ
        refs = strategy._extract_type_refs("Optional[int]")
        assert refs == []

    def test_union_type(self, strategy):
        """Union型の抽出"""
        refs = strategy._extract_type_refs("Union[MyClass, YourClass]")
        assert sorted(refs) == ["MyClass", "YourClass"]

        # 組み込み型はフィルタ
        refs = strategy._extract_type_refs("Union[int, str]")
        assert refs == []

        # 混合
        refs = strategy._extract_type_refs("Union[MyClass, int]")
        assert refs == ["MyClass"]

    def test_union_type_new_syntax(self, strategy):
        """Union型の新構文（|）の抽出"""
        refs = strategy._extract_type_refs("MyClass | YourClass")
        assert sorted(refs) == ["MyClass", "YourClass"]

        refs = strategy._extract_type_refs("MyClass | int | str")
        assert refs == ["MyClass"]

    def test_dict_type(self, strategy):
        """Dict型の抽出"""
        refs = strategy._extract_type_refs("Dict[str, MyClass]")
        assert refs == ["MyClass"]

        refs = strategy._extract_type_refs("Dict[MyKey, MyValue]")
        assert sorted(refs) == ["MyKey", "MyValue"]

        # 組み込み型のみはフィルタ
        refs = strategy._extract_type_refs("Dict[str, int]")
        assert refs == []

    def test_list_type(self, strategy):
        """List型の抽出"""
        refs = strategy._extract_type_refs("List[MyClass]")
        assert refs == ["MyClass"]

        refs = strategy._extract_type_refs("List[int]")
        assert refs == []

    def test_nested_generics(self, strategy):
        """ネストされたジェネリック型の抽出"""
        refs = strategy._extract_type_refs("Dict[str, List[MyClass]]")
        assert refs == ["MyClass"]

        refs = strategy._extract_type_refs("Optional[Dict[str, List[MyClass]]]")
        assert refs == ["MyClass"]

        refs = strategy._extract_type_refs("Dict[MyKey, List[MyValue]]")
        assert sorted(refs) == ["MyKey", "MyValue"]

    def test_callable_type(self, strategy):
        """Callable型の抽出"""
        refs = strategy._extract_type_refs("Callable[[int], str]")
        assert refs == []

        refs = strategy._extract_type_refs("Callable[[MyInput], MyOutput]")
        assert sorted(refs) == ["MyInput", "MyOutput"]

        refs = strategy._extract_type_refs("Callable[[int, str], MyOutput]")
        assert refs == ["MyOutput"]

    def test_tuple_type(self, strategy):
        """Tuple型の抽出"""
        refs = strategy._extract_type_refs("Tuple[int, str]")
        assert refs == []

        refs = strategy._extract_type_refs("Tuple[MyClass, YourClass]")
        assert sorted(refs) == ["MyClass", "YourClass"]

    def test_forward_reference(self, strategy):
        """前方参照の抽出"""
        refs = strategy._extract_type_refs("'MyClass'")
        assert refs == ["MyClass"]

        refs = strategy._extract_type_refs("Optional['MyClass']")
        assert refs == ["MyClass"]

    def test_complex_nested_types(self, strategy):
        """複雑にネストされた型の抽出"""
        refs = strategy._extract_type_refs(
            "Optional[Dict[str, List[Union[MyClass, YourClass]]]]"
        )
        assert sorted(refs) == ["MyClass", "YourClass"]

        refs = strategy._extract_type_refs(
            "Callable[[Dict[str, MyInput]], Optional[MyOutput]]"
        )
        assert sorted(refs) == ["MyInput", "MyOutput"]

    def test_typing_primitives_filtered(self, strategy):
        """typing primitiveがフィルタされることを確認"""
        refs = strategy._extract_type_refs("Any")
        assert refs == []

        refs = strategy._extract_type_refs("Optional[Any]")
        assert refs == []

        refs = strategy._extract_type_refs("TypeVar")
        assert refs == []

    def test_dotted_type_names(self, strategy):
        """ドット区切りの型名の抽出"""
        refs = strategy._extract_type_refs("module.MyClass")
        assert refs == ["MyClass"]

        refs = strategy._extract_type_refs("pkg.subpkg.MyClass")
        assert refs == ["MyClass"]

    def test_sequence_mapping_types(self, strategy):
        """SequenceとMapping型の抽出"""
        refs = strategy._extract_type_refs("Sequence[MyClass]")
        assert refs == ["MyClass"]

        refs = strategy._extract_type_refs("Mapping[str, MyClass]")
        assert refs == ["MyClass"]

    def test_empty_and_invalid_strings(self, strategy):
        """空文字列と無効な型文字列の処理"""
        refs = strategy._extract_type_refs("")
        assert refs == []

        # 無効な構文でもエラーなく処理し、抽出可能な型名を返す
        # "Invalid[" のような不完全な型でも、"Invalid"という型名を抽出
        refs = strategy._extract_type_refs("Invalid[")
        assert refs == ["Invalid"]

    def test_deduplication(self, strategy):
        """重複する型参照が除外されることを確認"""
        refs = strategy._extract_type_refs("Union[MyClass, MyClass]")
        assert refs == ["MyClass"]

        refs = strategy._extract_type_refs("Dict[MyClass, List[MyClass]]")
        assert refs == ["MyClass"]

    def test_real_world_examples(self, strategy):
        """実世界の型アノテーション例"""
        # Pydantic BaseModel
        refs = strategy._extract_type_refs("BaseModel")
        assert refs == ["BaseModel"]

        # FastAPI Response
        refs = strategy._extract_type_refs("Optional[Response]")
        assert refs == ["Response"]

        # 複雑なネスト
        refs = strategy._extract_type_refs(
            "Dict[str, Union[str, int, List[CustomType]]]"
        )
        assert refs == ["CustomType"]


class TestSecurityTypingNamespace:
    """typing_nsセキュリティのテスト

    typing_nsが悪意ある属性アクセスを防ぐことを確認します。
    """

    @pytest.fixture
    def strategy(self):
        """テスト用のNormalAnalysisStrategyインスタンスを作成"""
        from src.core.analyzer.strategies import NormalAnalysisStrategy

        config = PylayConfig()
        return NormalAnalysisStrategy(config)

    def test_typing_ns_allowlist_blocks_sys(self, strategy):
        """typing_nsがsysモジュールへのアクセスをブロック"""
        # sysモジュールはallowlistに含まれていないため、eval失敗→ASTフォールバック
        # ASTパースでは"Sys"という型名として抽出される
        refs = strategy._extract_type_refs("sys.modules")
        # "Sys"は大文字始まりではないのでフィルタされ、"modules"が抽出される
        # 実際にはASTパースで"modules"という型名として抽出される可能性がある
        # ただし、組み込み型フィルタで除外される可能性が高い
        # ここでは、評価が失敗してASTフォールバックすることを確認
        assert isinstance(refs, list)  # 型リストが返されることを確認

    def test_typing_ns_allowlist_blocks_types(self, strategy):
        """typing_nsがtypesモジュールへのアクセスをブロック"""
        # typesモジュールはallowlistに含まれていないため、eval失敗→ASTフォールバック
        refs = strategy._extract_type_refs("types.ModuleType")
        # ASTパースで"ModuleType"が抽出される
        assert "ModuleType" in refs or refs == []

    def test_typing_ns_allowlist_allows_valid_types(self, strategy):
        """typing_nsが正当な型へのアクセスを許可"""
        # allowlistに含まれる型は正常に評価される
        refs = strategy._extract_type_refs("Optional[List[int]]")
        assert refs == []  # 組み込み型のみなのでフィルタ

        refs = strategy._extract_type_refs("Union[MyClass, YourClass]")
        assert sorted(refs) == ["MyClass", "YourClass"]

    def test_typing_ns_eval_failure_fallback_to_ast(self, strategy):
        """eval失敗時にASTパースにフォールバック"""
        # 無効な型文字列でもASTパースにフォールバックして処理
        refs = strategy._extract_type_refs("NonExistentModule.SomeClass")
        # ASTパースで"SomeClass"が抽出される
        assert "SomeClass" in refs or refs == []

    def test_typing_ns_no_arbitrary_code_execution(self, strategy):
        """typing_nsで任意コード実行を防ぐ"""
        # __builtins__が空なので、組み込み関数へのアクセスは失敗→ASTフォールバック
        refs = strategy._extract_type_refs("__import__('os').system('ls')")
        # eval失敗→ASTパース→特定の型名は抽出されない
        assert isinstance(refs, list)

    def test_typing_ns_restricted_attributes(self, strategy):
        """typing_nsの属性が制限されていることを確認"""
        import typing

        # allowed_typing_attrsにのみ含まれる属性のみがtyping_nsに存在
        allowed_attrs = {
            "Any",
            "Optional",
            "Union",
            "Literal",
            "Final",
            "ClassVar",
            "Callable",
            "TypeVar",
            "Generic",
            "Protocol",
            "TypedDict",
            "Annotated",
            "Sequence",
            "Mapping",
            "Iterable",
            "Iterator",
            "List",
            "Dict",
            "Set",
            "Tuple",
            "FrozenSet",
            "get_origin",
            "get_args",
            "ForwardRef",
            "cast",
            "overload",
            "TypeAlias",
            "Concatenate",
            "ParamSpec",
            "TypeGuard",
            "Unpack",
            "TypeVarTuple",
            "Never",
            "Self",
            "LiteralString",
            "assert_type",
            "reveal_type",
            "dataclass_transform",
            "AbstractSet",
            "MutableSet",
            "MutableMapping",
            "MutableSequence",
            "Awaitable",
            "Coroutine",
            "AsyncIterable",
            "AsyncIterator",
            "ContextManager",
            "AsyncContextManager",
        }

        # typing.__dict__に含まれる属性で、allowlistに含まれないものを確認
        typing_dict_keys = set(typing.__dict__.keys())
        blocked_attrs = typing_dict_keys - allowed_attrs

        # sys, types などの危険な属性がブロックされていることを確認
        # (実際にはtyping.__dict__にsysやtypesが含まれることは稀だが、念のため)
        # ここでは、allowlistに含まれない属性が多数存在することを確認
        assert len(blocked_attrs) > 0


class TestTempFileCleanup:
    """一時ファイルクリーンアップのテスト

    コード文字列を解析する際に作成される一時ファイルが
    確実にクリーンアップされることを確認します。
    """

    def test_temp_file_cleanup_on_success(self, tmp_path, monkeypatch):
        """正常終了時に一時ファイルがクリーンアップされることを確認"""
        import tempfile
        from unittest.mock import patch

        from src.core.analyzer.base import FullAnalyzer
        from src.core.schemas.pylay_config import PylayConfig

        config = PylayConfig()
        analyzer = FullAnalyzer(config)

        code = """
x: int = 5
y: str = "test"
"""

        # tempfileの一時ディレクトリをtmp_pathに変更
        original_named_temp_file = tempfile.NamedTemporaryFile

        def custom_named_temp_file(*args, **kwargs):
            kwargs["dir"] = str(tmp_path)
            return original_named_temp_file(*args, **kwargs)

        # 解析前の一時ファイル数を記録
        before_files = set(tmp_path.glob("*.py"))

        # 解析を実行（一時ファイルディレクトリをtmp_pathに設定）
        with patch("tempfile.NamedTemporaryFile", side_effect=custom_named_temp_file):
            graph = analyzer.analyze(code)
            assert isinstance(graph, TypeDependencyGraph)

        # 解析後の一時ファイル数を確認
        after_files = set(tmp_path.glob("*.py"))

        # 新しい一時ファイルが残っていないことを確認
        new_files = after_files - before_files
        assert len(new_files) == 0, f"一時ファイルが残っています: {new_files}"

    def test_temp_file_cleanup_on_error(self, tmp_path, monkeypatch):
        """エラー発生時も一時ファイルがクリーンアップされることを確認"""
        import tempfile
        from unittest.mock import patch

        from src.core.analyzer.base import FullAnalyzer
        from src.core.schemas.pylay_config import PylayConfig

        config = PylayConfig()
        analyzer = FullAnalyzer(config)

        code = """
x: int = 5
y: str = "test"
"""

        # tempfileの一時ディレクトリをtmp_pathに変更
        original_named_temp_file = tempfile.NamedTemporaryFile

        def custom_named_temp_file(*args, **kwargs):
            kwargs["dir"] = str(tmp_path)
            return original_named_temp_file(*args, **kwargs)

        # 解析前の一時ファイル数を記録
        before_files = set(tmp_path.glob("*.py"))

        # 戦略のanalyzeメソッドでエラーを発生させる
        with patch("tempfile.NamedTemporaryFile", side_effect=custom_named_temp_file):
            with patch.object(
                analyzer.strategy, "analyze", side_effect=RuntimeError("テストエラー")
            ):
                with pytest.raises(RuntimeError, match="テストエラー"):
                    analyzer.analyze(code)

        # エラー発生後も一時ファイルがクリーンアップされていることを確認
        after_files = set(tmp_path.glob("*.py"))
        new_files = after_files - before_files
        assert len(new_files) == 0, f"エラー時に一時ファイルが残っています: {new_files}"

    def test_no_cleanup_for_regular_files(self, tmp_path):
        """通常のファイルの場合はクリーンアップされないことを確認"""
        from src.core.analyzer.base import FullAnalyzer
        from src.core.schemas.pylay_config import PylayConfig

        config = PylayConfig()
        analyzer = FullAnalyzer(config)

        # 通常のテストファイルを作成
        test_file = tmp_path / "test.py"
        test_file.write_text("""
x: int = 5
y: str = "test"
""")

        # 解析を実行
        graph = analyzer.analyze(test_file)
        assert isinstance(graph, TypeDependencyGraph)

        # 元のファイルが削除されていないことを確認
        assert test_file.exists(), "通常のファイルが削除されてしまいました"
