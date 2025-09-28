"""
mypy型推論抽出機能。
mypy --inferを実行し、未アノテーションコードから型情報を抽出。
AST依存抽出と組み合わせて完全な型依存グラフを構築。
"""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from src.core.schemas.graph_types import GraphNode, GraphEdge, TypeDependencyGraph


class MypyTypeExtractor:
    """
    mypy --inferで型推論を実行し、型情報を抽出するクラス。
    AST抽出結果とマージして完全な依存グラフを構築。
    """

    def __init__(self) -> None:
        """抽出器を初期化"""
        self._mypy_cache: dict[str, dict[str, Any]] = {}

    def extract_types_with_mypy(self, file_path: str) -> dict[str, Any]:
        """
        mypy --inferを実行し、型推論結果を抽出。

        Args:
            file_path: 解析対象のPythonファイルパス

        Returns:
            mypyの型推論結果（JSON形式）
        """
        file_path_obj = Path(file_path)

        # キャッシュチェック
        if file_path in self._mypy_cache:
            return self._mypy_cache[file_path]

        try:
            # 一時ファイルにコピー（mypyが読み取り専用ファイルに対応）
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False
            ) as temp_file:
                with open(file_path, "r", encoding="utf-8") as src_file:
                    temp_file.write(src_file.read())
                    temp_file.flush()

                # mypy --inferを実行
                result = subprocess.run(
                    [
                        "uv",
                        "run",
                        "mypy",
                        "--infer",
                        "--output",
                        "json",
                        temp_file.name,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,  # タイムアウト設定
                )

                if result.returncode != 0:
                    # mypyエラー時は空の結果を返す（AST抽出にフォールバック）
                    print(f"⚠️  mypy型推論エラー: {file_path} - {result.stderr}")
                    inferred_types: dict[str, dict[str, str]] = {}
                else:
                    try:
                        inferred_types = (
                            json.loads(result.stdout) if result.stdout else {}
                        )
                    except json.JSONDecodeError:
                        inferred_types = {}
                    # 型をより具体的にアノテーション
                    if not isinstance(inferred_types, dict):
                        inferred_types = {}

                self._mypy_cache[file_path] = inferred_types
                return inferred_types

        except subprocess.TimeoutExpired:
            print(f"⚠️  mypy型推論タイムアウト: {file_path}")
            return {}
        except Exception as e:
            print(f"⚠️  mypy型推論実行エラー: {file_path} - {e}")
            return {}
        finally:
            # 一時ファイル削除
            if "temp_file" in locals():
                Path(temp_file.name).unlink(missing_ok=True)

    def merge_mypy_results(
        self, ast_graph: TypeDependencyGraph, mypy_results: dict[str, Any]
    ) -> TypeDependencyGraph:
        """
        AST抽出結果にmypy型推論結果をマージ。

        Args:
            ast_graph: ASTから抽出された依存グラフ
            mypy_results: mypyの型推論結果

        Returns:
            マージされた依存グラフ
        """
        if not mypy_results:
            return ast_graph

        # mypy結果から追加の型情報を抽出
        additional_nodes, additional_edges = self._extract_mypy_nodes_and_edges(
            mypy_results
        )

        # ASTグラフにマージ
        merged_nodes = list(ast_graph.nodes)
        merged_edges = list(ast_graph.edges)

        # 重複を避けて追加
        existing_names = {node.name for node in merged_nodes}
        for node in additional_nodes:
            if node.name not in existing_names:
                merged_nodes.append(node)
                existing_names.add(node.name)

        merged_edges.extend(additional_edges)

        # メタデータを更新
        merged_metadata = dict(ast_graph.metadata or {})
        merged_metadata.update(
            {
                "mypy_inferred": True,
                "mypy_inference_count": len(additional_nodes),
                "total_nodes": len(merged_nodes),
                "total_edges": len(merged_edges),
            }
        )

        return TypeDependencyGraph(
            nodes=merged_nodes, edges=merged_edges, metadata=merged_metadata
        )

    def _extract_mypy_nodes_and_edges(
        self, mypy_results: dict[str, Any]
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        """mypy結果からノードとエッジを抽出"""
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        if not isinstance(mypy_results, dict) or "types" not in mypy_results:
            return nodes, edges

        types_data = mypy_results["types"]

        for var_name, type_info in types_data.items():
            # 変数ノードを作成
            node = GraphNode(
                name=var_name,
                node_type="variable",
                attributes={
                    "inferred_by_mypy": True,
                    "mypy_type": str(type_info.get("type", "Unknown")),
                },
            )
            nodes.append(node)

            # 型参照エッジを作成（推論された型への参照）
            inferred_type = type_info.get("type", "")
            if inferred_type and inferred_type != "Unknown":
                # 型名を抽出（簡易的に最初の単語）
                type_name = str(inferred_type).split("[")[0].split(".")[0]
                if type_name != var_name:  # 自己参照を避ける
                    edges.append(
                        GraphEdge(
                            source=var_name,
                            target=type_name,
                            relation_type="references",
                            weight=0.7,  # mypy推論は中程度の信頼性
                            metadata={"inferred_by_mypy": True},
                        )
                    )

        return nodes, edges

    def extract_complete_dependencies(
        self, file_path: str, include_mypy: bool = True
    ) -> TypeDependencyGraph:
        """
        AST抽出とmypy推論を組み合わせた完全な依存抽出。

        Args:
            file_path: 解析対象のPythonファイルパス
            include_mypy: mypy推論を含めるかどうか

        Returns:
            完全な依存グラフ
        """
        # AST抽出を実行
        from converters.ast_dependency_extractor import ASTDependencyExtractor

        ast_extractor = ASTDependencyExtractor()
        ast_graph = ast_extractor.extract_dependencies(file_path)

        if not include_mypy:
            return ast_graph

        # mypy推論を実行
        mypy_results = self.extract_types_with_mypy(file_path)

        # マージ
        complete_graph = self.merge_mypy_results(ast_graph, mypy_results)

        return complete_graph
