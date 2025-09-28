"""
依存関係抽出モジュール

Python AST を使用してコードを解析し、型依存グラフを構築します。
NetworkX を使用して依存ツリーを作成し、視覚化を可能にします。
"""

import ast
import networkx as nx
from typing import Any, Union
from collections.abc import Mapping


class DependencyExtractor(ast.NodeVisitor):
    """
    AST を走査して型依存関係を抽出するビジタークラス。
    """

    def __init__(self) -> None:
        self.graph = nx.DiGraph()
        self.current_scope: list[str] = []
        self.visited_nodes: set[str] = set()  # 循環参照防止用

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
                    self.graph.add_edge(arg_type, func_name, relation="argument")
                    self._add_type_dependencies(arg_type)

        # 戻り値の型依存を追加
        if node.returns:
            return_type = self._extract_type_annotation(node.returns)
            if return_type:
                self.graph.add_edge(func_name, return_type, relation="return")
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
                self.graph.add_edge(var_type, var_name, relation="assignment")
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
                self.graph.add_edge(base_name, class_name, relation="inheritance")

        self.generic_visit(node)

    def _extract_type_annotation(self, annotation_node: ast.AST) -> str | None:
        """
        ASTノードから型アノテーションを抽出します。
        ForwardRef（文字列リテラル）と複雑なジェネリック型を適切に処理します。
        """
        if annotation_node is None:
            return None
        elif isinstance(annotation_node, ast.Name):
            # シンプルな型名（例: int, str）
            return annotation_node.id
        elif isinstance(annotation_node, ast.Constant) and isinstance(
            annotation_node.value, str
        ):
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
        elif isinstance(annotation_node, ast.BinOp) and isinstance(
            annotation_node.op, ast.BitOr
        ):
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

    def _extract_type_params(self, slice_node: ast.AST) -> list[str] | None:
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
                    self.graph.add_edge(base_type, type_str, relation="generic")
                    self._add_type_dependencies(base_type)

                # 型パラメータの依存関係も追加（例: Dict[str, List[int]] の場合、strとList[int]）
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


def extract_dependencies_from_code(code: str) -> nx.DiGraph:
    """
    コードから依存関係を抽出します。

    Args:
        code: 解析対象のPythonコード

    Returns:
        NetworkXの有向グラフ（依存関係）
    """
    tree = ast.parse(code)
    extractor = DependencyExtractor()
    extractor.visit(tree)
    return extractor.get_dependencies()


def extract_dependencies_from_file(file_path: str) -> nx.DiGraph:
    """
    ファイルから依存関係を抽出します。

    Args:
        file_path: Pythonファイルのパス

    Returns:
        NetworkXの有向グラフ（依存関係）
    """
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()
    return extract_dependencies_from_code(code)


def convert_graph_to_yaml_spec(graph: nx.DiGraph) -> dict[str, Any]:
    """
    依存グラフをYAML型仕様に変換します。

    Args:
        graph: 依存関係のNetworkXグラフ

    Returns:
        YAML型仕様の辞書
    """
    dependencies = {}

    for node in graph.nodes():
        node_type = graph.nodes[node].get("type", "unknown")
        predecessors = list(graph.predecessors(node))
        successors = list(graph.successors(node))

        dependencies[node] = {
            "type": node_type,
            "depends_on": predecessors,
            "used_by": successors,
            "relations": [
                graph.edges[edge]["relation"]
                for edge in graph.in_edges(node)
                if "relation" in graph.edges[edge]
            ],
        }

    return {"dependencies": dependencies}


def visualize_dependencies(graph: nx.DiGraph, output_path: str = "deps.png") -> None:
    """
    依存関係をGraphvizで視覚化します。

    Args:
        graph: 依存関係のNetworkXグラフ
        output_path: 出力画像のパス
    """
    try:
        import pydot
        from networkx.drawing.nx_pydot import graphviz_layout

        # NetworkXグラフをpydotグラフに変換
        pydot_graph = nx.drawing.nx_pydot.to_pydot(graph)

        # ノードの色を設定（型によって異なる色）
        for node in pydot_graph.get_nodes():
            node_name = node.get_name().strip('"')
            node_data = graph.nodes.get(node_name, {})
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
        for edge in pydot_graph.get_edges():
            edge_data = graph.edges.get(
                (edge.get_source().strip('"'), edge.get_destination().strip('"'))
            )
            if edge_data:
                relation = edge_data.get("relation", "")
                if relation == "argument":
                    edge.set_color("blue")
                elif relation == "return":
                    edge.set_color("green")
                elif relation == "inheritance":
                    edge.set_color("red")
                elif relation == "generic":
                    edge.set_color("orange")
                else:
                    edge.set_color("black")

        # レイアウトを設定
        pydot_graph.set_rankdir("TB")  # Top to Bottom
        pydot_graph.set_size("8,6")  # サイズ設定

        # 画像を保存
        pydot_graph.write_png(output_path)
        print(f"依存関係グラフを {output_path} に保存しました。")

    except ImportError as e:
        print(
            f"Graphviz または pydot がインストールされていないため、視覚化をスキップします: {e}"
        )
    except Exception as e:
        print(f"視覚化中にエラーが発生しました: {e}")
