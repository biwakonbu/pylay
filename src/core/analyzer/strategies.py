"""
型推論戦略

AnalysisStrategyの抽象基底クラスと実装を提供します。
各戦略が依存抽出+型推論+グラフ構築を一括実行します。
"""

from abc import ABC, abstractmethod
from pathlib import Path
import logging

from src.core.schemas.pylay_config import PylayConfig
from src.core.schemas.graph_types import TypeDependencyGraph
from src.core.analyzer.models import AnalyzerState, ParseContext, InferenceConfig
from src.core.analyzer.exceptions import AnalysisError, MypyExecutionError

logger = logging.getLogger(__name__)


class AnalysisStrategy(ABC):
    """
    解析戦略の抽象基底クラス

    依存抽出、型推論、グラフ構築を統合した解析を実行します。
    """

    def __init__(self, config: PylayConfig) -> None:
        """
        戦略を初期化します。

        Args:
            config: pylayの設定オブジェクト
        """
        self.config = config
        self.infer_config = InferenceConfig.from_pylay_config(config)
        self.state = AnalyzerState()

    @abstractmethod
    def analyze(self, file_path: Path) -> TypeDependencyGraph:
        """
        ファイルから解析を実行します。

        Args:
            file_path: 解析対象のファイルパス

        Returns:
            生成された型依存グラフ

        Raises:
            AnalysisError: 解析に失敗した場合
        """
        pass

    def _create_context(self, file_path: Path) -> ParseContext:
        """解析コンテキストを作成"""
        module_name = file_path.stem
        return ParseContext(file_path=file_path, module_name=module_name)

    def _build_graph(self, file_path: Path) -> TypeDependencyGraph:
        """状態からグラフを構築"""
        metadata: dict[str, str | int | bool] = {
            "source_file": str(file_path),
            "extraction_method": self._get_extraction_method(),
            "node_count": len(self.state.nodes),
            "edge_count": len(self.state.edges),
            "infer_level": self.infer_config.infer_level,
        }
        return TypeDependencyGraph(
            nodes=list(self.state.nodes.values()),
            edges=list(self.state.edges.values()),
            metadata=metadata,
        )

    @abstractmethod
    def _get_extraction_method(self) -> str:
        """抽出メソッド名を取得"""
        pass


class LooseAnalysisStrategy(AnalysisStrategy):
    """
    Looseモードの解析戦略

    ASTのみを使用し、mypyを統合しません。
    高速だが精度は低めです。
    """

    def analyze(self, file_path: Path) -> TypeDependencyGraph:
        """Loose解析を実行"""
        from src.core.analyzer.ast_visitors import DependencyVisitor, parse_ast

        # 状態リセット
        self.state.reset()

        # コンテキスト作成
        context = self._create_context(file_path)

        # AST解析
        tree = parse_ast(file_path)
        visitor = DependencyVisitor(self.state, context)
        visitor.visit(tree)

        # グラフ構築
        return self._build_graph(file_path)

    def _get_extraction_method(self) -> str:
        return "AST_analysis_loose"


class NormalAnalysisStrategy(AnalysisStrategy):
    """
    Normalモードの解析戦略

    AST + mypyの基本統合を行います。
    バランスの取れた精度とパフォーマンスを提供します。
    """

    def analyze(self, file_path: Path) -> TypeDependencyGraph:
        """Normal解析を実行"""
        from src.core.analyzer.ast_visitors import DependencyVisitor, parse_ast

        # 状態リセット
        self.state.reset()

        # コンテキスト作成
        context = self._create_context(file_path)

        # AST解析
        tree = parse_ast(file_path)
        visitor = DependencyVisitor(self.state, context)
        visitor.visit(tree)

        # mypy統合（Normal以上）
        if self.infer_config.should_use_mypy():
            self._integrate_mypy(file_path)

        # グラフ構築
        return self._build_graph(file_path)

    def _integrate_mypy(self, file_path: Path) -> None:
        """mypy型推論を統合"""
        try:
            from src.core.analyzer.type_inferrer import run_mypy_inference
            from src.core.schemas.graph_types import GraphNode, RelationType

            # mypy推論を実行
            infer_results = run_mypy_inference(
                file_path, self.infer_config.mypy_flags, self.infer_config.timeout
            )

            # 推論結果をグラフに追加
            for var_name, infer_result in infer_results.items():
                # ノード追加
                if var_name not in self.state.nodes:
                    node = GraphNode(
                        name=var_name,
                        node_type="inferred_variable",
                        attributes={
                            "source_file": str(file_path),
                            "inferred_type": infer_result.inferred_type,
                            "confidence": infer_result.confidence,
                            "extraction_method": "mypy_inferred",
                        },
                    )
                    self.state.nodes[var_name] = node

                # 型依存エッジ追加
                if infer_result.inferred_type != "Any":
                    type_refs = self._extract_type_refs(infer_result.inferred_type)
                    for ref in type_refs:
                        if ref != var_name:
                            from src.core.schemas.graph_types import GraphEdge

                            edge_key = f"{var_name}->{ref}:REFERENCES"
                            if edge_key not in self.state.edges:
                                edge = GraphEdge(
                                    source=var_name,
                                    target=ref,
                                    relation_type=RelationType.REFERENCES,
                                    weight=0.5,
                                )
                                self.state.edges[edge_key] = edge
        except (MypyExecutionError, AnalysisError) as e:
            # mypy失敗時はログして続行（Normalモードでは許容）
            logger.warning(f"mypy統合に失敗しました ({file_path}): {e}")

    def _extract_type_refs(self, type_str: str) -> list[str]:
        """
        型文字列から型参照を抽出

        複雑な型アノテーション（Optional, Dict, List, Callable, Union等）を
        正しくパースし、ユーザー定義型名を抽出します。

        Args:
            type_str: 型を表す文字列（例: "Optional[Dict[str, List[int]]]"）

        Returns:
            抽出された型参照のリスト（重複なし）
        """
        import ast
        import typing

        refs: set[str] = set()

        # 組み込み型とtyping primitiveを除外するセット
        builtins_and_primitives = {
            "int",
            "str",
            "float",
            "bool",
            "bytes",
            "list",
            "dict",
            "set",
            "tuple",
            "frozenset",
            "type",
            "None",
            "NoneType",
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
        }

        def extract_from_typing_obj(obj: object) -> None:
            """typingオブジェクトから型参照を再帰的に抽出"""
            try:
                origin = typing.get_origin(obj)
                args = typing.get_args(obj)

                # originが存在する場合（Generic等）
                if origin is not None:
                    # originが型の場合、その名前を抽出
                    if hasattr(origin, "__name__"):
                        name = origin.__name__
                        if name not in builtins_and_primitives:
                            refs.add(name)

                    # 型引数を再帰的に処理
                    for arg in args:
                        extract_from_typing_obj(arg)
                # 通常の型オブジェクト
                elif hasattr(obj, "__name__"):
                    name = obj.__name__
                    if name not in builtins_and_primitives:
                        refs.add(name)
                # ForwardRef（文字列型参照）
                elif isinstance(obj, typing.ForwardRef):
                    ref_name = obj.__forward_arg__
                    if ref_name not in builtins_and_primitives:
                        refs.add(ref_name)
            except (AttributeError, TypeError):
                # 型オブジェクトでない場合はスキップ
                pass

        def extract_from_ast_node(node: ast.AST) -> None:
            """ASTノードから型参照を抽出"""
            if isinstance(node, ast.Name):
                if node.id not in builtins_and_primitives:
                    refs.add(node.id)
            elif isinstance(node, ast.Attribute):
                # ドット区切りの型名（例: module.ClassName）
                parts: list[str] = []
                current: ast.AST = node
                while isinstance(current, ast.Attribute):
                    parts.insert(0, current.attr)
                    current = current.value
                if isinstance(current, ast.Name):
                    parts.insert(0, current.id)
                if parts:
                    # 最後の部分のみを型名として使用
                    type_name = parts[-1]
                    if type_name not in builtins_and_primitives:
                        refs.add(type_name)
            elif isinstance(node, ast.Subscript):
                # Generic型（例: List[int], Dict[str, Any]）
                extract_from_ast_node(node.value)
                extract_from_ast_node(node.slice)
            elif isinstance(node, ast.Tuple):
                # 複数要素（例: Tuple[int, str]）
                for elt in node.elts:
                    extract_from_ast_node(elt)
            elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
                # Union型の新形式（例: int | str）
                extract_from_ast_node(node.left)
                extract_from_ast_node(node.right)
            elif isinstance(node, (ast.List, ast.Set)):
                # リストやセット内の要素を処理
                for elt in node.elts:
                    extract_from_ast_node(elt)

        # 前方参照（引用符で囲まれた型）を処理
        if type_str.startswith("'") and type_str.endswith("'"):
            inner = type_str[1:-1].strip()
            if inner and inner not in builtins_and_primitives:
                refs.add(inner)
                return sorted(refs)

        # まずtyping評価を試みる
        try:
            # 型文字列をtyping環境で評価
            typing_ns = {**typing.__dict__, "__builtins__": {}}
            obj = eval(type_str, typing_ns)  # noqa: S307
            extract_from_typing_obj(obj)
            if refs:
                return sorted(refs)
        except (NameError, SyntaxError, AttributeError, TypeError):
            # 評価失敗時はASTパースにフォールバック
            pass

        # ASTパースにフォールバック
        try:
            parsed = ast.parse(type_str, mode="eval")
            extract_from_ast_node(parsed.body)
        except SyntaxError:
            # パース失敗時は単純な文字列分割にフォールバック
            logger.debug(f"型文字列のパースに失敗しました: {type_str}")
            parts = (
                type_str.replace("[", " ")
                .replace("]", " ")
                .replace(",", " ")
                .replace("|", " ")
                .split()
            )
            for part in parts:
                part = part.strip()
                if part and part[0].isupper() and part not in builtins_and_primitives:
                    refs.add(part)

        return sorted(refs)

    def _get_extraction_method(self) -> str:
        return "AST_analysis_with_mypy"


class StrictAnalysisStrategy(NormalAnalysisStrategy):
    """
    Strictモードの解析戦略

    AST + mypyの完全統合、厳密な型チェックを行います。
    最も精度が高いが低速です。
    """

    def analyze(self, file_path: Path) -> TypeDependencyGraph:
        """Strict解析を実行"""
        # Normalと同じ処理 + 厳密チェック
        graph = super().analyze(file_path)

        # 循環依存検出（Strictモードでは必須）
        self._detect_cycles(graph)

        return graph

    def _integrate_mypy(self, file_path: Path) -> None:
        """mypy型推論を統合（Strictモード）"""
        try:
            super()._integrate_mypy(file_path)
        except (MypyExecutionError, AnalysisError) as e:
            # Strictモードではエラーを伝播
            logger.error(f"Strictモードでmypy統合に失敗しました ({file_path}): {e}")
            raise AnalysisError(
                f"Strictモードでmypy統合に失敗しました: {e}", file_path=str(file_path)
            ) from e

    def _detect_cycles(self, graph: TypeDependencyGraph) -> None:
        """循環依存を検出（Strictモードでは警告）"""
        try:
            import networkx as nx
        except ImportError:
            return

        nx_graph = graph.to_networkx()
        cycles = list(nx.simple_cycles(nx_graph))
        if cycles:
            # Strictモードでは警告を出力（エラーにはしない）
            print(f"警告: 循環依存が検出されました（{len(cycles)}個）")
            for i, cycle in enumerate(cycles[:5], 1):  # 最初の5個のみ表示
                cycle_str = " -> ".join(cycle)
                print(f"  循環{i}: {cycle_str}")

    def _get_extraction_method(self) -> str:
        return "AST_analysis_with_mypy_strict"


def create_analysis_strategy(config: PylayConfig) -> AnalysisStrategy:
    """
    設定に基づいてAnalysisStrategyを作成します。

    Args:
        config: pylayの設定

    Returns:
        対応するAnalysisStrategyインスタンス

    Raises:
        ValueError: 無効なinfer_levelの場合
    """
    if config.infer_level == "loose":
        return LooseAnalysisStrategy(config)
    elif config.infer_level == "normal":
        return NormalAnalysisStrategy(config)
    elif config.infer_level == "strict":
        return StrictAnalysisStrategy(config)
    else:
        raise ValueError(
            f"無効なinfer_level: {config.infer_level}。'loose', 'normal', 'strict' のいずれかを指定してください。"
        )
