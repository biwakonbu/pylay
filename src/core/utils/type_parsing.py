"""
型文字列パース・型参照抽出ユーティリティ

型アノテーション文字列から型参照を抽出する統一ユーティリティを提供します。
複雑なジェネリクス、Union型、Callable型、前方参照などに対応し、
以下の3段階フォールバック戦略を使用します：

1. typing.eval() による型評価（最も精度が高い）
2. ast.parse() によるASTパース（中程度の精度）
3. 文字列分割による抽出（最終フォールバック）
"""

import ast
import logging

# 実行時の型解析処理に使用
# - get_args, get_origin: ジェネリック型の解析
# - ForwardRef: 前方参照の型チェック
from typing import ForwardRef, get_args, get_origin

logger = logging.getLogger(__name__)

# 組み込み型とtyping primitiveを除外するセット
BUILTINS_AND_PRIMITIVES = frozenset(
    {
        # 組み込み型
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
        # typing プリミティブ
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
        # コレクション型
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
)

# typing評価時に許可する属性のallowlist
ALLOWED_TYPING_ATTRS = frozenset(
    {
        # 基本型コンストラクタ
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
        # コレクション型
        "Sequence",
        "Mapping",
        "Iterable",
        "Iterator",
        "List",
        "Dict",
        "Set",
        "Tuple",
        "FrozenSet",
        # ジェネリック型ユーティリティ
        "get_origin",
        "get_args",
        "ForwardRef",
        # 型操作ユーティリティ
        "cast",
        "overload",
        "TypeAlias",
        "Concatenate",
        "ParamSpec",
        "TypeGuard",
        "Unpack",
        # Python 3.10+の新機能
        "TypeVarTuple",
        "Never",
        "Self",
        "LiteralString",
        "assert_type",
        "reveal_type",
        "dataclass_transform",
        # 抽象基底クラス
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
)


def extract_type_references(
    type_str: str,
    *,
    exclude_builtins: bool = True,
    deduplicate: bool = True,
) -> list[str]:
    """
    型文字列から型参照を抽出

    複雑な型アノテーション（Optional, Dict, List, Callable, Union等）を
    正しくパースし、ユーザー定義型名を抽出します。

    Args:
        type_str: 型を表す文字列（例: "Optional[Dict[str, List[int]]]"）
        exclude_builtins: 組み込み型とtyping primitiveを除外するか（デフォルト: True）
        deduplicate: 重複を除去してソート済みリストを返すか（デフォルト: True）

    Returns:
        抽出された型参照のリスト

    Examples:
        >>> extract_type_references("Dict[str, List[MyClass]]")
        ['MyClass']
        >>> extract_type_references("Optional[Union[Foo, Bar]]")
        ['Bar', 'Foo']
        >>> extract_type_references("int | MyType | str")
        ['MyType']
    """
    refs: set[str] = set()

    # 除外する型名のセット
    excluded_types = BUILTINS_AND_PRIMITIVES if exclude_builtins else frozenset()

    def extract_from_typing_obj(obj: object) -> None:
        """typingオブジェクトから型参照を再帰的に抽出"""
        try:
            origin = get_origin(obj)
            args = get_args(obj)

            # originが存在する場合（Generic等）
            if origin is not None:
                # originが型の場合、その名前を抽出
                if hasattr(origin, "__name__"):
                    name = origin.__name__
                    if name not in excluded_types:
                        refs.add(name)

                # 型引数を再帰的に処理
                for arg in args:
                    extract_from_typing_obj(arg)
            # 通常の型オブジェクト
            elif hasattr(obj, "__name__"):
                name = getattr(obj, "__name__", None)
                if isinstance(name, str) and name not in excluded_types:
                    refs.add(name)
            # ForwardRef（文字列型参照）
            elif isinstance(obj, ForwardRef):
                ref_name = obj.__forward_arg__
                if ref_name not in excluded_types:
                    refs.add(ref_name)
        except (AttributeError, TypeError):
            # 型オブジェクトでない場合はスキップ
            pass

    def extract_from_ast_node(node: ast.AST) -> None:
        """ASTノードから型参照を抽出"""
        if isinstance(node, ast.Name):
            if node.id not in excluded_types:
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
                if type_name not in excluded_types:
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
        if inner and inner not in excluded_types:
            refs.add(inner)
            return sorted(refs) if deduplicate else list(refs)

    # まずtyping評価を試みる
    try:
        import typing

        # セキュリティ: allowlist方式で必要最小限の属性のみ許可
        typing_ns = {k: v for k, v in typing.__dict__.items() if k in ALLOWED_TYPING_ATTRS}
        typing_ns["__builtins__"] = {}

        # TODO: 将来的にはASTパースのみで処理を完結させる移行を検討
        # 現在の多層防御（eval失敗→ASTフォールバック）は有効だが、
        # eval()によるセキュリティリスクを完全に排除するため、
        # ASTパーサーの精度向上とともにeval()の使用を段階的に削減する
        obj = eval(type_str, typing_ns)
        extract_from_typing_obj(obj)
        if refs:
            return sorted(refs) if deduplicate else list(refs)
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
        parts = type_str.replace("[", " ").replace("]", " ").replace(",", " ").replace("|", " ").split()
        for part in parts:
            part = part.strip()
            if part and part[0].isupper() and part not in excluded_types:
                refs.add(part)

    return sorted(refs) if deduplicate else list(refs)


def validate_type_string(type_str: str) -> tuple[bool, str | None]:
    """
    型文字列の妥当性を検証

    Args:
        type_str: 検証する型文字列

    Returns:
        (妥当性, エラーメッセージ) のタプル。妥当な場合は (True, None)
    """
    if not type_str or not isinstance(type_str, str):
        return False, "型文字列が空またはstr型ではありません"

    try:
        import typing

        typing_ns = {k: v for k, v in typing.__dict__.items() if k in ALLOWED_TYPING_ATTRS}
        typing_ns["__builtins__"] = {}
        eval(type_str, typing_ns)
        return True, None
    except (NameError, SyntaxError, AttributeError, TypeError):
        # typing評価失敗の場合はASTパースを試みる
        try:
            ast.parse(type_str, mode="eval")
            return True, None
        except SyntaxError as ast_err:
            return False, f"型文字列のパースに失敗: {ast_err}"
    except Exception as e:
        return False, f"予期しないエラー: {e}"
