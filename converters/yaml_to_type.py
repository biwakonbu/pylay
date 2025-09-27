import yaml
from typing import Any, Dict

from schemas.yaml_type_spec import (
    TypeSpec, ListTypeSpec, DictTypeSpec, UnionTypeSpec, TypeRoot, TypeContext, _create_spec_from_data
)

def yaml_to_spec(yaml_str: str, root_key: str | None = None) -> TypeSpec | TypeRoot:  # type: ignore[import-untyped]
    """YAML文字列からTypeSpecまたはTypeRootを生成 (v1.1対応、参照解決付き)"""
    data = yaml.safe_load(yaml_str)

    # v1.1: ルートがdictの場合、トップレベルキーを型名として扱う
    if isinstance(data, dict) and not root_key:
        if 'types' in data:
            # 複数型: まず循環参照を検出してからTypeRootを構築
            types_data = data['types']
            _detect_circular_references_from_data(types_data)

            # 循環参照がないことを確認してからTypeRootを構築
            type_root = TypeRoot(**data)
            # 参照解決を実行
            resolved_types = _resolve_all_refs(type_root.types)
            # 既存のTypeRootインスタンスのtypes属性を更新
            type_root.types = resolved_types
            return type_root
        else:
            # 単一型: 最初のキーを型名としてTypeSpec作成
            if len(data) == 1:
                type_name, spec_data = next(iter(data.items()))
                if not isinstance(spec_data, dict):
                    raise ValueError(f"Invalid YAML structure for type '{type_name}': expected dict, got {type(spec_data).__name__}")
                spec_data['name'] = type_name  # nameを補完（オプション）
                spec = _create_spec_from_data(spec_data)
                # 単一型の場合も参照解決を実行（循環参照チェックのため）
                context = TypeContext()
                context.add_type(type_name, spec)
                return context.resolve_ref(spec)
            else:
                # 複数単一型: まず循環参照を検出してからTypeRootを構築
                _detect_circular_references_from_data(data)
                type_root = TypeRoot(types=data)
                resolved_types = _resolve_all_refs(type_root.types)
                return TypeRoot(types=resolved_types)
    elif isinstance(data, dict):
        # 従来v1または指定root_key: nameフィールドで処理
        spec = _create_spec_from_data(data, root_key)
        # 参照解決（循環参照チェックのため）
        context = TypeContext()
        if spec.name:
            context.add_type(spec.name, spec)
        return context.resolve_ref(spec)

    raise ValueError("Invalid YAML structure for TypeSpec or TypeRoot")

def _detect_circular_references_from_data(types_data: Dict[str, Any]) -> None:
    """生のデータから循環参照を検出"""
    # 参照グラフを構築
    ref_graph = {}
    for name, spec_data in types_data.items():
        refs = _collect_refs_from_data(spec_data)
        ref_graph[name] = refs

    # 循環参照を検出（DFS）
    visited = set()
    rec_stack = set()

    def has_cycle(node):
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

def _collect_refs_from_data(spec_data: Any):
    """生のデータから参照文字列を収集"""
    refs = []

    if isinstance(spec_data, dict):
        for key, value in spec_data.items():
            if key == 'items' and isinstance(value, str):
                refs.append(value)
            elif key == 'properties' and isinstance(value, dict):
                for prop_value in value.values():
                    if isinstance(prop_value, str):
                        refs.append(prop_value)
                    elif isinstance(prop_value, dict):
                        # ネストされたproperties内の参照
                        refs.extend(_collect_refs_from_data(prop_value))
            elif key == 'variants' and isinstance(value, list):
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

def _resolve_all_refs(types: Dict[str, TypeSpec]) -> Dict[str, TypeSpec]:
    """すべての参照を解決"""
    # まず循環参照を検出
    _detect_circular_references(types)

    context = TypeContext()

    # すべての型をコンテキストに追加
    for name, spec in types.items():
        context.add_type(name, spec)

    # 参照解決を実行
    resolved_types = {}
    for name, spec in types.items():
        resolved_types[name] = context._resolve_nested_refs(spec)

    return resolved_types

def _detect_circular_references(types: Dict[str, TypeSpec]) -> None:
    """循環参照を検出"""
    # 参照グラフを構築
    ref_graph = {}
    for name, spec in types.items():
        refs = _collect_refs_from_spec(spec)
        ref_graph[name] = refs

    # 循環参照を検出（DFS）
    visited = set()
    rec_stack = set()

    def has_cycle(node):
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

def _collect_refs_from_spec(spec: TypeSpec):
    """TypeSpecから参照文字列を収集"""
    from schemas.yaml_type_spec import RefPlaceholder
    refs = []

    if isinstance(spec, ListTypeSpec):
        if isinstance(spec.items, RefPlaceholder):
            refs.append(spec.items.ref_name)
        elif isinstance(spec.items, str):
            refs.append(spec.items)
        elif hasattr(spec.items, '__class__'):  # TypeSpecの場合
            refs.extend(_collect_refs_from_spec(spec.items))
    elif isinstance(spec, DictTypeSpec):
        for prop in spec.properties.values():
            if isinstance(prop, RefPlaceholder):
                refs.append(prop.ref_name)
            elif isinstance(prop, str):
                refs.append(prop)
            elif hasattr(prop, '__class__'):  # TypeSpecの場合
                refs.extend(_collect_refs_from_spec(prop))
    elif isinstance(spec, UnionTypeSpec):
        for variant in spec.variants:
            if isinstance(variant, RefPlaceholder):
                refs.append(variant.ref_name)
            elif isinstance(variant, str):
                refs.append(variant)
            elif hasattr(variant, '__class__'):  # TypeSpecの場合
                refs.extend(_collect_refs_from_spec(variant))

    return refs



def validate_with_spec(spec: TypeSpec, data: Any) -> bool:
    """TypeSpecに基づいてデータをバリデーション"""
    try:
        if isinstance(spec, DictTypeSpec):
            if not isinstance(data, dict):
                return False
            for key, prop_spec in spec.properties.items():
                if key in data:
                    if not validate_with_spec(prop_spec, data[key]):
                        return False
            return True
        elif isinstance(spec, ListTypeSpec):
            if not isinstance(data, list):
                return False
            return all(validate_with_spec(spec.items, item) for item in data)
        elif isinstance(spec, UnionTypeSpec):
            return any(validate_with_spec(variant, data) for variant in spec.variants)
        elif isinstance(spec, TypeSpec):
            # 基本型バリデーション
            if spec.type == 'str':
                return isinstance(data, str)
            elif spec.type == 'int':
                return isinstance(data, int)
            elif spec.type == 'float':
                # floatはintも受け入れる（Pythonのfloat()関数と同様）
                return isinstance(data, (int, float))
            elif spec.type == 'bool':
                return isinstance(data, bool)
            elif spec.type == 'any':
                # any型は常にTrue
                return True
            else:
                # 未サポートの型はFalse
                return False
        return True
    except Exception:
        return False

def generate_pydantic_model(spec: TypeSpec, model_name: str = "DynamicModel") -> str:
    """TypeSpecからPydanticモデルコードを生成 (簡易版)"""
    # これはコード生成なので、文字列として返す
    if isinstance(spec, TypeSpec):
        return f"class {model_name}(BaseModel):\\n    value: {spec.type}"
    # 他の型の場合、拡張可能
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
    print(spec.types['User'].description)  # ユーザー情報を表す型

    # 単一型例
    single_yaml = """
    User:
      type: dict
      properties:
        id: {type: int}
    """
    single_spec = yaml_to_spec(single_yaml)
    print(type(single_spec))  # TypeSpec
    print(single_spec.name)  # User (補完)
