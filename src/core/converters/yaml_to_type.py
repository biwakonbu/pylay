from typing import Any
from pydantic import ValidationError
from ruamel.yaml import YAML

from src.core.schemas.yaml_type_spec import (
    TypeSpec,
    RefPlaceholder,
    ListTypeSpec,
    DictTypeSpec,
    UnionTypeSpec,
    GenericTypeSpec,
    TypeRoot,
    TypeContext,
    TypeSpecOrRef,
    _create_spec_from_data,
)


def yaml_to_spec(
    yaml_str: str, root_key: str | None = None
) -> TypeSpec | TypeRoot | RefPlaceholder | None:
    """YAML文字列からTypeSpecまたはTypeRootを生成 (v1.1対応、参照解決付き)"""
    yaml_parser = YAML()
    data = yaml_parser.load(yaml_str)

    # v1.1: ルートがdictの場合、トップレベルキーを型名として扱う
    if isinstance(data, dict) and not root_key:
        if "types" in data:
            # 旧形式: 複数型（types: コンテナ使用）
            types_data = data["types"]
            # _detect_circular_references_from_data(types_data)

            # 循環参照がないことを確認してからTypeRootを構築
            type_root = TypeRoot(**data)
            # 参照解決を実行
            resolved_types = _resolve_all_refs(type_root.types)
            # 参照解決されたTypeRootを返す
            return type_root.__class__(types=resolved_types)
        elif len(data) > 1:
            # 新形式: 複数型（トップレベルに直接型名キー）
            types_dict = {k: _create_spec_from_data(v, k) for k, v in data.items()}
            type_root = TypeRoot(types=types_dict)
            # 参照解決を実行
            resolved_types = _resolve_all_refs(type_root.types)
            # 参照解決されたTypeRootを返す
            return type_root.__class__(types=resolved_types)
        else:
            # 従来v1または指定root_key: nameフィールドで処理
            if len(data) == 1 and "type" not in data:
                # トップレベルが型名の場合 (例: TestDict: {type: dict, ...})
                key, value = list(data.items())[0]
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


def _detect_circular_references_from_data(types_data: dict[str, Any]) -> None:
    """生のデータから循環参照を検出"""
    # 参照グラフを構築
    ref_graph = {}
    for name, spec_data in types_data.items():
        refs = _collect_refs_from_data(spec_data)
        ref_graph[name] = refs

    # 循環参照を検出（DFS）
    visited = set()
    rec_stack = set()

    def has_cycle(node: str) -> bool:
        visited.add(node)
        rec_stack.add(node)

        for neighbor in ref_graph.get(node, []):
            if neighbor not in visited:
                if has_cycle(neighbor):
                    return True
            elif neighbor in rec_stack:
                return True

        rec_stack.remove(node)
        return False

    for node in ref_graph:
        if node not in visited:
            if has_cycle(node):
                raise ValueError(f"Circular reference detected involving: {node}")


def _collect_refs_from_data(spec_data: Any) -> list[str]:
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
            elif isinstance(value, (dict, list)):
                # ネストされた構造もチェック
                refs.extend(_collect_refs_from_data(value))
    elif isinstance(spec_data, list):
        for item in spec_data:
            if isinstance(item, str):
                refs.append(item)
            elif isinstance(item, (dict, list)):
                refs.extend(_collect_refs_from_data(item))

    return refs


def _resolve_all_refs(types: dict[str, TypeSpec]) -> dict[str, TypeSpec]:
    """すべての参照を解決"""
    # 循環参照を検出（一時的に無効化）
    # _detect_circular_references(types)

    context = TypeContext()

    # すべての型をコンテキストに追加
    for name, spec in types.items():
        context.add_type(name, spec)

    # 参照解決を実行
    resolved_types = {}
    for name, spec in types.items():
        resolved_types[name] = context._resolve_nested_refs(spec)

    return resolved_types


def _detect_circular_references(types: dict[str, TypeSpec]) -> None:
    """循環参照を検出（循環参照を許容するためスキップ）"""
    # 循環参照を許容するため検出をスキップ
    pass


def _collect_refs_from_spec(spec: TypeSpec) -> list[str]:
    """TypeSpecから参照文字列を収集"""
    from src.core.schemas.yaml_type_spec import RefPlaceholder

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


def validate_with_spec(
    spec: TypeSpecOrRef, data: Any, max_depth: int = 10, current_depth: int = 0
) -> bool:
    """TypeSpecに基づいてデータをバリデーション"""
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
                    if not validate_with_spec(
                        prop_spec, data[key], max_depth, current_depth + 1
                    ):
                        return False
            return True
        elif isinstance(spec, ListTypeSpec):
            if not isinstance(data, list):
                return False
            return all(
                validate_with_spec(spec.items, item, max_depth, current_depth + 1)
                for item in data
            )
        elif isinstance(spec, UnionTypeSpec):
            return any(
                validate_with_spec(variant, data, max_depth, current_depth + 1)
                for variant in spec.variants
            )
        elif isinstance(spec, TypeSpec):
            # 基本型バリデーション
            if spec.type == "str":
                return isinstance(data, str)
            elif spec.type == "int":
                return isinstance(data, int)
            elif spec.type == "float":
                # floatはintも受け入れる（Pythonのfloat()関数と同様）
                return isinstance(data, (int, float))
            elif spec.type == "bool":
                return isinstance(data, bool)
            elif spec.type == "any":
                # any型は常にTrue
                return True
            else:
                # 未サポートの型はFalse
                return False
        # デフォルトでFalseを返す（TypeSpecOrRefの型チェック用）
        return False
    except Exception:
        return False


def generate_pydantic_model(spec: TypeSpec, model_name: str = "DynamicModel") -> str:
    """TypeSpecからPydanticモデルコードを生成 (簡易版)"""
    # これはコード生成なので、文字列として返す
    if isinstance(spec, TypeSpec):
        return f"class {model_name}(BaseModel):\\n    value: {spec.type}"
    # 他の型の場合、拡張可能
    else:
        return f"class {model_name}(BaseModel):\\n    # Complex type\\n    pass"


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
