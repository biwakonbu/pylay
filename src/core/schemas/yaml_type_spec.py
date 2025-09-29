from typing import Any, Literal, Optional, Annotated, ForwardRef, NewType
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class RefPlaceholder(BaseModel):
    """参照文字列を保持するためのプレースホルダー（Pydantic v2対応強化）"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    type: Literal["ref"] = "ref"
    ref_name: str

    def __str__(self) -> str:
        return self.ref_name

    def __repr__(self) -> str:
        return f"RefPlaceholder({self.ref_name})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, RefPlaceholder):
            return self.ref_name == other.ref_name
        return self.ref_name == other

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> Any:
        """Pydanticのスキーマ生成"""
        from pydantic_core import core_schema

        return core_schema.str_schema()


class TypeSpec(BaseModel):
    """YAML形式の型仕様の基底モデル（v1.1対応、循環参照耐性強化）"""

    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )  # 遅延型解決はmodel_rebuildで対応

    name: Optional[str] = Field(
        None, description="型の名前 (v1.1ではオプション。参照時は不要)"
    )
    type: str = Field(
        ..., description="基本型 (str, int, float, bool, list, dict, union)"
    )
    description: Optional[str] = Field(None, description="型の説明")
    required: bool = Field(True, description="必須かどうか")


# 参照解決のための型エイリアス（前方参照用）
type TypeSpecOrRef = RefPlaceholder | str | TypeSpec


class ListTypeSpec(TypeSpec):
    """リスト型の仕様"""

    type: Literal["list"] = "list"
    items: Any = Field(..., description="リストの要素型 (参照文字列またはTypeSpec)")

    @field_validator("items", mode="before")
    @classmethod
    def validate_items(cls, v: Any) -> Any:
        """itemsの前処理バリデーション（dictをTypeSpecに変換）"""
        if isinstance(v, dict):
            return _create_spec_from_data(v)
        return v


class DictTypeSpec(TypeSpec):
    """辞書型の仕様（プロパティの型をTypeSpecOrRefに統一）"""

    type: Literal["dict"] = "dict"
    properties: dict[str, Any] = Field(
        default_factory=dict, description="辞書のプロパティ (参照文字列またはTypeSpec)"
    )
    additional_properties: bool = Field(False, description="追加プロパティ許可")

    @field_validator("properties", mode="before")
    @classmethod
    def validate_properties_before(cls, v: Any) -> Any:
        """propertiesフィールドの前処理バリデーション（参照文字列を保持）"""
        if isinstance(v, dict):
            result: dict[str, Any] = {}
            for key, value in v.items():
                if isinstance(value, str):
                    # 参照文字列の場合はそのまま保持
                    result[key] = value
                elif isinstance(value, dict):
                    # dictの場合、参照文字列を含む可能性があるのでTypeSpecに変換
                    result[key] = _create_spec_from_data(value)
                else:
                    result[key] = value
            return result
        return v


class UnionTypeSpec(TypeSpec):
    """Union型の仕様（参照型をTypeSpecOrRefに統一）"""

    type: Literal["union"] = "union"
    variants: list[Any] = Field(
        ..., description="Unionのバリアント (参照文字列またはTypeSpec)"
    )

    @field_validator("variants", mode="before")
    @classmethod
    def validate_variants(cls, v: Any) -> Any:
        """variantsの前処理バリデーション（dictをTypeSpecに変換）"""
        if isinstance(v, list):
            result = []
            for item in v:
                if isinstance(item, dict):
                    result.append(_create_spec_from_data(item))
                else:
                    result.append(item)
            return result
        return v


class GenericTypeSpec(TypeSpec):
    """Generic型の仕様（例: Generic[T]）（参照型をTypeSpecOrRefに統一）"""

    type: Literal["generic"] = "generic"
    params: list[Any] = Field(
        ..., description="Genericのパラメータ (参照文字列またはTypeSpec)"
    )

    @field_validator("params", mode="before")
    @classmethod
    def validate_params(cls, v: Any) -> Any:
        """paramsの前処理バリデーション（dictをTypeSpecに変換）"""
        if isinstance(v, list):
            result = []
            for item in v:
                if isinstance(item, dict):
                    result.append(_create_spec_from_data(item))
                else:
                    result.append(item)
            return result
        return v

    @model_validator(mode="after")
    def validate_generic_depth(self) -> "GenericTypeSpec":
        """Generic型のネスト深さを検証"""
        MAX_DEPTH = 10

        def check_depth(items: list[TypeSpecOrRef], current_depth: int = 0) -> None:
            if current_depth > MAX_DEPTH:
                raise ValueError(f"Generic型の深さが{MAX_DEPTH}を超えました")
            for item in items:
                if isinstance(item, GenericTypeSpec):
                    check_depth(item.params, current_depth + 1)
                elif isinstance(item, str):
                    # 文字列参照の場合は何もしない
                    pass

        check_depth(self.params)
        return self


# v1.1用: ルートモデル (複数型をキー=型名で管理)
class TypeRoot(BaseModel):
    """YAML型仕様のルートモデル (v1.1構造、循環耐性強化）"""

    types: dict[str, TypeSpec] = Field(
        default_factory=dict, description="型仕様のルート辞書。キー=型名、値=TypeSpec"
    )

    @model_validator(mode="before")
    @classmethod
    def preprocess_types(cls, data: Any) -> Any:
        """TypeRoot構築前の参照文字列処理"""
        if isinstance(data, dict) and "types" in data:
            processed_types = {}
            for name, spec_data in data["types"].items():
                if isinstance(spec_data, dict):
                    # 参照文字列を保持したままTypeSpecを作成
                    spec_data = spec_data.copy()
                    spec_data["name"] = name
                    processed_types[name] = _create_spec_from_data(spec_data)
                else:
                    processed_types[name] = spec_data
            data["types"] = processed_types
        return data

    @field_validator("types", mode="before")
    @classmethod
    def validate_types(cls, v: Any) -> Any:
        """typesフィールドのバリデーション（参照文字列を保持）"""
        if isinstance(v, dict):
            result = {}
            for key, value in v.items():
                if isinstance(value, dict):
                    # dictの場合、参照文字列を保持したままTypeSpecに変換
                    result[key] = _create_spec_from_data(value)
                elif isinstance(value, TypeSpec):
                    result[key] = value
                else:
                    result[key] = value
            return result
        return v


def _preprocess_refs_for_yaml_parsing(data: dict) -> dict:
    """YAML解析後の参照文字列をRefPlaceholderに変換"""
    result: dict[str, Any] = {}
    for key, value in data.items():
        if key == "items" and isinstance(value, str):
            # itemsが参照文字列の場合はRefPlaceholderに変換
            result[key] = RefPlaceholder(ref_name=value)
        elif key == "properties" and isinstance(value, dict):
            # properties内の参照文字列をRefPlaceholderに変換
            processed_props: dict[str, Any] = {}
            for prop_key, prop_value in value.items():
                if isinstance(prop_value, str):
                    # 参照文字列の場合はRefPlaceholderに変換
                    processed_props[prop_key] = RefPlaceholder(ref_name=prop_value)
                else:
                    # TypeSpecデータの場合はそのまま
                    processed_props[prop_key] = prop_value
            result[key] = processed_props
        elif key == "variants" and isinstance(value, list):
            # variants内の参照文字列をRefPlaceholderに変換
            processed_variants: list[Any] = []
            for variant in value:
                if isinstance(variant, str):
                    # 参照文字列の場合はRefPlaceholderに変換
                    processed_variants.append(RefPlaceholder(ref_name=variant))
                else:
                    # TypeSpecデータの場合はそのまま
                    processed_variants.append(variant)
            result[key] = processed_variants
        else:
            result[key] = value
    return result


def _create_spec_from_data(data: dict, root_key: str | None = None) -> TypeSpec:
    """dictからTypeSpecサブクラスを作成 (内部関数)"""
    # 参照文字列を保持するための前処理
    processed_data = _preprocess_refs_for_spec_creation(data)

    # nameが設定されていない場合、root_keyから設定
    if "name" not in processed_data and root_key:
        processed_data["name"] = root_key

    type_key = processed_data.get("type")
    if type_key == "list":
        # itemsが参照文字列の場合は明示的にListTypeSpecとして作成
        items_value = processed_data.get("items")
        if isinstance(items_value, str):
            # 参照文字列の場合は明示的にListTypeSpecとして作成
            return ListTypeSpec(**processed_data)
        else:
            return ListTypeSpec(**processed_data)
    elif type_key == "dict":
        # properties内のdictをTypeSpecに変換
        processed_data["properties"] = {
            k: _create_spec_from_data(v, None) if isinstance(v, dict) else v
            for k, v in processed_data["properties"].items()
        }
        return DictTypeSpec(**processed_data)
    elif type_key == "union":
        return UnionTypeSpec(**processed_data)
    elif type_key == "generic":
        return GenericTypeSpec(**processed_data)
    else:
        # 基本型: nameをroot_keyから補完（v1.1対応）
        return TypeSpec(**processed_data)


def _preprocess_refs_for_spec_creation(data: dict) -> dict[str, Any]:
    """参照文字列を保持するための前処理"""
    result: dict[str, Any] = {}
    for key, value in data.items():
        if key == "items" and isinstance(value, str):
            # itemsが参照文字列の場合はそのまま保持
            result[key] = value
        elif key == "properties" and isinstance(value, dict):
            # properties内の参照文字列を保持
            processed_props: dict[str, Any] = {}
            for prop_key, prop_value in value.items():
                if isinstance(prop_value, str):
                    # 参照文字列の場合はそのまま保持
                    processed_props[prop_key] = prop_value
                else:
                    # TypeSpecデータの場合はそのまま
                    processed_props[prop_key] = prop_value
            result[key] = processed_props
        elif key == "variants" and isinstance(value, list):
            # variants内の参照文字列を保持
            processed_variants: list[Any] = []
            for variant in value:
                if isinstance(variant, str):
                    # 参照文字列の場合はそのまま保持
                    processed_variants.append(variant)
                else:
                    # TypeSpecデータの場合はそのまま
                    processed_variants.append(variant)
            result[key] = processed_variants
        else:
            result[key] = value
    return result


def _create_spec_from_data_preserve_refs(
    data: dict, root_key: str | None = None
) -> TypeSpec:
    """参照文字列を保持したままTypeSpecを作成 (内部関数)"""
    # 参照文字列を明示的に保持するための特別な処理
    type_key = data.get("type")
    if type_key == "list":
        # itemsが参照文字列の場合はそのまま保持
        items_value = data.get("items")
        if isinstance(items_value, str):
            # 参照文字列の場合はそのまま
            list_data = data.copy()
            return ListTypeSpec(**list_data)
        else:
            return ListTypeSpec(**data)
    elif type_key == "dict":
        # propertiesが参照文字列の場合はそのまま保持
        return DictTypeSpec(**data)
    elif type_key == "union":
        # variantsが参照文字列の場合はそのまま保持
        return UnionTypeSpec(**data)
    else:
        # 基本型: nameをroot_keyから補完（v1.1対応）
        if root_key:
            data["name"] = root_key
        return TypeSpec(**data)


# 参照解決のためのコンテキスト
class TypeContext:
    """型参照解決のためのコンテキスト"""

    def __init__(self) -> None:
        self.type_map: dict[str, TypeSpec] = {}
        self.resolving: set[str] = set()  # 循環参照検出用

        # 組み込み型を事前に登録
        self._add_builtin_types()

    def _add_builtin_types(self) -> None:
        """組み込み型をコンテキストに追加"""
        builtin_types = {
            "str": TypeSpec(name="str", type="str", description="String type"),
            "int": TypeSpec(name="int", type="int", description="Integer type"),
            "float": TypeSpec(name="float", type="float", description="Float type"),
            "bool": TypeSpec(name="bool", type="bool", description="Boolean type"),
            "Any": TypeSpec(name="Any", type="any", description="Any type"),
        }
        for name, spec in builtin_types.items():
            self.type_map[name] = spec

    def add_type(self, name: str, spec: TypeSpec) -> None:
        """型をコンテキストに追加"""
        self.type_map[name] = spec

    def resolve_ref(
        self, ref: TypeSpecOrRef
    ) -> TypeSpec | RefPlaceholder:  # 循環時はValueErrorを発生
        """参照を解決してTypeSpecを返す（NewType対応）"""
        if isinstance(ref, RefPlaceholder):
            ref_name = ref.ref_name
            if ref_name in self.resolving:
                # 循環参照の場合、ValueErrorを発生（テスト対応）
                raise ValueError(f"Circular reference detected: {ref_name}")
            if ref_name not in self.type_map and ref_name not in [
                "str",
                "int",
                "float",
                "bool",
                "Any",
            ]:
                raise ValueError(f"Undefined type reference: {ref_name}")

            self.resolving.add(ref_name)
            try:
                resolved = self.type_map[ref_name]
                return self._resolve_nested_refs(resolved)
            finally:
                self.resolving.remove(ref_name)
        elif isinstance(ref, str):
            # str参照の処理
            if ref in self.resolving:
                # 循環参照の場合、ValueErrorを発生（テスト対応）
                raise ValueError(f"Circular reference detected: {ref}")
            if ref not in self.type_map and ref not in [
                "str",
                "int",
                "float",
                "bool",
                "Any",
            ]:
                raise ValueError(f"Undefined type reference: {ref}")

            self.resolving.add(ref)
            try:
                resolved = self.type_map[ref]
                return self._resolve_nested_refs(resolved)
            finally:
                self.resolving.remove(ref)
        else:
            # TypeSpecやその他のオブジェクトの場合はそのまま返す
            return ref

    def _resolve_nested_refs(self, spec: TypeSpec) -> TypeSpec:
        """ネストされた参照を解決"""
        if isinstance(spec, ListTypeSpec):
            if isinstance(spec.items, str):
                # 参照文字列の場合は解決
                resolved_items = self.resolve_ref(spec.items)
                return ListTypeSpec(
                    name=spec.name,
                    type=spec.type,
                    description=spec.description,
                    required=spec.required,
                    items=resolved_items,
                )
            else:
                # すでにTypeSpecの場合はそのまま
                return spec
        elif isinstance(spec, DictTypeSpec):
            resolved_props = {}
            for key, prop in spec.properties.items():
                if isinstance(prop, str):
                    # 参照文字列の場合は解決
                    resolved_props[key] = self.resolve_ref(prop)
                elif isinstance(prop, TypeSpec):
                    # TypeSpecの場合は再帰的に参照解決
                    resolved_props[key] = self._resolve_nested_refs(prop)
                else:
                    # その他の場合はそのまま
                    resolved_props[key] = prop
            return DictTypeSpec(
                name=spec.name,
                type=spec.type,
                description=spec.description,
                required=spec.required,
                properties=resolved_props,
                additional_properties=spec.additional_properties,
            )
        elif isinstance(spec, UnionTypeSpec):
            resolved_variants = []
            for variant in spec.variants:
                if isinstance(variant, str):
                    # 参照文字列の場合は解決
                    resolved_variants.append(self.resolve_ref(variant))
                else:
                    # すでにTypeSpecの場合はそのまま
                    resolved_variants.append(variant)
            return UnionTypeSpec(
                name=spec.name,
                type=spec.type,
                description=spec.description,
                required=spec.required,
                variants=resolved_variants,
            )
        else:
            return spec


# モデル再構築: 循環参照解決のため、モジュール末尾で呼び出し
TypeSpec.model_rebuild()
ListTypeSpec.model_rebuild()
DictTypeSpec.model_rebuild()
UnionTypeSpec.model_rebuild()
GenericTypeSpec.model_rebuild()
TypeRoot.model_rebuild()

# 例の使用: TypeSpecモデルをYAMLにシリアライズ可能
# v1.1例:
# types:
#   User:
#     \"type\": dict
#     \"description\": ユーザー情報
#     \"properties\":
#       id:
#         \"type\": int
#         \"description\": ID
