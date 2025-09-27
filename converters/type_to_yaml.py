import yaml
import inspect
from typing import Any, get_origin, get_args, Optional, Union
from types import UnionType

from schemas.yaml_type_spec import TypeSpec, ListTypeSpec, DictTypeSpec, UnionTypeSpec, TypeSpecOrRef
from src.schemas.graph_types import TypeDependencyGraph



def _get_basic_type_str(typ: type[Any]) -> str:
    """基本型の型名を取得"""
    basic_type_mapping = {
        str: 'str',
        int: 'int',
        float: 'float',
        bool: 'bool',
    }
    return basic_type_mapping.get(typ, 'str')

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

def _get_class_properties_with_docstrings(cls: type[Any]) -> dict[str, Any]:
    """クラスのプロパティとフィールドdocstringを取得"""
    properties = {}

    # クラスアノテーションからフィールドを取得
    annotations = getattr(cls, '__annotations__', {})

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
                type='unknown',
                description=_get_field_docstring(cls, field_name)
            )

    return properties

def _handle_basic_type(typ: type[Any], type_name: str, description: str | None) -> TypeSpec:
    """基本型をTypeSpecに変換"""
    if typ in {str, int, float, bool}:
        type_str = _get_basic_type_str(typ)
        return TypeSpec(name=type_name, type=type_str, description=description)
    else:
        # カスタムクラスはdict型として扱い、フィールドのdocstringを取得
        properties = _get_class_properties_with_docstrings(typ)
        return DictTypeSpec(
            name=type_name,
            type='dict',
            description=description,
            properties=properties
        )


def _handle_list_type(typ: type[Any], type_name: str, description: str | None, args: tuple[type, ...]) -> ListTypeSpec:
    """List型をListTypeSpecに変換"""
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


def _handle_dict_type(typ: type[Any], type_name: str, description: str | None, args: tuple[type, ...]) -> DictTypeSpec:
    """Dict型をDictTypeSpecに変換"""
    if args and len(args) >= 2:
        key_type, value_type = args[0], args[1]

        # Dict[str, T] のような場合、propertiesとして扱う
        if key_type is str:
            properties: dict[str, TypeSpecOrRef] = {}

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


def _handle_union_type(typ: type[Any], type_name: str, description: str | None, args: tuple[type, ...]) -> UnionTypeSpec:
    """Union型をUnionTypeSpecに変換"""
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

        return UnionTypeSpec(name=type_name, variants=variants, description=description)
    else:
        return UnionTypeSpec(name=type_name, variants=[], description=description)


def type_to_spec(typ: type[Any]) -> TypeSpec:
    """Python型をTypeSpecに変換（v1.1対応）"""
    origin = get_origin(typ)
    args = get_args(typ)

    # docstringを取得
    description = _get_docstring(typ)

    # 型名を取得
    type_name = _get_type_name(typ)

    if origin is None:
        return _handle_basic_type(typ, type_name, description)
    elif origin is list:
        return _handle_list_type(typ, type_name, description, args)
    elif origin is dict:
        return _handle_dict_type(typ, type_name, description, args)
    elif origin is Union or origin is UnionType:
        return _handle_union_type(typ, type_name, description, args)
    else:
        # 未サポート型
        return TypeSpec(name=type_name, type='unknown', description=description)

def type_to_yaml(typ: type[Any], output_file: Optional[str] = None, as_root: bool = True,
                 dependencies: Optional[TypeDependencyGraph] = None) -> str | dict[str, dict]:
    """型をYAML文字列に変換、またはファイル出力 (v1.1対応)"""
    spec = type_to_spec(typ)

    # v1.1構造: nameフィールドを除外して出力
    spec_data = spec.model_dump(exclude={'name'})

    # 依存情報を統合（オプション）
    if dependencies and as_root:
        dependency_data = _build_dependency_yaml(dependencies)
        spec_data = {**spec_data, 'dependencies': dependency_data}

    if as_root:
        # 単一型: 型名をキーとして出力
        yaml_data = {_get_type_name(typ): spec_data}
        yaml_str = yaml.dump(yaml_data, default_flow_style=False, allow_unicode=True, indent=2)
    else:
        # 従来形式 (互換性用)
        yaml_str = yaml.dump(spec.model_dump(), default_flow_style=False, allow_unicode=True, indent=2)
        # yaml_data は文字列として扱う

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(yaml_str)

    return yaml_str if as_root else yaml_data

def types_to_yaml(types: dict[str, type[Any]], output_file: Optional[str] = None) -> str:
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


def _build_dependency_yaml(graph: TypeDependencyGraph) -> dict[str, list[str]]:
    """TypeDependencyGraphからYAML依存データを構築"""
    dependencies: dict[str, list[str]] = {}

    for edge in graph.edges:
        if edge.source not in dependencies:
            dependencies[edge.source] = []
        dependencies[edge.source].append(f"{edge.target} ({edge.relation_type})")

    return dependencies


# 例
if __name__ == "__main__":
    # テスト用（実際の使用では削除してください）

    # テスト型
    UserId = str  # NewTypeではないが簡易
    Users = list[dict[str, str]]
    Result = int | str

    print("v1.1形式出力:")
    print(type_to_yaml(dict, as_root=True))
    print("\n従来形式出力:")
    print(type_to_yaml(int, as_root=False))
