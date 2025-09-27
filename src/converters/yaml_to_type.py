import yaml
from typing import Any, Dict, Type, Union
from pydantic import ValidationError

from src.schemas.yaml_type_spec import (
    TypeSpec, ListTypeSpec, DictTypeSpec, UnionTypeSpec, TypeRoot, TypeContext, TypeSpecOrRef, _create_spec_from_data
)

def yaml_to_spec(yaml_str: str, root_key: str = None) -> TypeSpec | TypeRoot:
    """YAML文字列からTypeSpecまたはTypeRootを生成 (v1.1対応、参照解決付き)"""
    data = yaml.safe_load(yaml_str)

    # v1.1: ルートがdictの場合、トップレベルキーを型名として扱う
    if isinstance(data, dict) and not root_key:
        if 'types' in data:
            # 複数型: TypeRoot（参照解決付き）
            type_root = TypeRoot(**data)
            # 参照解決を実行
            resolved_types = _resolve_all_refs(type_root.types)
            return TypeRoot(types=resolved_types)
        else:
            # 単一型: 最初のキーを型名としてTypeSpec作成
            if len(data) == 1:
                type_name, spec_data = next(iter(data.items()))
                spec_data['name'] = type_name  # nameを補完（オプション）
                spec = _create_spec_from_data(spec_data)
                # 単一型の場合も参照解決を実行（循環参照チェックのため）
                context = TypeContext()
                context.add_type(type_name, spec)
                return context.resolve_ref(spec)
            else:
                # 複数単一型: TypeRoot(types=data) に変換
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

def _resolve_all_refs(types: Dict[str, TypeSpec]) -> Dict[str, TypeSpec]:
    """すべての参照を解決"""
    context = TypeContext()

    # まずすべての型をコンテキストに追加（元のspecを保持）
    for name, spec in types.items():
        context.add_type(name, spec)

    # 次にすべての参照を解決（_resolve_nested_refsを使って構造を維持）
    resolved_types = {}
    for name, spec in types.items():
        resolved_types[name] = context._resolve_nested_refs(spec)

    return resolved_types


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
            if spec.type == 'str' and not isinstance(data, str):
                return False
            elif spec.type == 'int' and not isinstance(data, int):
                return False
            # ... 他の基本型
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
