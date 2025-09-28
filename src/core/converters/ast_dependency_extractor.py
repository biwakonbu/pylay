"""
AST依存関係抽出機能。
Python ASTを解析し、型依存グラフを構築するためのコンポーネント。
"""

import ast
from pathlib import Path
from typing import Optional
from datetime import datetime

from src.core.schemas.graph_types import (
    GraphNode,
    GraphEdge,
    TypeDependencyGraph,
    RelationType,
)


class ASTDependencyExtractor:
    """
    Python ASTから型依存関係を抽出するクラス。
    基本的な依存（参照、継承、関数引数）を検出。
    最適化版：キャッシュ機構とより正確な依存検出。
    """

    def __init__(self) -> None:
        """抽出器を初期化"""
        self.nodes: dict[str, GraphNode] = {}
        self.edges: dict[str, GraphEdge] = {}
        self.visited_nodes: set[str] = set()
        self._node_cache: dict[str, GraphNode] = {}
        self._processing_stack: set[str] = set()  # 循環参照防止

    def _reset_state(self) -> None:
        """抽出状態をリセット"""
        self.nodes.clear()
        self.edges.clear()
        self.visited_nodes.clear()
        self._node_cache.clear()
        self._processing_stack.clear()

    def extract_dependencies(
        self, file_path: str, include_mypy: bool = False
    ) -> TypeDependencyGraph:
        """
        指定されたPythonファイルから依存関係を抽出。

        Args:
            file_path: 解析対象のPythonファイルパス
            include_mypy: mypy型推論を含めるかどうか

        Returns:
            抽出された依存グラフ
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source_code = f.read()
        except FileNotFoundError:
            raise ValueError(f"ファイルが見つかりません: {file_path}")
        except UnicodeDecodeError as e:
            raise ValueError(f"ファイルのエンコーディングエラー: {file_path} - {e}")

        # ASTを解析
        try:
            tree = ast.parse(source_code, filename=file_path)
        except SyntaxError as e:
            raise ValueError(f"Python構文エラー: {file_path} - {e}")

        # 状態をリセット
        self._reset_state()

        # 依存関係を抽出
        self._extract_from_ast(tree, file_path)

        # mypy統合（オプション）
        if include_mypy:
            from src.core.converters.infer_types import (
                infer_types_from_file,
                extract_existing_annotations,
                merge_inferred_types,
            )

            # mypy型推論を実行
            try:
                existing_annotations = extract_existing_annotations(file_path)
                inferred_types = infer_types_from_file(file_path)
                merged_types = merge_inferred_types(
                    existing_annotations, inferred_types
                )

                # 推論結果をノードとして追加
                for var_name, type_info in merged_types.items():
                    if var_name not in self.nodes:
                        inferred_node = GraphNode(
                            name=var_name,
                            node_type="inferred_variable",
                            attributes={
                                "source_file": file_path,
                                "inferred_type": str(type_info),
                                "extraction_method": "mypy_inferred",
                            },
                        )
                        self._add_node(inferred_node)

                        # 型依存エッジを追加
                        if isinstance(type_info, str) and type_info != "Any":
                            # 型参照を抽出してエッジ作成
                            type_refs = self._extract_type_refs_from_string(type_info)
                            for ref in type_refs:
                                if ref != var_name:
                                    self._add_edge(
                                        var_name,
                                        ref,
                                        RelationType.REFERENCES,
                                        weight=0.5,
                                    )

            except Exception as e:
                # mypy推論失敗時は無視してASTのみ使用
                pass

        # グラフを構築
        graph = TypeDependencyGraph(
            nodes=list(self.nodes.values()),
            edges=list(self.edges.values()),
            metadata={
                "source_file": file_path,
                "extraction_method": "AST_analysis_with_mypy"
                if include_mypy
                else "AST_analysis",
                "extraction_timestamp": datetime.now().isoformat(),
                "node_count": len(self.nodes),
                "edge_count": len(self.edges),
                "mypy_enabled": include_mypy,
            },
        )

        return graph

    def _extract_from_ast(self, tree: ast.AST, file_path: str) -> None:
        """ASTから依存関係を抽出"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self._handle_class_def(node, file_path)
            elif isinstance(node, ast.FunctionDef):
                self._handle_function_def(node, file_path)
            elif isinstance(node, ast.Assign):
                self._handle_assign(node, file_path)
            elif isinstance(node, ast.Import):
                self._handle_import(node, file_path)
            elif isinstance(node, ast.ImportFrom):
                self._handle_import_from(node, file_path)
            elif isinstance(node, ast.Attribute):
                self._handle_attribute(node, file_path)
            elif isinstance(node, ast.Call):
                self._handle_call(node, file_path)

    def _handle_class_def(self, node: ast.ClassDef, file_path: str) -> None:
        """クラス定義から依存を抽出"""
        class_name = node.name

        # 循環参照チェック
        if class_name in self._processing_stack:
            return
        self._processing_stack.add(class_name)

        try:
            class_node = GraphNode(
                name=class_name,
                node_type="class",
                attributes={
                    "source_file": file_path,
                    "line": node.lineno,
                    "column": getattr(node, "col_offset", 0),
                },
            )
            self._add_node(class_node)

            # 基底クラス（継承関係）
            for base in node.bases:
                base_name = self._get_type_name_from_ast(base)
                if base_name and base_name != class_name:
                    # 継承は強い依存
                    self._add_edge(
                        class_name, base_name, RelationType.INHERITS_FROM, weight=0.9
                    )

            # クラス内の型アノテーションとメソッド
            for item in node.body:
                if isinstance(item, ast.AnnAssign):
                    self._handle_annotation(item, class_name, file_path)
                elif isinstance(item, ast.FunctionDef):
                    self._handle_method_def(item, class_name, file_path)
        finally:
            self._processing_stack.discard(class_name)

    def _handle_function_def(self, node: ast.FunctionDef, file_path: str) -> None:
        """関数定義から依存を抽出"""
        func_name = node.name
        func_node = GraphNode(
            name=func_name,
            node_type="function",
            attributes={
                "source_file": file_path,
                "line": node.lineno,
                "column": getattr(node, "col_offset", 0),
            },
        )
        self._add_node(func_node)

        # 引数の型アノテーション
        for arg in node.args.args:
            if arg.annotation:
                arg_type = self._get_type_name_from_ast(arg.annotation)
                if arg_type:
                    # 引数参照は中程度の依存
                    self._add_edge(
                        func_name, arg_type, RelationType.REFERENCES, weight=0.6
                    )

        # 戻り値の型アノテーション
        if node.returns:
            return_type = self._get_type_name_from_ast(node.returns)
            if return_type:
                # 戻り値参照は強い依存
                self._add_edge(func_name, return_type, RelationType.RETURNS, weight=0.8)

    def _handle_method_def(
        self, node: ast.FunctionDef, class_name: str, file_path: str
    ) -> None:
        """メソッド定義から依存を抽出"""
        method_name = f"{class_name}.{node.name}"
        method_node = GraphNode(
            qualified_name=f"{class_name}.{node.name}",
            name=method_name,
            node_type="method",
            attributes={
                "source_file": file_path,
                "line": node.lineno,
                "class_name": class_name,
            },
        )
        self._add_node(method_node)

        # メソッドの引数と戻り値
        for arg in node.args.args:
            if arg.annotation:
                arg_type = self._get_type_name_from_ast(arg.annotation)
                if arg_type:
                    self._add_edge(
                        method_name, arg_type, RelationType.REFERENCES, weight=0.6
                    )

        if node.returns:
            return_type = self._get_type_name_from_ast(node.returns)
            if return_type:
                self._add_edge(
                    method_name, return_type, RelationType.RETURNS, weight=0.8
                )

    def _handle_call(self, node: ast.Call, file_path: str) -> None:
        """関数呼び出しから依存を抽出"""
        if hasattr(node.func, "id"):
            func_name = node.func.id
            # 関数呼び出しノードを作成（必要に応じて）
            call_node = GraphNode(
                name=f"call_{func_name}",
                node_type="function_call",
                attributes={"source_file": file_path, "called_function": func_name},
            )
            self._add_node(call_node)

            # 呼び出し元の関数を探す（簡易的に）
            # 実際の実装ではコールスタックやコンテキストが必要
            self._add_edge(call_node.name, func_name, RelationType.CALLS, weight=0.8)
        elif isinstance(node.func, ast.Attribute):
            # obj.method() のような属性アクセス呼び出し
            self._handle_attribute_call(node.func, file_path)

    def _handle_import(self, node: ast.Import, file_path: str) -> None:
        """import文から依存を抽出"""
        for alias in node.names:
            module_name = alias.name
            import_node = GraphNode(
                name=module_name,
                node_type="module",
                attributes={"source_file": file_path, "import_type": "direct"},
            )
            self._add_node(import_node)

            # 現在のファイルがモジュールに依存
            current_module = Path(file_path).stem
            self._add_edge(current_module, module_name, RelationType.USES, weight=0.9)

    def _handle_import_from(self, node: ast.ImportFrom, file_path: str) -> None:
        """from import文から依存を抽出"""
        if node.module:
            module_name = node.module
            import_node = GraphNode(
                name=module_name,
                node_type="module",
                attributes={"source_file": file_path, "import_type": "from"},
            )
            self._add_node(import_node)

            # インポートされたシンボル
            for alias in node.names:
                symbol_name = alias.name
                symbol_node = GraphNode(
                    name=f"{module_name}.{symbol_name}",
                    node_type="imported_symbol",
                    attributes={"source_file": file_path, "imported_from": module_name},
                )
                self._add_node(symbol_node)

                # 依存関係
                current_module = Path(file_path).stem
                self._add_edge(
                    current_module, module_name, RelationType.USES, weight=0.9
                )
                self._add_edge(
                    symbol_node.name, module_name, RelationType.DEPENDS_ON, weight=0.8
                )

    def _handle_attribute(self, node: ast.Attribute, file_path: str) -> None:
        """属性アクセスから依存を抽出"""
        if hasattr(node.value, "id") and hasattr(node, "attr"):
            obj_name = node.value.id
            attr_name = node.attr

            # 属性アクセスノードを作成
            attr_node = GraphNode(
                name=f"{obj_name}.{attr_name}",
                node_type="attribute_access",
                attributes={
                    "source_file": file_path,
                    "object": obj_name,
                    "attribute": attr_name,
                },
            )
            self._add_node(attr_node)

            # オブジェクトへの依存
            self._add_edge(
                attr_node.name, obj_name, RelationType.REFERENCES, weight=0.7
            )

    def _handle_attribute_call(self, node: ast.Attribute, file_path: str) -> None:
        """属性を通じた関数呼び出しから依存を抽出"""
        if hasattr(node.value, "id") and hasattr(node, "attr"):
            obj_name = node.value.id
            method_name = node.attr

            # メソッド呼び出しノードを作成
            method_call_node = GraphNode(
                name=f"{obj_name}.{method_name}()",
                node_type="method_call",
                attributes={
                    "source_file": file_path,
                    "object": obj_name,
                    "method": method_name,
                },
            )
            self._add_node(method_call_node)

            # オブジェクトとメソッドへの依存
            self._add_edge(
                method_call_node.name, obj_name, RelationType.REFERENCES, weight=0.7
            )
            self._add_edge(
                method_call_node.name, method_name, RelationType.CALLS, weight=0.8
            )

    def _handle_assign(self, node: ast.Assign, file_path: str) -> None:
        """変数代入から依存を抽出"""
        if node.value and isinstance(node.value, ast.Call):
            # 関数呼び出しの検出（簡易版）
            if hasattr(node.value.func, "id"):
                func_name = node.value.func.id
                # 変数名を推定（targets[0]のid）
                if node.targets and hasattr(node.targets[0], "id"):
                    var_name = node.targets[0].id
                    var_node = GraphNode(
                        name=var_name,
                        node_type="variable",
                        attributes={"source_file": file_path, "line": node.lineno},
                    )
                    self._add_node(var_node)
                    self._add_edge(var_name, func_name, RelationType.CALLS)

    def _handle_annotation(
        self, node: ast.AnnAssign, class_name: str, file_path: str
    ) -> None:
        """型アノテーションから依存を抽出"""
        if node.annotation:
            annotated_type = self._get_type_name_from_ast(node.annotation)
            if annotated_type:
                self._add_edge(class_name, annotated_type, RelationType.REFERENCES)

    def _get_type_name_from_ast(self, node: ast.AST) -> Optional[str]:
        """ASTノードから型名を抽出（ForwardRef対応）"""
        if isinstance(node, ast.Name):
            return str(node.id)
        elif isinstance(node, ast.Attribute):
            # 例: module.Class → Class
            return str(node.attr)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            # ForwardRef（文字列リテラル、例: 'MyClass'）
            return node.value
        elif isinstance(node, ast.Subscript):
            # ジェネリック型（例: List[User] → User）
            if hasattr(node.slice, "id"):  # Python 3.9+
                return str(node.slice.id)
            elif hasattr(node.slice, "value") and hasattr(node.slice.value, "id"):
                return str(node.slice.value.id)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            # Union型（例: str | int、Python 3.10+）
            left_type = self._get_type_name_from_ast(node.left)
            right_type = self._get_type_name_from_ast(node.right)
            if left_type and right_type:
                return f"{left_type} | {right_type}"
            return left_type or right_type
        # その他の複雑な型は簡易的にスキップ
        return None

    def _extract_type_refs_from_string(self, type_str: str) -> list[str]:
        """型文字列から型参照を抽出"""
        refs = []
        # 簡易的な分割（List[str] -> ['List', 'str']）
        parts = (
            type_str.replace("[", " ")
            .replace("]", " ")
            .replace(",", " ")
            .replace("|", " ")
            .split()
        )
        for part in parts:
            part = part.strip()
            if part and part[0].isupper():  # クラス名らしきもの
                refs.append(part)
        return refs

    def _add_node(self, node: GraphNode) -> None:
        """ノードを追加（重複を避け、キャッシュを使用）"""
        if node.name not in self.nodes:
            self.nodes[node.name] = node
            self._node_cache[node.name] = node

    def _add_edge(
        self, source: str, target: str, relation: RelationType, weight: float = 1.0
    ) -> None:
        """エッジを追加（重み付き）"""
        if source != target and target not in self.visited_nodes:
            self.visited_nodes.add(target)
            edge_key = f"{source}->{target}:{relation}"
            edge = GraphEdge(
                source=source,
                target=target,
                relation_type=relation,
                weight=weight,
                metadata={"extraction_method": "AST_analysis"},
            )
            self.edges[edge_key] = edge
