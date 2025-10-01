"""
依存関係抽出モジュール

Python AST を使用してコードを解析し、型依存グラフを構築します。
NetworkX を使用して依存ツリーを作成し、視覚化を可能にします。
"""

from __future__ import annotations

import logging
from pathlib import Path

try:
    import networkx as nx
except ImportError:
    nx = None

from src.core.analyzer.abc_base import Analyzer
from src.core.analyzer.ast_visitors import DependencyVisitor, parse_ast
from src.core.analyzer.exceptions import (
    DependencyExtractionError,
    MypyExecutionError,
    TypeInferenceError,
)
from src.core.analyzer.models import AnalyzerState, ParseContext
from src.core.schemas.graph_types import TypeDependencyGraph
from src.core.schemas.pylay_config import PylayConfig

logger = logging.getLogger(__name__)


class DependencyExtractionAnalyzer(Analyzer):
    """
    依存関係抽出に特化したAnalyzer

    ASTとNetworkXで依存グラフを構築します。
    循環検出を自動実行します。
    """

    def __init__(self, config: PylayConfig) -> None:
        super().__init__(config)
        self.state = AnalyzerState()

    def analyze(self, input_path: Path | str) -> TypeDependencyGraph:
        """
        指定された入力から依存関係を抽出します。

        Args:
            input_path: 解析対象のファイルパスまたはコード文字列

        Returns:
            抽出されたTypeDependencyGraph

        Raises:
            ValueError: 入力が無効な場合
            DependencyExtractionError: 抽出に失敗した場合
        """
        # 入力を準備
        temp_path: Path | None = None
        if isinstance(input_path, str):
            # コード文字列の場合、一時ファイルを作成
            from pydantic import ValidationError

            from src.core.schemas.analyzer_types import TempFileConfig
            from src.core.utils.io_helpers import create_temp_file

            try:
                temp_config = TempFileConfig(code=input_path, suffix=".py", mode="w")
            except ValidationError as e:
                raise ValueError(f"無効な入力: {e}") from e
            temp_path = create_temp_file(temp_config)
            file_path = temp_path
        elif isinstance(input_path, Path):
            file_path = input_path
        else:
            raise ValueError("input_path は Path または str でなければなりません")

        try:
            # 状態リセット
            self.state.reset()

            # コンテキスト作成
            context = ParseContext(
                file_path=Path(file_path),
                module_name=self._compute_module_name(Path(file_path)),
            )

            # ASTを解析
            tree = parse_ast(file_path)
            visitor = DependencyVisitor(self.state, context)
            visitor.visit(tree)

            # mypy統合（config.infer_levelに基づく）
            if self.config.infer_level in ["strict", "normal"]:
                self._integrate_mypy(file_path)

            # グラフ構築
            from src.core.schemas.types import GraphMetadata

            metadata = GraphMetadata(
                statistics={
                    "node_count": len(self.state.nodes),
                    "edge_count": len(self.state.edges),
                },
                custom_fields={
                    "source_file": str(file_path),
                    "extraction_method": "AST_analysis_with_mypy"
                    if self.config.infer_level != "loose"
                    else "AST_analysis",
                    "mypy_enabled": self.config.infer_level != "loose",
                },
            )
            graph = TypeDependencyGraph(
                nodes=list(self.state.nodes.values()),
                edges=list(self.state.edges.values()),
                metadata=metadata,
            )

            # 循環検出
            if nx:
                cycles = self._detect_cycles(graph)
                if cycles:
                    metadata.cycles = cycles

            return graph

        except Exception as e:
            raise DependencyExtractionError(
                f"依存関係抽出に失敗しました: {e}", file_path=str(file_path)
            )
        finally:
            # 一時ファイルのクリーンアップ
            if temp_path is not None:
                from src.core.utils.io_helpers import cleanup_temp_file

                cleanup_temp_file(temp_path)

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
            relative_path = (
                file_path.resolve().with_suffix("").relative_to(project_root)
            )
            return relative_path.as_posix().replace("/", ".")
        except (ValueError, Exception) as e:
            # エラーログを出力
            import hashlib
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(
                f"モジュール名の計算に失敗しました: file_path={file_path}, error={e}"
            )

            # より一意性の高いフォールバック名を生成
            try:
                # 解決済みパスからドット区切り名を生成
                resolved = file_path.resolve().with_suffix("")
                fallback_name = resolved.as_posix().replace("/", ".")
                # 先頭のドットを削除（絶対パスの場合）
                if fallback_name.startswith("."):
                    fallback_name = fallback_name[1:]
                return fallback_name
            except Exception:
                # 最終フォールバック: パスの最後の2要素 + ハッシュ
                resolved_str = str(file_path.resolve())
                path_hash = hashlib.sha256(resolved_str.encode()).hexdigest()[:8]
                parts = (
                    file_path.parts[-2:]
                    if len(file_path.parts) > 1
                    else (file_path.stem,)
                )
                return f"{'.'.join(parts)}.{path_hash}"

    def _integrate_mypy(self, file_path: Path | str) -> None:
        """mypy統合（型推論結果を追加）"""
        try:
            from src.core.analyzer.type_inferrer import TypeInferenceAnalyzer

            # 型推論を実行してノード/エッジ追加
            infer_analyzer = TypeInferenceAnalyzer(self.config)
            inferred_graph = infer_analyzer._analyze_from_file(Path(file_path))
            for node in inferred_graph.nodes:
                if node.name not in self.state.nodes:
                    self.state.nodes[node.name] = node
                    # 型依存エッジ追加
                    if node.attributes and "inferred_type" in node.attributes:
                        type_str = node.attributes["inferred_type"]
                        if type_str != "Any":
                            type_refs = self._extract_type_refs_from_string(
                                str(type_str)
                            )
                            for ref in type_refs:
                                if ref != node.name:
                                    from src.core.schemas.graph_types import (
                                        GraphEdge,
                                        RelationType,
                                    )

                                    edge_key = f"{node.name}->{ref}:REFERENCES"
                                    if edge_key not in self.state.edges:
                                        edge = GraphEdge(
                                            source=node.name,
                                            target=ref,
                                            relation_type=RelationType.REFERENCES,
                                            weight=0.5,
                                        )
                                        self.state.edges[edge_key] = edge
        except (TypeInferenceError, MypyExecutionError) as e:
            # mypy失敗時はログして続行
            logger.warning(f"mypy統合に失敗しました ({file_path}): {e}")

    def _extract_type_refs_from_string(self, type_str: str) -> list[str]:
        """
        型文字列から型参照を抽出（統合ユーティリティ使用）

        ネストされたジェネリクス、Union型、Callable型など
        複雑な型アノテーションに対応します。

        Args:
            type_str: 型を表す文字列（例: "Dict[str, List[int]]", "int | str"）

        Returns:
            抽出された型参照のリスト（重複除去済み）
        """
        from src.core.utils.type_parsing import extract_type_references

        return extract_type_references(
            type_str, exclude_builtins=True, deduplicate=True
        )

    def _detect_cycles(self, graph: TypeDependencyGraph) -> list[list[str]]:
        """グラフから循環を検出"""
        if nx is None:
            return []
        nx_graph = graph.to_networkx()
        cycles = list(nx.simple_cycles(nx_graph))
        return cycles
