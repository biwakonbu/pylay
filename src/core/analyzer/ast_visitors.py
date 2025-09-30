"""
AST訪問者モジュール

1パスで効率的に依存関係を抽出するNodeVisitorクラスを提供します。
"""

import ast
from pathlib import Path
from typing import Optional, Union

from src.core.analyzer.models import AnalyzerState, ParseContext
from src.core.analyzer.exceptions import ASTParseError
from src.core.schemas.graph_types import GraphNode, GraphEdge, RelationType

# 関数定義の共通型（Python 3.13+）
FunctionDefLike = Union[ast.FunctionDef, ast.AsyncFunctionDef]


class DependencyVisitor(ast.NodeVisitor):
    """
    依存関係抽出用のAST訪問者

    1パス走査で全ての依存関係を効率的に抽出します。
    """

    def __init__(self, state: AnalyzerState, context: ParseContext) -> None:
        """
        訪問者を初期化します。

        Args:
            state: アナライザー状態
            context: 解析コンテキスト
        """
        self.state = state
        self.context = context

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """クラス定義を訪問"""
        class_name = node.name

        # 循環参照チェック
        if self.state.is_processing(class_name):
            return

        self.state.start_processing(class_name)
        try:
            # クラスノードを追加
            class_node = GraphNode(
                name=class_name,
                node_type="class",
                attributes={
                    "source_file": str(self.context.file_path),
                    "line": node.lineno,
                    "column": getattr(node, "col_offset", 0),
                },
            )
            self._add_node(class_node)

            # 基底クラス（継承関係）
            for base in node.bases:
                base_names = self._get_type_names_from_ast(base)
                for base_name in base_names:
                    if base_name and base_name != class_name:
                        self._add_edge(
                            class_name, base_name, RelationType.INHERITS_FROM, weight=0.9
                        )

            # クラス内部を走査（コンテキスト更新）
            prev_class = self.context.current_class
            self.context.current_class = class_name
            self.generic_visit(node)
            self.context.current_class = prev_class
        finally:
            self.state.finish_processing(class_name)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """関数定義を訪問"""
        self._process_function_def(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """非同期関数定義を訪問"""
        self._process_function_def(node)

    def _process_function_def(self, node: FunctionDefLike) -> None:
        """
        関数定義の共通処理

        Args:
            node: FunctionDef または AsyncFunctionDef ノード
        """
        if self.context.in_class_context():
            # メソッドの場合
            self._visit_method_def(node)
        else:
            # トップレベル関数の場合
            self._visit_function_def(node)

        # 関数内部を走査
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """型アノテーション付き代入を訪問"""
        if self.context.in_class_context() and isinstance(node.target, ast.Name):
            # クラス属性のアノテーション
            assert self.context.current_class is not None
            type_names = self._get_type_names_from_ast(node.annotation)
            for type_name in type_names:
                if type_name:
                    self._add_edge(
                        self.context.current_class,
                        type_name,
                        RelationType.REFERENCES,
                        weight=0.6,
                    )
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        """import文を訪問"""
        for alias in node.names:
            module_name = alias.name
            import_node = GraphNode(
                name=module_name,
                node_type="module",
                attributes={
                    "source_file": str(self.context.file_path),
                    "import_type": "direct",
                },
            )
            self._add_node(import_node)

            # 現在のモジュールが依存
            self._add_edge(
                self.context.module_name, module_name, RelationType.USES, weight=0.9
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """from import文を訪問"""
        if node.module:
            module_name = node.module
            import_node = GraphNode(
                name=module_name,
                node_type="module",
                attributes={
                    "source_file": str(self.context.file_path),
                    "import_type": "from",
                },
            )
            self._add_node(import_node)

            # インポートされたシンボル
            for alias in node.names:
                symbol_name = alias.name
                symbol_node = GraphNode(
                    name=f"{module_name}.{symbol_name}",
                    node_type="imported_symbol",
                    attributes={
                        "source_file": str(self.context.file_path),
                        "imported_from": module_name,
                    },
                )
                self._add_node(symbol_node)

                # 依存関係
                self._add_edge(
                    self.context.module_name, module_name, RelationType.USES, weight=0.9
                )
                self._add_edge(
                    symbol_node.name,
                    module_name,
                    RelationType.DEPENDS_ON,
                    weight=0.8,
                )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """関数呼び出しを訪問"""
        if hasattr(node.func, "id"):
            func_name = node.func.id
            call_node = GraphNode(
                name=f"call_{func_name}",
                node_type="function_call",
                attributes={
                    "source_file": str(self.context.file_path),
                    "called_function": func_name,
                },
            )
            self._add_node(call_node)
            self._add_edge(call_node.name, func_name, RelationType.CALLS, weight=0.8)
        elif isinstance(node.func, ast.Attribute):
            self._visit_attribute_call(node.func)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """属性アクセスを訪問"""
        if hasattr(node.value, "id") and hasattr(node, "attr"):
            obj_name = node.value.id
            attr_name = node.attr

            attr_node = GraphNode(
                name=f"{obj_name}.{attr_name}",
                node_type="attribute_access",
                attributes={
                    "source_file": str(self.context.file_path),
                    "object": obj_name,
                    "attribute": attr_name,
                },
            )
            self._add_node(attr_node)
            self._add_edge(
                attr_node.name, obj_name, RelationType.REFERENCES, weight=0.7
            )
        self.generic_visit(node)

    def _visit_function_def(self, node: FunctionDefLike) -> None:
        """トップレベル関数定義の処理"""
        func_name = node.name
        func_node = GraphNode(
            name=func_name,
            node_type="function",
            attributes={
                "source_file": str(self.context.file_path),
                "line": node.lineno,
                "column": getattr(node, "col_offset", 0),
                "is_async": isinstance(node, ast.AsyncFunctionDef),
            },
        )
        self._add_node(func_node)

        # 引数の型アノテーション
        for arg in node.args.args:
            if arg.annotation:
                arg_types = self._get_type_names_from_ast(arg.annotation)
                for arg_type in arg_types:
                    if arg_type:
                        self._add_edge(
                            func_name, arg_type, RelationType.REFERENCES, weight=0.6
                        )

        # 戻り値の型アノテーション
        if node.returns:
            return_types = self._get_type_names_from_ast(node.returns)
            for return_type in return_types:
                if return_type:
                    self._add_edge(func_name, return_type, RelationType.RETURNS, weight=0.8)

    def _visit_method_def(self, node: FunctionDefLike) -> None:
        """メソッド定義の処理"""
        class_name = self.context.current_class
        if not class_name:
            return

        method_name = f"{class_name}.{node.name}"
        method_node = GraphNode(
            qualified_name=method_name,
            name=method_name,
            node_type="method",
            attributes={
                "source_file": str(self.context.file_path),
                "line": node.lineno,
                "class_name": class_name,
                "is_async": isinstance(node, ast.AsyncFunctionDef),
            },
        )
        self._add_node(method_node)

        # メソッドの引数と戻り値
        for arg in node.args.args:
            if arg.annotation:
                arg_types = self._get_type_names_from_ast(arg.annotation)
                for arg_type in arg_types:
                    if arg_type:
                        self._add_edge(
                            method_name, arg_type, RelationType.REFERENCES, weight=0.6
                        )

        if node.returns:
            return_types = self._get_type_names_from_ast(node.returns)
            for return_type in return_types:
                if return_type:
                    self._add_edge(
                        method_name, return_type, RelationType.RETURNS, weight=0.8
                    )

    def _visit_attribute_call(self, node: ast.Attribute) -> None:
        """属性を通じた関数呼び出しの処理"""
        if hasattr(node.value, "id") and hasattr(node, "attr"):
            obj_name = node.value.id
            method_name = node.attr

            method_call_node = GraphNode(
                name=f"{obj_name}.{method_name}()",
                node_type="method_call",
                attributes={
                    "source_file": str(self.context.file_path),
                    "object": obj_name,
                    "method": method_name,
                },
            )
            self._add_node(method_call_node)
            self._add_edge(
                method_call_node.name, obj_name, RelationType.REFERENCES, weight=0.7
            )
            self._add_edge(
                method_call_node.name, method_name, RelationType.CALLS, weight=0.8
            )

    def _get_type_names_from_ast(self, node: ast.AST) -> list[str]:
        """
        ASTノードから型名を抽出（ForwardRef対応、Union型は個別要素を返す）

        Args:
            node: 型を表すASTノード

        Returns:
            抽出された型名のリスト（Union型の場合は複数要素を返す）
        """
        if isinstance(node, ast.Name):
            return [str(node.id)]
        elif isinstance(node, ast.Attribute):
            return [str(node.attr)]
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            # ForwardRef（文字列リテラル）
            return [node.value]
        elif isinstance(node, ast.Subscript):
            # ジェネリック型（例: List[User] → User, Dict[str, List[int]] → [str, List[int]]）
            # Python 3.9+では複数パラメータはast.Tupleとして表現される
            if isinstance(node.slice, ast.Tuple):
                # 複数のジェネリック型パラメータ（例: Dict[str, int]）
                result: list[str] = []
                for elt in node.slice.elts:
                    result.extend(self._get_type_names_from_ast(elt))
                return result
            else:
                # 単一パラメータ（例: List[User]）- 再帰的に処理
                return self._get_type_names_from_ast(node.slice)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            # Union型（例: str | int） - 各要素を個別に返す
            left_types = self._get_type_names_from_ast(node.left)
            right_types = self._get_type_names_from_ast(node.right)
            return left_types + right_types
        return []

    def _get_type_name_from_ast(self, node: ast.AST) -> Optional[str]:
        """
        ASTノードから型名を抽出（後方互換性のため残す）

        注意: Union型の場合は最初の要素のみを返します。
        Union型の全要素を取得するには _get_type_names_from_ast を使用してください。
        """
        types = self._get_type_names_from_ast(node)
        return types[0] if types else None

    def _add_node(self, node: GraphNode) -> None:
        """ノードを追加（重複を避ける）"""
        if node.name not in self.state.nodes:
            self.state.nodes[node.name] = node

    def _add_edge(
        self, source: str, target: str, relation: RelationType, weight: float = 1.0
    ) -> None:
        """エッジを追加（重複を避ける）"""
        if source != target:
            edge_key = f"{source}->{target}:{relation}"
            if edge_key not in self.state.edges:
                edge = GraphEdge(
                    source=source,
                    target=target,
                    relation_type=relation,
                    weight=weight,
                    metadata={"extraction_method": "AST_analysis"},
                )
                self.state.edges[edge_key] = edge


class TypeAnnotationVisitor(ast.NodeVisitor):
    """
    型アノテーション専用の訪問者

    既存の型アノテーションを抽出します。
    """

    def __init__(self) -> None:
        """訪問者を初期化"""
        self.annotations: dict[str, str] = {}

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """型付き代入を訪問"""
        if isinstance(node.target, ast.Name):
            var_name = node.target.id
            self.annotations[var_name] = ast.unparse(node.annotation)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """関数定義を訪問"""
        self._process_function_annotations(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """非同期関数定義を訪問"""
        self._process_function_annotations(node)

    def _process_function_annotations(self, node: FunctionDefLike) -> None:
        """
        関数の型アノテーションを処理

        Args:
            node: FunctionDef または AsyncFunctionDef ノード
        """
        for arg in node.args.args:
            if arg.annotation and arg.arg not in self.annotations:
                self.annotations[arg.arg] = ast.unparse(arg.annotation)
        self.generic_visit(node)


def parse_ast(file_path: Path | str) -> ast.AST:
    """
    ファイルからASTを解析します。

    Args:
        file_path: Pythonファイルパス

    Returns:
        解析されたAST

    Raises:
        ASTParseError: 構文エラーの場合
    """
    file_path = Path(file_path)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source_code = f.read()
    except FileNotFoundError:
        raise ASTParseError(f"ファイルが見つかりません", file_path=str(file_path))
    except UnicodeDecodeError as e:
        raise ASTParseError(
            f"ファイルのエンコーディングエラー: {e}", file_path=str(file_path)
        )

    try:
        tree = ast.parse(source_code, filename=str(file_path))
        return tree
    except SyntaxError as e:
        raise ASTParseError(
            f"Python構文エラー: {e.msg}",
            line_number=e.lineno,
            file_path=str(file_path),
        )
