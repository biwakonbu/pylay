"""
型推論戦略

AnalysisStrategyの抽象基底クラスと実装を提供します。
各戦略が依存抽出+型推論+グラフ構築を一括実行します。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

try:
    import networkx as nx
except ImportError as e:
    raise ImportError("NetworkX is required for cycle detection. Install it with: pip install networkx") from e

from datetime import UTC

from src.core.analyzer.exceptions import AnalysisError
from src.core.analyzer.models import AnalyzerState, InferenceConfig, ParseContext
from src.core.schemas.graph import TypeDependencyGraph
from src.core.schemas.pylay_config import PylayConfig
from src.core.schemas.types import GraphMetadata, TypeRefList, create_weight

logger = logging.getLogger(__name__)

# サイクル検出を実行する最大ノード数（大規模グラフでのパフォーマンス劣化を防ぐ）
MAX_NODES_FOR_CYCLE_DETECTION = 1000


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
        module_name = self._compute_module_name(file_path)
        return ParseContext(file_path=file_path, module_name=module_name)

    def _compute_module_name(self, file_path: Path) -> str:
        """ファイルパスから完全修飾モジュール名を計算"""
        try:
            # プロジェクトルートを探索
            project_root = file_path.resolve().parent
            while project_root != project_root.parent:
                if (project_root / "pyproject.toml").exists():
                    break
                project_root = project_root.parent

            # 相対パスからモジュール名を生成
            relative_path = file_path.resolve().with_suffix("").relative_to(project_root)
            return relative_path.as_posix().replace("/", ".")
        except (ValueError, OSError):
            # フォールバック: ファイル名のみ
            return file_path.stem

    def _build_graph(self, file_path: Path) -> TypeDependencyGraph:
        """状態からグラフを構築"""
        from datetime import datetime

        metadata = GraphMetadata(
            created_at=datetime.now(UTC).isoformat(),
            statistics={
                "node_count": len(self.state.nodes),
                "edge_count": len(self.state.edges),
            },
            custom_fields={
                "source_file": str(file_path),
                "extraction_method": self._get_extraction_method(),
                "infer_level": self.infer_config.infer_level,
            },
        )
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
            from src.core.schemas.graph import GraphNode, RelationType

            # mypy推論を実行
            mypy_result = run_mypy_inference(file_path, self.infer_config.mypy_flags, self.infer_config.timeout)

            # 推論結果をグラフに追加
            for var_name, infer_result in mypy_result.inferred_types.items():
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
                            from src.core.schemas.graph import GraphEdge

                            edge_key = f"{var_name}->{ref}:REFERENCES"
                            if edge_key not in self.state.edges:
                                edge = GraphEdge(
                                    source=var_name,
                                    target=ref,
                                    relation_type=RelationType.REFERENCES,
                                    weight=create_weight(0.5),
                                )
                                self.state.edges[edge_key] = edge
        except AnalysisError as e:
            # mypy失敗時はログして続行（Normalモードでは許容）
            logger.warning(f"mypy統合に失敗しました ({file_path}): {e}")

    def _extract_type_refs(self, type_str: str) -> TypeRefList:
        """
        型文字列から型参照を抽出（統合ユーティリティ使用）

        複雑な型アノテーション（Optional, Dict, List, Callable, Union等）を
        正しくパースし、ユーザー定義型名を抽出します。

        Args:
            type_str: 型を表す文字列（例: "Optional[Dict[str, List[int]]]"）

        Returns:
            抽出された型参照のリスト（重複なし、ソート済み）
        """
        from src.core.utils.type_parsing import extract_type_references

        return extract_type_references(type_str, exclude_builtins=True, deduplicate=True)

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
        except AnalysisError as e:
            # Strictモードではエラーを伝播（元の例外をそのまま再送出）
            logger.error(f"Strictモードでmypy統合に失敗しました ({file_path}): {e}")
            raise

    def _detect_cycles(self, graph: TypeDependencyGraph) -> None:
        """循環依存を検出（Strictモードでは警告）"""
        nx_graph = graph.to_networkx()
        num_nodes = nx_graph.number_of_nodes()

        # 大規模グラフでのサイクル検出をスキップ
        if num_nodes > MAX_NODES_FOR_CYCLE_DETECTION:
            logger.warning(
                "グラフが大規模すぎるためサイクル検出をスキップします: %d ノード（上限: %d）",
                num_nodes,
                MAX_NODES_FOR_CYCLE_DETECTION,
            )
            return

        logger.info("サイクル検出を実行中... (%d ノード)", num_nodes)
        cycles = list(nx.simple_cycles(nx_graph))

        if cycles:
            logger.warning("循環依存が検出されました: %d 個", len(cycles))
            # 最初の5個のみログ出力
            for i, cycle in enumerate(cycles[:5], 1):
                cycle_str = " -> ".join(cycle)
                logger.warning("  循環 %d: %s", i, cycle_str)
            if len(cycles) > 5:
                logger.info("  ... 他 %d 個の循環依存", len(cycles) - 5)
        else:
            logger.info("循環依存は検出されませんでした")

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
