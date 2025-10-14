"""
依存関係抽出モジュール

Python AST を使用してコードを解析し、型依存グラフを構築します。
NetworkX を使用して依存ツリーを作成し、視覚化を可能にします。
"""

import ast
import logging
from pathlib import Path
from typing import Any

import networkx as nx

from src.core.schemas.graph import TypeDependencyGraph
from src.core.schemas.types import NodeId, ScopeStack, TypeParamList

logger = logging.getLogger(__name__)


class DependencyExtractor(ast.NodeVisitor):
    """
    AST を走査して型依存関係を抽出するビジタークラス。
    """

    def __init__(self) -> None:
        self.graph = nx.DiGraph()
        self.current_scope: ScopeStack = []
        self.visited_nodes: set[NodeId] = set()  # 循環参照防止用

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """
        関数定義を処理し、引数と戻り値の型依存を抽出。
        """
        func_name = node.name
        self.graph.add_node(func_name, type="function")

        # 引数の型依存を追加
        for arg in node.args.args:
            if arg.annotation:
                arg_type = self._extract_type_annotation(arg.annotation)
                if arg_type:
                    self.graph.add_edge(arg_type, func_name, relation_type="argument")
                    self._add_type_dependencies(arg_type)

        # 戻り値の型依存を追加
        if node.returns:
            return_type = self._extract_type_annotation(node.returns)
            if return_type:
                self.graph.add_edge(func_name, return_type, relation_type="returns")
                self._add_type_dependencies(return_type)

        # 関数本体を処理
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """
        型付きの代入を処理。
        """
        if isinstance(node.target, ast.Name):
            var_name = node.target.id
            var_type = self._extract_type_annotation(node.annotation)
            self.graph.add_node(var_name, type="variable")
            if var_type:
                self.graph.add_edge(var_type, var_name, relation_type="assignment")
                self._add_type_dependencies(var_type)

        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """
        クラス定義を処理し、基底クラスの依存を抽出。
        """
        class_name = node.name
        self.graph.add_node(class_name, type="class")

        # 基底クラスの依存を追加
        for base in node.bases:
            base_name = self._extract_type_annotation(base)
            if base_name:
                self.graph.add_edge(base_name, class_name, relation_type="inherits_from")

        self.generic_visit(node)

    def _extract_type_annotation(self, annotation_node: ast.AST | None) -> str | None:
        """
        ASTノードから型アノテーションを抽出します。
        ForwardRef（文字列リテラル）と複雑なジェネリック型を適切に処理します。
        """
        if annotation_node is None:
            return None
        if isinstance(annotation_node, ast.Name):
            # シンプルな型名（例: int, str）
            return annotation_node.id
        elif isinstance(annotation_node, ast.Constant) and isinstance(annotation_node.value, str):
            # ForwardRef（文字列リテラル、例: 'MyClass'）
            return annotation_node.value
        elif isinstance(annotation_node, ast.Subscript):
            # ジェネリック型（例: List[str], Dict[str, int]）
            base_type = self._extract_type_annotation(annotation_node.value)
            if base_type:
                slice_node = annotation_node.slice
                param_types = self._extract_type_params(slice_node)
                if param_types:
                    return f"{base_type}[{', '.join(param_types)}]"
            return base_type
        elif isinstance(annotation_node, ast.BinOp) and isinstance(annotation_node.op, ast.BitOr):
            # Union型（例: str | int、Python 3.10+）
            left_type = self._extract_type_annotation(annotation_node.left)
            right_type = self._extract_type_annotation(annotation_node.right)
            if left_type and right_type:
                return f"{left_type} | {right_type}"
            return left_type or right_type
        elif isinstance(annotation_node, ast.Attribute):
            # 属性アクセス（例: typing.List）
            return ast.unparse(annotation_node)
        else:
            # その他の場合
            return ast.unparse(annotation_node)

    def _extract_type_params(self, slice_node: ast.AST) -> TypeParamList | None:
        """
        型パラメータを抽出します。
        """
        if isinstance(slice_node, ast.Tuple):
            # 複数の型パラメータ（例: Dict[str, int]）
            param_types = []
            for elt in slice_node.elts:
                param_type = self._extract_type_annotation(elt)
                if param_type:
                    param_types.append(param_type)
            return param_types if param_types else None
        else:
            # 単一の型パラメータ（例: List[str]）
            param_type = self._extract_type_annotation(slice_node)
            return [param_type] if param_type else None

    def _add_type_dependencies(self, type_str: str) -> None:
        """
        型文字列から依存関係を再帰的に追加。
        循環参照を検出して防止します。
        """
        if not type_str or type_str in self.visited_nodes:
            return  # 循環参照防止

        self.visited_nodes.add(type_str)
        self.graph.add_node(type_str, type="type")

        try:
            if "[" in type_str and "]" in type_str:
                # ジェネリック型の場合
                base_type = type_str.split("[")[0]
                self.graph.add_node(base_type, type="type")
                if base_type != type_str:
                    self.graph.add_edge(base_type, type_str, relation_type="generic")
                    self._add_type_dependencies(base_type)

                # 型パラメータの依存関係も追加
                # （例: Dict[str, List[int]] の場合、strとList[int]）
                param_part = type_str[type_str.find("[") + 1 : type_str.rfind("]")]
                if "," in param_part:
                    # 複数のパラメータ
                    params = [p.strip() for p in param_part.split(",")]
                    for param in params:
                        self._add_type_dependencies(param)
                else:
                    # 単一のパラメータ
                    self._add_type_dependencies(param_part)
        finally:
            self.visited_nodes.remove(type_str)

    def get_dependencies(self) -> nx.DiGraph:
        """
        構築された依存グラフを返します。
        """
        return self.graph


def extract_dependencies_from_code(code: str) -> TypeDependencyGraph:
    """
    コードから依存関係を抽出します。

    Args:
        code: 解析対象のPythonコード

    Returns:
        TypeDependencyGraph（依存関係グラフ）
    """
    tree = ast.parse(code)
    extractor = DependencyExtractor()
    extractor.visit(tree)
    nx_graph = extractor.get_dependencies()

    # TypeDependencyGraph.from_networkx() は "relation_type" を期待するため、
    # "relation" 属性を "relation_type" にコピー
    for _u, _v, data in nx_graph.edges(data=True):
        if "relation" in data:
            data["relation_type"] = data["relation"]

    return TypeDependencyGraph.from_networkx(nx_graph)


def extract_dependencies_from_file(file_path: Path | str) -> TypeDependencyGraph:
    """
    ファイルから依存関係を抽出します。

    Args:
        file_path: Pythonファイルのパス (Path または str)

    Returns:
        TypeDependencyGraph（依存関係グラフ）
    """
    with open(str(file_path), encoding="utf-8") as f:
        code = f.read()
    return extract_dependencies_from_code(code)


def convert_graph_to_yaml_spec(
    graph: TypeDependencyGraph | nx.DiGraph,
) -> dict[str, Any]:
    """
    依存グラフをYAML型仕様に変換します。

    Args:
        graph: 依存関係のグラフ（TypeDependencyGraphまたはNetworkX DiGraph）

    Returns:
        YAML型仕様の辞書
    """
    # TypeDependencyGraphをNetworkX DiGraphに変換
    if isinstance(graph, TypeDependencyGraph):
        nx_graph = graph.to_networkx()
    else:
        nx_graph = graph

    dependencies = {}

    for node in nx_graph.nodes():
        node_type = nx_graph.nodes[node].get("type", "unknown")
        predecessors = list(nx_graph.predecessors(node))
        successors = list(nx_graph.successors(node))

        # エッジ属性の正規化: relation_type を優先し、なければ relation にフォールバック
        relations = []
        for edge in nx_graph.in_edges(node):
            edge_data = nx_graph.edges[edge]
            relation = edge_data.get("relation_type") or edge_data.get("relation")
            if relation:
                relations.append(relation)

        dependencies[node] = {
            "type": node_type,
            "depends_on": predecessors,
            "used_by": successors,
            "relations": relations,
        }

    return {"dependencies": dependencies}


def visualize_dependencies(graph: TypeDependencyGraph | nx.DiGraph, output_path: str = "deps.png") -> None:
    """
    依存関係をGraphvizで視覚化します。

    Args:
        graph: 依存関係のグラフ（TypeDependencyGraphまたはNetworkX DiGraph）
        output_path: 出力画像のパス
    """
    # TypeDependencyGraphをNetworkX DiGraphに変換
    if isinstance(graph, TypeDependencyGraph):
        nx_graph = graph.to_networkx()
    else:
        nx_graph = graph

    try:
        # NetworkXグラフをpydotグラフに変換
        import networkx.drawing.nx_pydot as nx_pydot

        pydot_graph = nx_pydot.to_pydot(nx_graph)  # type: ignore[attr-defined]

        # ノードの色を設定（型によって異なる色）
        for node in pydot_graph.get_node_list():  # type: ignore[attr-defined]
            node_name = node.get_name().strip('"')
            node_data = nx_graph.nodes.get(node_name, {})
            node_type = node_data.get("type", "unknown")

            if node_type == "function":
                node.set_color("lightblue")
            elif node_type == "class":
                node.set_color("lightgreen")
            elif node_type == "type":
                node.set_color("lightyellow")
            else:
                node.set_color("lightgray")

        # エッジの色を設定（関係によって異なる色）
        for edge in pydot_graph.get_edge_list():  # type: ignore[attr-defined]
            edge_data = nx_graph.edges.get((edge.get_source().strip('"'), edge.get_destination().strip('"')))
            if edge_data:
                # エッジ属性の正規化: relation_type を優先し、
                # なければ relation にフォールバック
                relation = edge_data.get("relation_type") or edge_data.get("relation", "")
                if relation == "argument":
                    edge.set_color("blue")
                elif relation in ("returns", "return"):
                    edge.set_color("green")
                elif relation in ("inherits_from", "inheritance"):
                    edge.set_color("red")
                elif relation == "generic":
                    edge.set_color("orange")
                else:
                    edge.set_color("black")

        # レイアウトを設定
        pydot_graph.set_rankdir("TB")  # type: ignore[attr-defined] # 上から下
        pydot_graph.set_size("8,6")  # type: ignore[attr-defined] # サイズ設定

        # 画像を保存
        pydot_graph.write_png(output_path)
        print(f"依存関係グラフを {output_path} に保存しました。")

    except ImportError as e:
        logger.warning("Graphviz/pydot が未インストールのため視覚化をスキップします: %s", e)
    except Exception:
        logger.exception("視覚化中にエラーが発生しました")
