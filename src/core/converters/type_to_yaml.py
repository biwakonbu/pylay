import inspect
from typing import Any, get_origin, get_args, Union as TypingUnion, ForwardRef, Generic
from pydantic import BaseModel


def _recursive_dump(obj: Any) -> Any:
    """Pydanticモデルを再帰的にdictに変換"""
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    elif isinstance(obj, dict):
        return {k: _recursive_dump(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_recursive_dump(v) for v in obj]
    else:
        return obj


from ruamel.yaml import YAML
from pathlib import Path

from src.core.schemas.yaml_type_spec import (
    TypeSpec,
    ListTypeSpec,
    DictTypeSpec,
    UnionTypeSpec,
    GenericTypeSpec,
    TypeSpecOrRef,
)

MAX_DEPTH = 10  # Generic再帰の深さ制限


def _get_basic_type_str(typ: type[Any]) -> str:
    """基本型の型名を取得"""
    basic_type_mapping = {
        str: "str",
        int: "int",
        float: "float",
        bool: "bool",
    }
    return basic_type_mapping.get(typ, "any")


def _get_type_name(typ: type[Any]) -> str:
    """型名を取得（ジェネリック型の場合も考慮）"""
    if isinstance(typ, ForwardRef):
        # ForwardRefの場合、アンカー形式で出力
        return f"&{typ.__forward_arg__}"

    # UnionTypeの場合、argsから動的名前生成
    origin = get_origin(typ)
    if origin is TypingUnion or str(origin) == "<class 'types.UnionType'>":
        args = get_args(typ)
        if args:
            arg_names = [_get_type_name(arg) for arg in args]
            return f"Union[{', '.join(arg_names)}]"
        return "Union"

    if hasattr(typ, "__name__"):
        return typ.__name__

    # origin_nameがNoneの場合のフォールバック
    if hasattr(typ, "__name__"):
        return typ.__name__
    return str(typ)


def _recurse_generic_args(args: tuple, depth: int = 0) -> list[TypeSpecOrRef]:
    """再帰的にGeneric引数を展開（深さ制限付き）"""
    if depth > MAX_DEPTH:
        raise RecursionError(f"Generic型の深さが{MAX_DEPTH}を超えました")

    result: list[TypeSpecOrRef] = []
    for arg in args:
        if get_origin(arg) is None:
            # 非ジェネリック型
            if arg in {str, int, float, bool}:
                result.append(type_to_spec(arg))
            else:
                result.append(_get_type_name(arg))
        else:
            # ジェネリック型の場合、再帰的に展開
            param_spec = type_to_spec(arg)
            result.append(param_spec)
    return result


def _get_docstring(typ: type[Any]) -> str | None:
    """型またはクラスのdocstringを取得"""
    return inspect.getdoc(typ)


def _get_field_docstring(cls: type[Any], field_name: str) -> str | None:
    """クラスフィールドのdocstringを取得"""
    try:
        # dataclassesの場合
        if hasattr(cls, "__dataclass_fields__"):
            field = cls.__dataclass_fields__.get(field_name)
            if field and field.metadata.get("doc"):
                doc = field.metadata["doc"]
                return str(doc) if doc is not None else None

        # Pydantic Fieldの場合
        annotations = getattr(cls, "__annotations__", {})
        if field_name in annotations:
            # クラス属性としてdocstringを探す
            doc_attr_name = f"{field_name}_doc"
            if hasattr(cls, doc_attr_name):
                doc_value = getattr(cls, doc_attr_name)
                if isinstance(doc_value, str):
                    return doc_value

            # 型アノテーションにdocstringが含まれる場合（簡易的な対応）
            # 実際にはより洗練された方法が必要
    except Exception:
        pass
    return None


def _get_class_properties_with_docstrings(cls: type[Any]) -> dict[str, TypeSpecOrRef]:
    """クラスのプロパティとフィールドdocstringを取得"""
    properties: dict[str, TypeSpecOrRef] = {}

    # クラスアノテーションからフィールドを取得
    annotations = getattr(cls, "__annotations__", {})

    for field_name, field_type in annotations.items():
        # フィールドの型をTypeSpecに変換
        try:
            field_spec = type_to_spec(field_type)
            # フィールドのdocstringを取得
            field_doc = _get_field_docstring(cls, field_name)
            if field_doc:
                # docstringがある場合はdescriptionに設定
                field_spec.description = field_doc
            properties[field_name] = field_spec
        except Exception:
            # 型変換に失敗した場合は基本的なTypeSpecを作成
            properties[field_name] = TypeSpec(
                name=field_name,
                type="unknown",
                description=_get_field_docstring(cls, field_name),
            )

    return properties


def type_to_spec(typ: type[Any]) -> TypeSpec:
    """Python型をTypeSpecに変換（v1.1対応）"""
    origin = get_origin(typ)
    args = get_args(typ)

    # docstringを取得
    description = _get_docstring(typ)

    # 型名を取得
    type_name = _get_type_name(typ)

    if origin is None:
        # 基本型またはカスタムクラス
        if typ in {str, int, float, bool}:
            type_str = _get_basic_type_str(typ)
            return TypeSpec(name=type_name, type=type_str, description=description)
        else:
            # カスタムクラスはdict型として扱い、フィールドのdocstringを取得
            properties = _get_class_properties_with_docstrings(typ)
            return DictTypeSpec(
                name=type_name,
                type="dict",
                description=description,
                properties=properties,
            )

    elif issubclass(origin, Generic) or origin is Generic:
        # Generic[T]型（カスタムGenericサポート）
        if args:
            generic_args = _recurse_generic_args(args)
            return GenericTypeSpec(
                name=type_name, params=generic_args, description=description
            )
        else:
            return GenericTypeSpec(name=type_name, params=[], description=description)

    elif origin is list:
        # List型は常にtype: "list" として処理
        if args:
            item_type = args[0]
            if get_origin(item_type) is None and item_type not in {
                str,
                int,
                float,
                bool,
            }:
                # カスタム型の場合、参照として保持
                return ListTypeSpec(
                    name=type_name,
                    items=_get_type_name(item_type),  # 参照文字列として保持
                    description=description,
                )
            else:
                # 基本型の場合、TypeSpecとして展開
                items_spec = type_to_spec(item_type)
                return ListTypeSpec(
                    name=type_name, items=items_spec, description=description
                )
        else:
            # 型パラメータなし
            return ListTypeSpec(
                name=type_name,
                items=TypeSpec(name="any", type="any"),
                description=description,
            )

    elif origin is dict:
        if args and len(args) >= 2:
            key_type, value_type = args[0], args[1]

            # Dict[str, T] のような場合、propertiesとして扱う
            if key_type == str:
                dict_properties: dict[str, TypeSpecOrRef] = {}

                # 値型がカスタム型の場合、参照として保持
                if get_origin(value_type) is None and value_type not in {
                    str,
                    int,
                    float,
                    bool,
                }:
                    # 各プロパティの型名をキーとして参照を保持（実際のプロパティ解決は別途）
                    dict_properties[_get_type_name(value_type)] = _get_type_name(
                        value_type
                    )
                else:
                    # 基本型の場合、TypeSpecとして展開
                    value_spec = type_to_spec(value_type)
                    dict_properties[_get_type_name(value_type)] = value_spec

                return DictTypeSpec(
                    name=type_name, properties=dict_properties, description=description
                )
            else:
                # キーがstr以外の場合、簡易的にanyとして扱う
                return DictTypeSpec(
                    name=type_name, properties={}, description=description
                )
        else:
            return DictTypeSpec(name=type_name, properties={}, description=description)

    elif origin is TypingUnion or str(origin) == "<class 'types.UnionType'>":
        # Union型（Union[int, str] など）
        if args:
            variants: list[TypeSpecOrRef] = []

            for arg in args:
                if get_origin(arg) is None and arg not in {str, int, float, bool}:
                    # カスタム型の場合、参照として保持
                    variants.append(_get_type_name(arg))
                else:
                    # 基本型の場合、TypeSpecとして展開
                    variant_spec = type_to_spec(arg)
                    variants.append(variant_spec)

            return UnionTypeSpec(
                name=type_name, variants=variants, description=description
            )
        else:
            union_variants: list[TypeSpecOrRef] = []
            return UnionTypeSpec(
                name=type_name, variants=union_variants, description=description
            )

    else:
        # 未サポート型
        return TypeSpec(name=type_name, type="unknown", description=description)


def type_to_yaml(
    typ: type[Any], output_file: str | None = None, as_root: bool = True
) -> str | dict[str, dict]:
    """型をYAML文字列に変換、またはファイル出力 (v1.1対応)"""
    spec = type_to_spec(typ)

    # v1.1構造: nameフィールドを除外して出力
    spec_data = _recursive_dump(spec.model_dump(exclude={"name"}))

    if as_root:
        # 単一型: 型名をキーとして出力
        yaml_data = {_get_type_name(typ): spec_data}
        yaml_parser = YAML()
        yaml_parser.preserve_quotes = True
        from io import StringIO

        output = StringIO()
        yaml_parser.dump(yaml_data, output)
        yaml_str = output.getvalue()
    else:
        # 従来形式 (互換性用)
        yaml_parser = YAML()
        yaml_parser.preserve_quotes = True
        from io import StringIO

        output = StringIO()
        yaml_parser.dump(spec.model_dump(), output)
        yaml_str = output.getvalue()

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(yaml_str)

    return yaml_str if as_root else yaml_str


def types_to_yaml(types: dict[str, type[Any]], output_file: str | None = None) -> str:
    """複数型をYAML文字列に変換 (v1.1対応)"""
    specs = {}
    for name, typ in types.items():
        spec = type_to_spec(typ)
        # nameフィールドを除外
        spec_data = spec.model_dump(exclude={"name"})
        specs[name] = spec_data

    # types: を省略して直接型定義を出力
    yaml_parser = YAML()
    yaml_parser.preserve_quotes = True
    from io import StringIO

    output = StringIO()
    yaml_parser.dump(specs, output)
    yaml_str = output.getvalue()

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(yaml_str)

    return yaml_str


def extract_types_from_module(module_path: str | Path) -> str | None:
    """Pythonモジュールから型を抽出してYAML形式で返す

    Args:
        module_path: Pythonモジュールのパス（.pyファイル）

    Returns:
        YAML形式の型定義文字列、または型定義がない場合 None
    """
    import ast

    module_path = Path(module_path)

    # モジュールから型定義を抽出
    type_definitions: dict[str, Any] = {}

    try:
        # AST解析で型定義を抽出
        with open(module_path, "r", encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source)

        for node in ast.walk(tree):
            # クラス定義（Pydantic BaseModelなど）
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                # 基底クラスを取得
                base_classes = []
                if node.bases:
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            base_classes.append(base.id)
                        elif isinstance(base, ast.Attribute):
                            # typing.List などの場合
                            base_classes.append(ast.unparse(base))

                # クラス情報を記録
                type_definitions[class_name] = {
                    "type": "class",
                    "bases": base_classes,
                    "docstring": ast.get_docstring(node),
                }

            # 変数アノテーション付きの代入（型エイリアスとして扱う）
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                var_name = node.target.id
                if node.annotation:
                    var_type = ast.unparse(node.annotation)
                    type_definitions[var_name] = {
                        "type": "type_alias",
                        "alias_to": var_type,
                        "docstring": None,  # AnnAssignにはdocstringがないため、Noneを返す
                    }

            # 関数定義はスキップ（独自型ではないため）
            # elif isinstance(node, ast.FunctionDef):
            #     ... (コメントアウト: function混入を防ぐ)

    except Exception as e:
        # AST解析に失敗した場合はNoneを返す
        print(f"AST解析エラー: {e}")
        return None

    # 抽出された型定義をYAML形式に変換（空ならNone）
    if type_definitions:
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=4, offset=2)

        # 出力用の構造を作成（types: を省略して直接型定義を出力）
        output_data = type_definitions

        import io

        output = io.StringIO()
        yaml.dump(output_data, output)
        return output.getvalue().strip()
    else:
        return None  # 空の場合、Noneを返す（ノイズ回避）


# 例
if __name__ == "__main__":
    # from typing import List, Dict, Union  # Not needed with built-in types

    # テスト型
    UserId = str  # NewTypeではないが簡易
    Users = list[dict[str, str]]
    Result = int | str

    print("v1.1形式出力:")
    print(type_to_yaml(Users, as_root=True))
    print("\n従来形式出力:")
    print(type_to_yaml(type(Result), as_root=False))
