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
                return self._resolve_nested_refs(self.type_map[ref])
            finally:
                self.resolving.remove(ref)
        else:
            return ref

    def _resolve_nested_refs(self, spec: TypeSpec) -> TypeSpec:
        """ネストされた参照を解決"""
        if isinstance(spec, ListTypeSpec):
            resolved_items = self.resolve_ref(spec.items)
            return ListTypeSpec(
                name=spec.name,
                type=spec.type,
                description=spec.description,
                required=spec.required,
                items=resolved_items
            )
        elif isinstance(spec, DictTypeSpec):
            resolved_props = {
                key: self.resolve_ref(prop)
                for key, prop in spec.properties.items()
            }
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
