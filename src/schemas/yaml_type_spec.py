from typing import Any, Dict, List, Union, Literal, Optional, ForwardRef
from pydantic import BaseModel, Field, validator, field_validator

# 参照解決のための型エイリアス
TypeSpecOrRef = Union["TypeSpec", str]

class TypeSpec(BaseModel):
    """YAML形式の型仕様の基底モデル"""
    name: Optional[str] = Field(None, description="型の名前 (v1.1ではオプション。参照時は不要)")
    type: str = Field(..., description="基本型 (str, int, float, bool, list, dict, union)")
    description: Optional[str] = Field(None, description="型の説明")
    required: bool = Field(True, description="必須かどうか")

class ListTypeSpec(TypeSpec):
    """リスト型の仕様"""
    type: Literal["list"] = "list"
    items: TypeSpecOrRef = Field(..., description="リストの要素型 (参照文字列またはTypeSpec)")

class DictTypeSpec(TypeSpec):
    """辞書型の仕様"""
    type: Literal["dict"] = "dict"
    properties: Dict[str, TypeSpecOrRef] = Field(default_factory=dict, description="辞書のプロパティ (参照文字列またはTypeSpec)")
    additional_properties: bool = Field(False, description="追加プロパティ許可")

class UnionTypeSpec(TypeSpec):
    """Union型の仕様"""
    type: Literal["union"] = "union"
    variants: List[TypeSpecOrRef] = Field(..., description="Unionのバリアント (参照文字列またはTypeSpec)")

# v1.1用: ルートモデル (複数型をキー=型名で管理)
class TypeRoot(BaseModel):
    """YAML型仕様のルートモデル (v1.1構造)"""
    types: Dict[str, TypeSpec] = Field(default_factory=dict, description="型仕様のルート辞書。キー=型名、値=TypeSpec")

    @field_validator('types', mode='before')
    @classmethod
    def validate_types(cls, v):
        """typesフィールドのバリデーション（生のdictも受け入れる）"""
        if isinstance(v, dict):
            result = {}
            for key, value in v.items():
                if isinstance(value, dict):
                    # dictの場合、TypeSpecに変換
                    result[key] = _create_spec_from_data(value)
                elif isinstance(value, TypeSpec):
                    result[key] = value
                else:
                    # 参照文字列の場合
                    result[key] = value
            return result
        return v

def _create_spec_from_data(data: dict, root_key: str = None) -> TypeSpec:
    """dictからTypeSpecサブクラスを作成 (内部関数)"""
    type_key = data.get('type')
    if type_key == 'list':
        return ListTypeSpec(**data)
    elif type_key == 'dict':
        return DictTypeSpec(**data)
    elif type_key == 'union':
        return UnionTypeSpec(**data)
    else:
        # 基本型: nameをroot_keyから補完（v1.1対応）
        if root_key:
            data['name'] = root_key
        return TypeSpec(**data)

# 参照解決のためのコンテキスト
class TypeContext:
    """型参照解決のためのコンテキスト"""
    def __init__(self):
        self.type_map: Dict[str, TypeSpec] = {}
        self.resolving: set[str] = set()  # 循環参照検出用

    def add_type(self, name: str, spec: TypeSpec) -> None:
        """型をコンテキストに追加"""
        self.type_map[name] = spec

    def resolve_ref(self, ref: str | TypeSpec) -> TypeSpec:
        """参照を解決してTypeSpecを返す"""
        if isinstance(ref, str):
            if ref in self.resolving:
                # 循環参照検出
                raise ValueError(f"Circular reference detected: {ref}")
            if ref not in self.type_map:
                raise ValueError(f"Undefined type reference: {ref}")

            self.resolving.add(ref)
            try:
                resolved = self.type_map[ref]
                return self._resolve_nested_refs(resolved)
            finally:
                self.resolving.remove(ref)
        else:
            return ref

    def _resolve_nested_refs(self, spec: TypeSpec) -> TypeSpec:
        """ネストされた参照を解決"""
        if isinstance(spec, ListTypeSpec):
            resolved_items = self.resolve_ref(spec.items)
            # itemsが参照文字列からTypeSpecに解決された場合、適切な型に変換
            if isinstance(resolved_items, str):
                # まだ参照文字列の場合は、そのまま保持
                final_items = resolved_items
            else:
                # TypeSpecに解決された場合は、そのまま使用
                final_items = resolved_items
            return ListTypeSpec(
                name=spec.name,
                type=spec.type,
                description=spec.description,
                required=spec.required,
                items=final_items
            )
        elif isinstance(spec, DictTypeSpec):
            resolved_props = {}
            for key, prop in spec.properties.items():
                # 参照文字列またはTypeSpecのどちらでも解決
                resolved_props[key] = self.resolve_ref(prop)
            return DictTypeSpec(
                name=spec.name,
                type=spec.type,
                description=spec.description,
                required=spec.required,
                properties=resolved_props,
                additional_properties=spec.additional_properties
            )
        elif isinstance(spec, UnionTypeSpec):
            resolved_variants = [
                self.resolve_ref(variant)
                for variant in spec.variants
            ]
            return UnionTypeSpec(
                name=spec.name,
                type=spec.type,
                description=spec.description,
                required=spec.required,
                variants=resolved_variants
            )
        else:
            return spec

# 例の使用: TypeSpecモデルをYAMLにシリアライズ可能
# v1.1例:
# types:
#   User:
#     type: dict
#     description: ユーザー情報
#     properties:
#       id:
#         type: int
#         description: ID
