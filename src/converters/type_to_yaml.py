import yaml
import inspect
from typing import Any, get_origin, get_args, Dict, Union as TypingUnion
from pydantic import ValidationError

from src.schemas.yaml_type_spec import TypeSpec, ListTypeSpec, DictTypeSpec, UnionTypeSpec, TypeSpecOrRef

def _get_basic_type_str(typ: type[Any]) -> str:
    """基本型の型名を取得"""
    basic_type_mapping = {
        str: 'str',
        int: 'int',
        float: 'float',
        bool: 'bool',
    }
    return basic_type_mapping.get(typ, 'any')

def _get_type_name(typ: type[Any]) -> str:
    """型名を取得（ジェネリック型の場合も考慮）"""
    if hasattr(typ, '__name__'):
        return typ.__name__
    # ジェネリック型の場合
    origin = get_origin(typ)
    if origin:
        origin_name = getattr(origin, '__name__', None)
        if origin_name:
            # List[Dict[str, str]] -> List
            return origin_name
    return str(typ)

def _get_docstring(typ: type[Any]) -> str | None:
    """型またはクラスのdocstringを取得"""
    return inspect.getdoc(typ)

def _get_field_docstring(cls: type[Any], field_name: str) -> str | None:
    """クラスフィールドのdocstringを取得"""
    try:
        # dataclassesの場合
        if hasattr(cls, '__dataclass_fields__'):
            field = cls.__dataclass_fields__.get(field_name)
            if field and field.metadata.get('doc'):
                return field.metadata['doc']

        # Pydantic Fieldの場合
        annotations = getattr(cls, '__annotations__', {})
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
            # カスタムクラスはdict型として扱う（プロパティは後で追加）
            return TypeSpec(name=type_name, type='dict', description=description)

    elif origin is list:
        # List型は常にtype: "list" として処理
        if args:
            item_type = args[0]
            if get_origin(item_type) is None and item_type not in {str, int, float, bool}:
                # カスタム型の場合、参照として保持
                return ListTypeSpec(
                    name=type_name,
                    items=_get_type_name(item_type),  # 参照文字列として保持
                    description=description
                )
            else:
                # 基本型の場合、TypeSpecとして展開
                items_spec = type_to_spec(item_type)
                return ListTypeSpec(name=type_name, items=items_spec, description=description)
        else:
            # 型パラメータなし
            return ListTypeSpec(name=type_name, items=TypeSpec(name='any', type='any'), description=description)

    elif origin is dict:
        if args and len(args) >= 2:
            key_type, value_type = args[0], args[1]

            # Dict[str, T] のような場合、propertiesとして扱う
            if key_type == str:
                properties: Dict[str, TypeSpecOrRef] = {}

                # 値型がカスタム型の場合、参照として保持
                if get_origin(value_type) is None and value_type not in {str, int, float, bool}:
                    # 各プロパティの型名をキーとして参照を保持（実際のプロパティ解決は別途）
                    properties[_get_type_name(value_type)] = _get_type_name(value_type)
                else:
                    # 基本型の場合、TypeSpecとして展開
                    value_spec = type_to_spec(value_type)
                    properties[_get_type_name(value_type)] = value_spec

                return DictTypeSpec(
                    name=type_name,
                    properties=properties,
                    description=description
                )
            else:
                # キーがstr以外の場合、簡易的にanyとして扱う
                return DictTypeSpec(name=type_name, properties={}, description=description)
        else:
            return DictTypeSpec(name=type_name, properties={}, description=description)

    elif origin is TypingUnion:
        # Union型（Union[int, str] など）
        if args:
            variants: List[TypeSpecOrRef] = []

            for arg in args:
                if get_origin(arg) is None and arg not in {str, int, float, bool}:
                    # カスタム型の場合、参照として保持
                    variants.append(_get_type_name(arg))
                else:
                    # 基本型の場合、TypeSpecとして展開
                    variant_spec = type_to_spec(arg)
                    variants.append(variant_spec)

            return UnionTypeSpec(name=type_name, variants=variants, description=description)
        else:
            return UnionTypeSpec(name=type_name, variants=[], description=description)

    else:
        # 未サポート型
        return TypeSpec(name=type_name, type='unknown', description=description)

def type_to_yaml(typ: type[Any], output_file: str = None, as_root: bool = True) -> str | Dict[str, dict]:
    """型をYAML文字列に変換、またはファイル出力 (v1.1対応)"""
    spec = type_to_spec(typ)

    # v1.1構造: nameフィールドを除外して出力
    spec_data = spec.model_dump(exclude={'name'})

    if as_root:
        # 単一型: 型名をキーとして出力
        yaml_data = {typ.__name__: spec_data}
        yaml_str = yaml.dump(yaml_data, default_flow_style=False, allow_unicode=True, indent=2)
    else:
        # 従来形式 (互換性用)
        yaml_str = yaml.dump(spec.model_dump(), default_flow_style=False, allow_unicode=True, indent=2)
        yaml_data = yaml_str  # 文字列

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(yaml_str)

    return yaml_str if as_root else yaml_data

def types_to_yaml(types: Dict[str, type[Any]], output_file: str = None) -> str:
    """複数型をYAML文字列に変換 (v1.1対応)"""
    specs = {}
    for name, typ in types.items():
        spec = type_to_spec(typ)
        # nameフィールドを除外
        spec_data = spec.model_dump(exclude={'name'})
        specs[name] = spec_data

    yaml_data = {'types': specs}
    yaml_str = yaml.dump(yaml_data, default_flow_style=False, allow_unicode=True, indent=2)

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(yaml_str)

    return yaml_str

# 例
if __name__ == "__main__":
    from typing import List, Dict, Union
    import datetime

    # テスト型
    UserId = str  # NewTypeではないが簡易
    Users = List[Dict[str, str]]
    Result = Union[int, str]

    print("v1.1形式出力:")
    print(type_to_yaml(Users, as_root=True))
    print("\n従来形式出力:")
    print(type_to_yaml(Result, as_root=False))
