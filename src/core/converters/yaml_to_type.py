from typing import Any

from ruamel.yaml import YAML

from src.core.schemas.types import TypeRefList
from src.core.schemas.yaml_spec import (
    DictTypeSpec,
    ListTypeSpec,
    RefPlaceholder,
    TypeContext,
    TypeRoot,
    TypeSpec,
    TypeSpecOrRef,
    UnionTypeSpec,
    _create_spec_from_data,
)


def yaml_to_spec(yaml_str: str, root_key: str | None = None) -> TypeSpec | TypeRoot | RefPlaceholder | str | None:
    """YAML文字列からTypeSpecまたはTypeRootを生成 (v1.1対応、参照解決付き)"""
    yaml_parser = YAML()
    data = yaml_parser.load(yaml_str)

    # v1.1: ルートがdictの場合、トップレベルキーを型名として扱う
    if isinstance(data, dict) and not root_key:
        if "types" in data:
            # 旧形式: 複数型（types: コンテナ使用）
            # 循環参照がないことを確認してからTypeRootを構築
            type_root = TypeRoot(**data)
            # 参照解決を実行
            resolved_types = _resolve_all_refs(type_root.types)
            # 参照解決されたTypeRootを返す
            return type_root.__class__(types=resolved_types)
        elif len(data) > 1:
            # 新形式: 複数型（トップレベルに直接型名キー）
            # _metadata, _imports キーは特別扱い
            # IMPORTANT: _で始まる型名（_BaseType等）を除外しないよう、特定キーのみ除外
            reserved_keys = {"_metadata", "_imports"}
            types_dict = {k: _create_spec_from_data(v, k) for k, v in data.items() if k not in reserved_keys}
            # _importsと_metadataを取得
            imports_dict = data.get("_imports")
            metadata_dict = data.get("_metadata")

            type_root = TypeRoot(types=types_dict, _imports=imports_dict, _metadata=metadata_dict)
            # 参照解決を実行
            resolved_types = _resolve_all_refs(type_root.types)
            # 参照解決されたTypeRootを返す（_imports, _metadataも保持）
            return type_root.__class__(
                types=resolved_types,
                _imports=type_root.imports_,
                _metadata=type_root.metadata_,
            )
        else:
            # 従来v1または指定root_key: nameフィールドで処理
            if len(data) == 1 and "type" not in data:
                # トップレベルが型名の場合 (例: TestDict: {type: dict, ...})
                key, value = next(iter(data.items()))
                spec = _create_spec_from_data(value, key)
            else:
                spec = _create_spec_from_data(data, root_key)
            # 参照解決（循環参照チェックのため）
            context = TypeContext()
            if spec.name:
                context.add_type(spec.name, spec)
            return context.resolve_ref(spec)
    elif isinstance(data, list):
        # リストの場合は最初の要素をTypeSpecとして処理
        if not data:
            raise ValueError("Empty list cannot be converted to TypeSpec")
        if not isinstance(data[0], dict):
            raise ValueError("List elements must be dict for TypeSpec conversion")
        spec = _create_spec_from_data(data[0], root_key)
        # 参照解決（循環参照チェックのため）
        context = TypeContext()
        if spec.name:
            context.add_type(spec.name, spec)
        return context.resolve_ref(spec)
    else:
        raise ValueError("Invalid YAML structure for TypeSpec or TypeRoot")


def _collect_refs_from_data(spec_data: Any) -> TypeRefList:
    """生のデータから参照文字列を収集"""
    refs = []

    if isinstance(spec_data, dict):
        for key, value in spec_data.items():
            if key == "items" and isinstance(value, str):
                refs.append(value)
            elif key == "properties" and isinstance(value, dict):
                for prop_value in value.values():
                    if isinstance(prop_value, str):
                        refs.append(prop_value)
                    elif isinstance(prop_value, dict):
                        # ネストされたproperties内の参照
                        refs.extend(_collect_refs_from_data(prop_value))
            elif key == "variants" and isinstance(value, list):
                for variant in value:
                    if isinstance(variant, str):
                        refs.append(variant)
                    elif isinstance(variant, dict):
                        # ネストされたvariants内の参照
                        refs.extend(_collect_refs_from_data(variant))
            elif isinstance(value, dict | list):
                # ネストされた構造もチェック
                refs.extend(_collect_refs_from_data(value))
    elif isinstance(spec_data, list):
        for item in spec_data:
            if isinstance(item, str):
                refs.append(item)
            elif isinstance(item, dict | list):
                refs.extend(_collect_refs_from_data(item))

    return refs


def _resolve_all_refs(types: dict[str, TypeSpec]) -> dict[str, TypeSpec]:
    """すべての参照を解決"""
    context = TypeContext()

    # すべての型をコンテキストに追加
    for name, spec in types.items():
        context.add_type(name, spec)

    # 参照解決を実行
    resolved_types = {}
    for name, spec in types.items():
        resolved_types[name] = context._resolve_nested_refs(spec)

    return resolved_types


def _collect_refs_from_spec(spec: TypeSpec) -> TypeRefList:
    """TypeSpecから参照文字列を収集

    TypeSpecオブジェクトから参照文字列を収集します。
    """
    from src.core.schemas.yaml_spec import RefPlaceholder

    refs = []

    if isinstance(spec, ListTypeSpec):
        if isinstance(spec.items, RefPlaceholder):
            refs.append(spec.items.ref_name)
        elif isinstance(spec.items, str):
            refs.append(spec.items)
        elif hasattr(spec.items, "__class__"):  # TypeSpecの場合
            refs.extend(_collect_refs_from_spec(spec.items))
    elif isinstance(spec, DictTypeSpec):
        for prop in spec.properties.values():
            if isinstance(prop, RefPlaceholder):
                refs.append(prop.ref_name)
            elif isinstance(prop, str):
                refs.append(prop)
            elif hasattr(prop, "__class__"):  # TypeSpecの場合
                refs.extend(_collect_refs_from_spec(prop))
    elif isinstance(spec, UnionTypeSpec):
        for variant in spec.variants:
            if isinstance(variant, RefPlaceholder):
                refs.append(variant.ref_name)
            elif isinstance(variant, str):
                refs.append(variant)
            elif hasattr(variant, "__class__"):  # TypeSpecの場合
                refs.extend(_collect_refs_from_spec(variant))

    return refs


def validate_with_spec(spec: TypeSpecOrRef, data: Any, max_depth: int = 10, current_depth: int = 0) -> bool:
    """TypeSpecに基づいてデータをバリデーション

    TypeSpec定義に基づいて入力データをバリデーションします。
    """
    if current_depth > max_depth:
        return False  # 深さ制限超過
    try:
        # 参照文字列の場合、常にTrue（参照解決は別途）
        if isinstance(spec, str):
            return True
        if isinstance(spec, DictTypeSpec):
            if not isinstance(data, dict):
                return False
            for key, prop_spec in spec.properties.items():
                if key in data:
                    if not validate_with_spec(prop_spec, data[key], max_depth, current_depth + 1):
                        return False
            return True
        elif isinstance(spec, ListTypeSpec):
            if not isinstance(data, list):
                return False
            return all(validate_with_spec(spec.items, item, max_depth, current_depth + 1) for item in data)
        elif isinstance(spec, UnionTypeSpec):
            return any(validate_with_spec(variant, data, max_depth, current_depth + 1) for variant in spec.variants)
        elif isinstance(spec, TypeSpec):
            # 基本型バリデーション
            if spec.type == "str":
                return isinstance(data, str)
            elif spec.type == "int":
                return isinstance(data, int)
            elif spec.type == "float":
                # floatはintも受け入れる（Pythonのfloat()関数と同様）
                return isinstance(data, int | float)
            elif spec.type == "bool":
                return isinstance(data, bool)
            elif spec.type == "any":
                # any型は常にTrue
                return True
            # 未サポートの型はFalse
            return False
        # デフォルトでFalseを返す（TypeSpecOrRefの型チェック用）
        return False
    except Exception:
        return False


def generate_pydantic_model(spec: TypeSpec, model_name: str = "DynamicModel") -> str:
    """TypeSpecからPydanticモデルコードを生成 (簡易版)

    TypeSpec定義からPydanticモデルコードを生成します（簡易版）。
    """
    # これはコード生成なので、文字列として返す
    if isinstance(spec, TypeSpec):
        return f"class {model_name}(BaseModel):\\n    value: {spec.type}"
    # 他の型の場合、拡張可能
    else:
        return f"class {model_name}(BaseModel):\\n    # 複雑な型\\n    pass"


# 例
if __name__ == "__main__":
    yaml_example = """
    types:
      User:
        type: dict
        description: ユーザー情報を表す型
        properties:
          id:
            type: int
            description: ユーザーID
          name:
            type: str
            description: ユーザー名
    """
    spec = yaml_to_spec(yaml_example)
    print(type(spec))  # TypeRoot
    if isinstance(spec, TypeRoot):
        print(spec.types["User"].description)  # ユーザー情報を表す型

    # 単一型例
    single_yaml = """
    User:
      type: dict
      properties:
        id: {type: int}
    """
    single_spec = yaml_to_spec(single_yaml)
    print(type(single_spec))  # TypeSpec
    if isinstance(single_spec, TypeSpec):
        print(single_spec.name)  # User (補完)
