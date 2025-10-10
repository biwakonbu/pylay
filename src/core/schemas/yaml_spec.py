from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.core.schemas.types import (
    AdditionalPropertiesFlag,
    Description,
    RequiredFlag,
    TypeSpecName,
    TypeSpecType,
)


class RefPlaceholder(BaseModel):
    """参照文字列を保持するためのプレースホルダー(Pydantic v2対応強化)"""

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
        """Pydanticのスキーマ生成

        Pydanticモデル用のスキーマを生成します。
        """
        from pydantic_core import core_schema

        return core_schema.str_schema()


class TypeSpec(BaseModel):
    """YAML形式の型仕様の基底モデル(v1.1対応、循環参照耐性強化)"""

    model_config = ConfigDict(arbitrary_types_allowed=True)  # 遅延型解決はmodel_rebuildで対応

    name: TypeSpecName | None = Field(None, description="型の名前 (v1.1ではオプション。参照時は不要)")
    type: TypeSpecType = Field(..., description="基本型 (str, int, float, bool, list, dict, union)")
    description: Description | None = Field(None, description="型の説明")
    required: RequiredFlag = Field(True, description="必須かどうか")


# 参照解決のための型エイリアス(前方参照用)
type TypeSpecOrRef = RefPlaceholder | str | TypeSpec


class ListTypeSpec(TypeSpec):
    """リスト型の仕様"""

    type: Literal["list"] = "list"  # type: ignore[assignment]  # Literal型でTypeSpecのtypeを特殊化
    items: Any = Field(..., description="リストの要素型 (参照文字列またはTypeSpec)")

    @field_validator("items", mode="before")
    @classmethod
    def validate_items(cls, v: Any) -> Any:
        """itemsの前処理バリデーション(dictをTypeSpecに変換)"""
        if isinstance(v, dict):
            return _create_spec_from_data(v)
        return v


class DictTypeSpec(TypeSpec):
    """辞書型の仕様(プロパティの型をTypeSpecOrRefに統一)"""

    type: Literal["dict"] = "dict"  # type: ignore[assignment]  # Literal型でTypeSpecのtypeを特殊化
    # NOTE: 設計上、YAML仕様から動的にプロパティを読み込むため Any型を使用
    # TODO(Issue #18, Target: v2.0): TypeSpecOrRefに狭める移行計画
    #   - 現状: Pydanticバリデーション前の段階でdictが渡されるためAnyが必要
    #   - 移行方法: Pydantic v2のSerializationInfoを活用して
    #     バリデーション前後で型を分離
    #   - トラッキング: Issue #18 (型定義ファイル構造の整理) で
    #     バリデーション戦略を再設計
    #   - 担当: 型定義リファクタリングチーム
    properties: dict[str, Any] = Field(default_factory=dict, description="辞書のプロパティ (参照文字列またはTypeSpec)")
    additional_properties: AdditionalPropertiesFlag = Field(default=False, description="追加プロパティ許可")

    @field_validator("properties", mode="before")
    @classmethod
    def validate_properties_before(cls, v: Any) -> Any:
        """propertiesフィールドの前処理バリデーション(参照文字列を保持)"""
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
    """Union型の仕様(参照型をTypeSpecOrRefに統一)

    Union型の型仕様を定義します。参照型はTypeSpecOrRefに統一されています。
    """

    type: Literal["union"] = "union"  # type: ignore[assignment]  # Literal型でTypeSpecのtypeを特殊化
    variants: list[Any] = Field(..., description="Unionのバリアント (参照文字列またはTypeSpec)")

    @field_validator("variants", mode="before")
    @classmethod
    def validate_variants(cls, v: Any) -> Any:
        """variantsの前処理バリデーション(dictをTypeSpecに変換)"""
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
    """
    Generic型の仕様(例: Generic[T])(参照型をTypeSpecOrRefに統一)

    Generic型の型仕様を定義します(例: Generic[T])。
    参照型はTypeSpecOrRefに統一されています。
    """

    type: Literal["generic"] = "generic"  # type: ignore[assignment]  # Literal型でTypeSpecのtypeを特殊化
    params: list[Any] = Field(..., description="Genericのパラメータ (参照文字列またはTypeSpec)")

    @field_validator("params", mode="before")
    @classmethod
    def validate_params(cls, v: Any) -> Any:
        """paramsの前処理バリデーション(dictをTypeSpecに変換)"""
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
        """Generic型のネスト深さを検証

        Generic型のネスト深さをチェックし、制限を超える場合はエラーを発生させます。
        """
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


class TypeAliasSpec(TypeSpec):
    """type文(型エイリアス)の仕様

    Python 3.12+ の type 文で定義される型エイリアスを表現します。
    例: type UserId = str
        type Point = tuple[float, float]
    """

    type: Literal["type_alias"] = "type_alias"  # type: ignore[assignment]
    target: str = Field(..., description="エイリアス先の型(例: str, tuple[float, float])")


class NewTypeSpec(TypeSpec):
    """NewType の仕様

    typing.NewType で定義される独自型を表現します。
    例: UserId = NewType('UserId', str)
    """

    type: Literal["newtype"] = "newtype"  # type: ignore[assignment]
    base_type: str = Field(..., description="基底型(例: str, int)")


class DataclassSpec(TypeSpec):
    """dataclass の仕様

    dataclasses.dataclass で定義されるデータクラスを表現します。
    例: @dataclass(frozen=True)
        class Point:
            x: float
            y: float
    """

    type: Literal["dataclass"] = "dataclass"  # type: ignore[assignment]
    frozen: bool = Field(default=False, description="不変(frozen)フラグ")
    fields: dict[str, Any] = Field(default_factory=dict, description="フィールド定義")

    @field_validator("fields", mode="before")
    @classmethod
    def validate_fields(cls, v: Any) -> Any:
        """fieldsフィールドの前処理バリデーション"""
        if isinstance(v, dict):
            result: dict[str, Any] = {}
            for key, value in v.items():
                if isinstance(value, str):
                    result[key] = value
                elif isinstance(value, dict):
                    result[key] = _create_spec_from_data(value)
                else:
                    result[key] = value
            return result
        return v


# v1.1用: ルートモデル (複数型をキー=型名で管理)
class TypeRoot(BaseModel):
    """YAML型仕様のルートモデル (v1.1構造、循環耐性強化)"""

    model_config = ConfigDict(populate_by_name=True)

    types: dict[TypeSpecName, TypeSpec] = Field(
        default_factory=dict, description="型仕様のルート辞書。キー=型名、値=TypeSpec"
    )
    imports_: dict[str, str] | None = Field(
        default=None,
        description="外部型のインポート情報(型名 → インポートパス)",
        alias="_imports",
    )
    metadata_: dict[str, Any] | None = Field(default=None, description="メタデータ情報", alias="_metadata")

    @model_validator(mode="before")
    @classmethod
    def preprocess_types(cls, data: Any) -> Any:
        """TypeRoot構築前の参照文字列処理

        TypeRootを構築する前に参照文字列を解決します。
        """
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
        """typesフィールドのバリデーション(参照文字列を保持)"""
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


def _create_spec_from_simple_format(data: dict, root_key: str | None = None) -> TypeSpec:
    """シンプル形式(fields:構造)からTypeSpecを作成

    Args:
        data: シンプル形式のYAMLデータ
        root_key: 型名(トップレベルキー)

    Returns:
        TypeSpec: 変換されたTypeSpec
    """

    # 基本情報を取得
    description = data.get("description", "")
    fields_data = data.get("fields", {})

    # propertiesに変換
    properties: dict[str, TypeSpecOrRef] = {}
    for field_name, field_info in fields_data.items():
        field_type_str = field_info.get("type", "any")
        field_required = field_info.get("required", True)
        field_description = field_info.get("description", "")
        field_default = field_info.get("default")

        # 型文字列を解析してTypeSpecに変換
        field_spec = _parse_type_string(field_type_str)
        field_spec.description = field_description
        field_spec.required = field_required

        # デフォルト値を設定
        if field_default is not None:
            # デフォルト値は文字列として保存されているので、元の型に変換
            # (現在は簡易実装として文字列のまま保存)
            pass

        properties[field_name] = field_spec

    # DictTypeSpecを作成(クラス型として扱う)
    # NOTE: Pydanticクラスはdict型として扱い、コード生成時にBaseModelに変換
    return DictTypeSpec(
        type="dict",
        name=root_key or "UnknownClass",
        description=description,
        required=True,
        properties=properties,
        additional_properties=False,
    )


def _parse_type_string(type_str: str) -> TypeSpec:
    """型文字列をTypeSpecに変換

    Args:
        type_str: 型文字列(例: "str", "list[str]", "dict[str, int]", "str | null")

    Returns:
        TypeSpec: 変換されたTypeSpec
    """
    # Union型の検出("|" を含む)
    if " | " in type_str:
        variants_str = [v.strip() for v in type_str.split(" | ")]
        variants: list[TypeSpecOrRef] = []
        for variant_str in variants_str:
            if variant_str == "null":
                variants.append(
                    TypeSpec(
                        name="null",
                        type="null",
                        description="None type",
                        required=True,
                    )
                )
            else:
                variant_spec = _parse_type_string(variant_str)
                variants.append(variant_spec)
        return UnionTypeSpec(
            type="union",
            name=f"Union[{type_str}]",
            description=None,
            required=True,
            variants=variants,
        )

    # List型の検出
    if type_str.startswith("list[") and type_str.endswith("]"):
        item_type_str = type_str[5:-1]  # "list[str]" -> "str"
        if item_type_str in {"str", "int", "float", "bool"}:
            item_spec = TypeSpec(name=item_type_str, type=item_type_str, description=None, required=True)
        else:
            # カスタム型は参照文字列として保持
            return ListTypeSpec(
                type="list",
                name=type_str,
                description=None,
                required=True,
                items=item_type_str,
            )
        return ListTypeSpec(type="list", name=type_str, description=None, required=True, items=item_spec)

    # Dict型の検出
    if type_str.startswith("dict[") and type_str.endswith("]"):
        dict_params = type_str[5:-1]  # "dict[str, int]" -> "str, int"
        key_type_str, value_type_str = (p.strip() for p in dict_params.split(",", 1))

        # 簡易実装: dict[str, T] の場合のみpropertiesとして扱う
        if key_type_str == "str":
            # 値型をparseしてpropertiesとして設定
            value_spec = _parse_type_string(value_type_str)
            return DictTypeSpec(
                type="dict",
                name=type_str,
                description=None,
                required=True,
                properties={value_type_str: value_spec},
                additional_properties=False,
            )

    # 基本型または参照型
    if type_str in {"str", "int", "float", "bool", "any", "null"}:
        return TypeSpec(name=type_str, type=type_str, description=None, required=True)
    else:
        # カスタム型は参照文字列として扱う(型名のみ)
        # この場合、TypeSpecを作成せず文字列として返すべきだが、
        # TypeSpecOrRefの制約により、TypeSpecを作成する
        return TypeSpec(name=type_str, type="reference", description=None, required=True)


def _create_spec_from_data(data: dict, root_key: str | None = None) -> TypeSpec:
    """dictからTypeSpecサブクラスを作成 (内部関数)

    シンプル形式(fields:構造)と従来形式(properties:構造)の両方をサポート
    """
    # シンプル形式の検出: "fields" キーがある場合
    if "fields" in data:
        return _create_spec_from_simple_format(data, root_key)

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
    elif type_key == "type_alias":
        # type文(型エイリアス)の場合
        return TypeAliasSpec(**processed_data)
    elif type_key == "newtype":
        # NewTypeの場合
        return NewTypeSpec(**processed_data)
    elif type_key == "dataclass":
        # dataclassの場合
        return DataclassSpec(**processed_data)
    else:
        # 基本型: nameをroot_keyから補完(v1.1対応)
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
            "str": TypeSpec(name="str", type="str", description="String type"),  # type: ignore[call-arg]  # Pydantic BaseModel動的属性
            "int": TypeSpec(name="int", type="int", description="Integer type"),  # type: ignore[call-arg]
            "float": TypeSpec(name="float", type="float", description="Float type"),  # type: ignore[call-arg]
            "bool": TypeSpec(name="bool", type="bool", description="Boolean type"),  # type: ignore[call-arg]
            "Any": TypeSpec(name="Any", type="any", description="Any type"),  # type: ignore[call-arg]
        }
        for name, spec in builtin_types.items():
            self.type_map[name] = spec

    def add_type(self, name: str, spec: TypeSpec) -> None:
        """型をコンテキストに追加"""
        self.type_map[name] = spec

    def resolve_ref(self, ref: TypeSpecOrRef) -> TypeSpec | RefPlaceholder:  # 循環時はValueErrorを発生
        """参照を解決してTypeSpecを返す(Annotated型対応)"""
        if isinstance(ref, RefPlaceholder):
            ref_name = ref.ref_name
            if ref_name in self.resolving:
                # 循環参照の場合、ValueErrorを発生(テスト対応)
                raise ValueError(f"Circular reference detected: {ref_name}")
            if ref_name not in self.type_map and ref_name not in [
                "str",
                "int",
                "float",
                "bool",
                "Any",
            ]:
                # 未定義の型参照は文字列として残す(型エイリアスなど)
                return ref_name  # type: ignore[return-value]

            self.resolving.add(ref_name)
            try:
                resolved = self.type_map[ref_name]
                return self._resolve_nested_refs(resolved)
            finally:
                self.resolving.remove(ref_name)
        elif isinstance(ref, str):
            # str参照の処理
            if ref in self.resolving:
                # 循環参照の場合、ValueErrorを発生(テスト対応)
                raise ValueError(f"Circular reference detected: {ref}")
            if ref not in self.type_map and ref not in [
                "str",
                "int",
                "float",
                "bool",
                "Any",
            ]:
                # 未定義の型参照は文字列として残す(型エイリアスなど)
                return ref  # type: ignore[return-value]

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
TypeAliasSpec.model_rebuild()
NewTypeSpec.model_rebuild()
DataclassSpec.model_rebuild()
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
