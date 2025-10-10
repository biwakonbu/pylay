import ast
import inspect
from pathlib import Path
from typing import Any, ForwardRef, Generic, NotRequired, TypedDict, get_args, get_origin
from typing import Union as TypingUnion

from pydantic import BaseModel
from ruamel.yaml import YAML

from src.core.schemas.graph import TypeDependencyGraph
from src.core.schemas.yaml_spec import (
    DictTypeSpec,
    GenericTypeSpec,
    ListTypeSpec,
    TypeSpec,
    TypeSpecOrRef,
    UnionTypeSpec,
)

# プロジェクトルートパッケージ名
PROJECT_ROOT_PACKAGE = "src"


# AST解析結果の型定義
class TypeAliasEntry(TypedDict):
    """type文（型エイリアス）のAST解析結果"""

    kind: str  # "type_alias"
    target: str
    docstring: NotRequired[str | None]


class NewTypeEntry(TypedDict):
    """NewTypeのAST解析結果"""

    kind: str  # "newtype"
    base_type: str
    docstring: NotRequired[str | None]


class DataclassFieldInfo(TypedDict):
    """dataclassフィールド情報"""

    type: str
    required: bool


class DataclassEntry(TypedDict):
    """dataclassのAST解析結果"""

    kind: str  # "dataclass"
    frozen: bool
    fields: dict[str, DataclassFieldInfo]
    docstring: NotRequired[str | None]


# AST解析結果の共用型
ASTEntry = TypeAliasEntry | NewTypeEntry | DataclassEntry


def extract_imports_from_file(file_path: Path) -> dict[str, str]:
    """ファイルからインポート情報を抽出(ASTベース)

    Args:
        file_path: Pythonファイルのパス

    Returns:
        型名 → インポートパス の辞書
        例: {"Literal": "typing", "BaseModel": "pydantic", "Path": "pathlib"}
    """
    import_map: dict[str, str] = {}

    try:
        with open(file_path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        for node in ast.walk(tree):
            # from X import Y, Z
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    # 実際の名前(asがあればその名前)
                    imported_name = alias.asname if alias.asname else alias.name
                    import_map[imported_name] = f"{module}.{alias.name}" if module else alias.name

            # import X
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imported_name = alias.asname if alias.asname else alias.name
                    import_map[imported_name] = alias.name

    except Exception as e:
        # エラーが発生してもクラッシュしない
        print(f"Warning: Failed to extract imports from {file_path}: {e}")

    return import_map


def _resolve_type_import_path(typ: type[Any], source_module_path: str | None = None) -> tuple[str, str | None]:
    """型のインポートパスを解決

    Args:
        typ: 型オブジェクト
        source_module_path: 現在のモジュールパス(例: "src.core.analyzer.models")

    Returns:
        (型名, インポートパス or None)
        - 同じファイル内: (TypeName, None)
        - プロジェクト内: (TypeName, ".core.schemas.types.TypeName")
        - 外部ライブラリ: (TypeName, "pathlib.Path")
    """
    if not hasattr(typ, "__module__"):
        return (typ.__name__ if hasattr(typ, "__name__") else str(typ), None)

    type_module = typ.__module__
    type_name = typ.__name__

    # 同じモジュール(同じファイル)の場合
    if source_module_path and type_module == source_module_path:
        return (type_name, None)

    # プロジェクト内の型かチェック
    if type_module.startswith(PROJECT_ROOT_PACKAGE + "."):
        # プロジェクト内 → 相対パス(.で始まる)
        # "src.core.schemas.types" → ".core.schemas.types.TypeName"
        relative_path = type_module[len(PROJECT_ROOT_PACKAGE) :]
        full_path = f"{relative_path}.{type_name}"
        return (type_name, full_path)

    # 外部ライブラリ → 絶対パス
    # 標準ライブラリの内部モジュール(_local等)をクリーン化
    if "._" in type_module:
        # pathlib._local.Path → pathlib.Path
        clean_module = type_module.split("._")[0]
        full_qualified_name = f"{clean_module}.{type_name}"
    else:
        full_qualified_name = f"{type_module}.{type_name}"

    return (type_name, full_qualified_name)


def _recursive_dump(obj: Any) -> Any:
    """Pydanticモデルを再帰的にdictに変換

    Pydanticモデルのインスタンスを再帰的に辞書形式に変換します。
    """
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    elif isinstance(obj, dict):
        return {k: _recursive_dump(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_recursive_dump(v) for v in obj]
    else:
        return obj


MAX_DEPTH = 10  # Generic再帰の深さ制限


def _get_basic_type_str(typ: type[Any]) -> str:
    """基本型の型名を取得"""
    basic_type_mapping = {
        str: "str",
        int: "int",
        float: "float",
        bool: "bool",
    }
    return basic_type_mapping.get(typ, "any")


def _get_type_name(typ: type[Any] | None) -> str:
    """型名を取得(ジェネリック型の場合も考慮)"""
    if isinstance(typ, ForwardRef):
        # ForwardRefの場合、アンカー形式で出力
        return f"&{typ.__forward_arg__}"

    # None型の特別処理
    if typ is type(None) or typ is None:
        return "null"

    # UnionTypeの場合、argsから動的名前生成
    origin = get_origin(typ)
    if origin is TypingUnion or str(origin) == "<class 'types.UnionType'>":
        args = get_args(typ)
        if args:
            arg_names = [_get_type_name(arg) for arg in args]
            return f"Union[{', '.join(arg_names)}]"
        return "Union"

    if hasattr(typ, "__name__"):
        return typ.__name__

    # origin_nameがNoneの場合のフォールバック
    if hasattr(typ, "__name__"):
        return typ.__name__
    return str(typ)


def _recurse_generic_args(args: tuple[Any, ...], depth: int = 0) -> list[TypeSpecOrRef]:
    """再帰的にGeneric引数を展開(深さ制限付き)"""
    if depth > MAX_DEPTH:
        raise RecursionError(f"Generic型の深さが{MAX_DEPTH}を超えました")

    result: list[TypeSpecOrRef] = []
    for arg in args:
        if get_origin(arg) is None:
            # 非ジェネリック型
            if arg in {str, int, float, bool}:
                result.append(type_to_spec(arg))
            else:
                result.append(_get_type_name(arg))
        else:
            # ジェネリック型の場合、再帰的に展開
            param_spec = type_to_spec(arg)
            result.append(param_spec)
    return result


def _get_docstring(typ: type[Any]) -> str | None:
    """型またはクラスのdocstringを取得(冗長なBaseModel docstringは除外)"""
    docstring = inspect.getdoc(typ)

    # BaseModelやその他のフレームワーク基底クラスの冗長なdocstringを検出
    if docstring and any(
        phrase in docstring
        for phrase in [
            '!!! abstract "Usage Documentation"',  # Pydantic BaseModel
            "A base class for creating Pydantic models",
            "__pydantic_",  # Pydanticの内部属性の説明
        ]
    ):
        return None  # 冗長なdocstringは削除

    return docstring


def _get_field_docstring(cls: type[Any], field_name: str) -> str | None:
    """クラスフィールドのdocstringを取得"""
    try:
        # dataclassesの場合
        if hasattr(cls, "__dataclass_fields__"):
            field = cls.__dataclass_fields__.get(field_name)
            if field and field.metadata.get("doc"):
                doc = field.metadata["doc"]
                return str(doc) if doc is not None else None

        # Pydantic Fieldの場合
        annotations = getattr(cls, "__annotations__", {})
        if field_name in annotations:
            # クラス属性としてdocstringを探す
            doc_attr_name = f"{field_name}_doc"
            if hasattr(cls, doc_attr_name):
                doc_value = getattr(cls, doc_attr_name)
                if isinstance(doc_value, str):
                    return doc_value

            # 型アノテーションにdocstringが含まれる場合(簡易的な対応)
            # 実際にはより洗練された方法が必要
    except Exception:
        pass
    return None


def _get_simple_type_name(typ: type[Any] | None) -> str:
    """型の簡潔な名前を取得(Union[str, None]のような形式)"""
    if typ is type(None) or typ is None:
        return "None"

    origin = get_origin(typ)
    args = get_args(typ)

    # Union型の場合
    if origin is TypingUnion or str(origin) == "<class 'types.UnionType'>":
        if args:
            arg_names = [_get_simple_type_name(arg) for arg in args]
            return " | ".join(arg_names)
        return "Union"

    # List型の場合
    if origin is list:
        if args:
            item_type = _get_simple_type_name(args[0])
            return f"list[{item_type}]"
        return "list"

    # Dict型の場合
    if origin is dict:
        if args and len(args) >= 2:
            key_type = _get_simple_type_name(args[0])
            value_type = _get_simple_type_name(args[1])
            return f"dict[{key_type}, {value_type}]"
        return "dict"

    # 基本型
    if hasattr(typ, "__name__"):
        return typ.__name__

    return str(typ)


def _collect_imports_from_type_string(
    type_str: str,
    file_imports: dict[str, str],
    imports_map: dict[str, str],
) -> None:
    """型文字列から外部型を抽出し、インポート情報を収集

    Args:
        type_str: 型文字列（例: "str", "list[UserId]", "dict[str, User]"）
        file_imports: ファイルから抽出したインポート情報（型名 → インポートパス）
        imports_map: インポート情報を格納する辞書（型名 → インポートパス）
    """
    import re

    # 基本型（str, int, float, bool, list, dict, tuple, set等）はスキップ
    builtin_types = {
        "str",
        "int",
        "float",
        "bool",
        "list",
        "dict",
        "tuple",
        "set",
        "frozenset",
        "bytes",
        "bytearray",
        "None",
        "Any",
        "object",
    }

    # 型文字列から型名を抽出（カッコや記号を除去）
    # 例: "list[UserId]" → ["list", "UserId"]
    # 例: "dict[str, User]" → ["dict", "str", "User"]
    type_names = re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", type_str)

    for type_name in type_names:
        # 基本型はスキップ
        if type_name in builtin_types:
            continue

        # file_importsに存在する外部型のみimports_mapに追加
        if type_name in file_imports:
            imports_map[type_name] = file_imports[type_name]


def _get_simple_type_name_with_imports(
    typ: type[Any] | None,
    source_module_path: str | None,
    imports_map: dict[str, str],
    file_imports: dict[str, str] | None = None,
) -> str:
    """型の簡潔な名前を取得し、必要なインポート情報を収集

    Args:
        typ: 型オブジェクト
        source_module_path: 現在のモジュールパス
        imports_map: インポート情報を格納する辞書(型名 → インポートパス)
        file_imports: ファイルから抽出したインポート情報(型名 → インポートパス)

    Returns:
        型名文字列(例: "str", "list[str]", "LineNumber")
    """
    if typ is type(None) or typ is None:
        return "None"

    if file_imports is None:
        file_imports = {}

    origin = get_origin(typ)
    args = get_args(typ)

    # Literal型の場合(具体的な値を保持)
    from typing import Literal as LiteralType

    if origin is LiteralType:
        # file_importsから Literal のインポート元を取得
        if "Literal" in file_imports:
            imports_map["Literal"] = file_imports["Literal"]
        else:
            # フォールバック: typing.Literal
            imports_map["Literal"] = "typing.Literal"
        if args:
            # Literal値を保持(人間可読性を向上)
            literal_values = ", ".join(f'"{arg}"' if isinstance(arg, str) else str(arg) for arg in args)
            # type フィールドに "literal" を設定し、候補を列挙
            return f"Literal[{literal_values}]"
        return "str"  # 空のLiteralはstrにフォールバック

    # Union型の場合
    if origin is TypingUnion or str(origin) == "<class 'types.UnionType'>":
        if args:
            arg_names = [
                _get_simple_type_name_with_imports(arg, source_module_path, imports_map, file_imports) for arg in args
            ]
            return " | ".join(arg_names)
        return "Union"

    # List型の場合
    if origin is list:
        if args:
            item_type = _get_simple_type_name_with_imports(args[0], source_module_path, imports_map, file_imports)
            return f"list[{item_type}]"
        return "list"

    # Dict型の場合
    if origin is dict:
        if args and len(args) >= 2:
            key_type = _get_simple_type_name_with_imports(args[0], source_module_path, imports_map, file_imports)
            value_type = _get_simple_type_name_with_imports(args[1], source_module_path, imports_map, file_imports)
            return f"dict[{key_type}, {value_type}]"
        return "dict"

    # 基本型
    if hasattr(typ, "__name__"):
        type_name = typ.__name__

        # 基本型はインポート不要
        if type_name in {"str", "int", "float", "bool", "Any"}:
            return type_name

        # カスタム型の場合、インポート情報を収集
        _, import_path = _resolve_type_import_path(typ, source_module_path)
        if import_path:
            imports_map[type_name] = import_path

        return type_name

    return str(typ)


def _extract_pydantic_field_info_with_imports(
    cls: type[Any],
    source_module_path: str | None,
    imports_map: dict[str, str],
    file_imports: dict[str, str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Pydanticモデルからフィールド情報を抽出(インポート情報付き、完全版)

    Args:
        cls: Pydanticモデルクラス
        source_module_path: 現在のモジュールパス
        imports_map: インポート情報を格納する辞書
        file_imports: ファイルから抽出したインポート情報

    Returns:
        フィールド情報の辞書
    """
    from pydantic_core import PydanticUndefined

    if file_imports is None:
        file_imports = {}

    fields_info: dict[str, dict[str, Any]] = {}

    if issubclass(cls, BaseModel):
        for field_name, field_info in cls.model_fields.items():
            # 型名を取得し、インポート情報を収集
            annotation = field_info.annotation if field_info.annotation is not None else type(None)
            type_str = _get_simple_type_name_with_imports(annotation, source_module_path, imports_map, file_imports)

            field_data: dict[str, Any] = {
                "type": type_str,
                "required": field_info.is_required(),
            }

            # descriptionを取得
            if field_info.description:
                field_data["description"] = field_info.description

            # field_info セクション(Field()の詳細情報)
            field_info_dict = {}

            # デフォルト値を取得
            if not field_info.is_required():
                if field_info.default is not PydanticUndefined:
                    # 固定デフォルト値
                    field_info_dict["default"] = repr(field_info.default)
                elif field_info.default_factory is not None:
                    # ファクトリ関数
                    factory = field_info.default_factory
                    # 組み込み型(list, dict, set等)はそのまま名前を使用
                    if factory in (list, dict, set, tuple, frozenset):
                        field_info_dict["default_factory"] = factory.__name__
                    else:
                        # lambda や他のcallableの場合は関数名(__name__)を使用
                        # ただし、<lambda>の場合は実行結果から推測
                        factory_name = getattr(factory, "__name__", str(factory))
                        if factory_name == "<lambda>":
                            try:
                                result = factory()  # type: ignore[call-arg]
                                if isinstance(result, list):
                                    field_info_dict["default_factory"] = "list"
                                elif isinstance(result, dict):
                                    field_info_dict["default_factory"] = "dict"
                                elif isinstance(result, set):
                                    field_info_dict["default_factory"] = "set"
                                else:
                                    field_info_dict["default_factory"] = factory_name
                            except Exception:
                                field_info_dict["default_factory"] = factory_name
                        else:
                            field_info_dict["default_factory"] = factory_name

            # バリデーション制約を取得
            if hasattr(field_info, "metadata"):
                for metadata in field_info.metadata:
                    # annotated_types の制約 (Ge, Le, Gt, Lt, MultipleOf, etc.)
                    metadata_type = type(metadata).__name__
                    if metadata_type in ["Ge", "Gt", "Le", "Lt"]:
                        # ge, gt, le, lt 制約
                        constraint_name = metadata_type.lower()
                        if hasattr(metadata, constraint_name):
                            field_info_dict[constraint_name] = getattr(metadata, constraint_name)
                    elif metadata_type == "MultipleOf":
                        if hasattr(metadata, "multiple_of"):
                            field_info_dict["multiple_of"] = metadata.multiple_of
                    elif metadata_type == "MinLen":
                        if hasattr(metadata, "min_length"):
                            field_info_dict["min_length"] = metadata.min_length
                    elif metadata_type == "MaxLen":
                        if hasattr(metadata, "max_length"):
                            field_info_dict["max_length"] = metadata.max_length
                    elif hasattr(metadata, "__dict__"):
                        # その他のメタデータ
                        for key, value in metadata.__dict__.items():
                            if value is not None and key not in ["type", "annotation"]:
                                field_info_dict[key] = value

            # field_infoがある場合のみ追加
            if field_info_dict:
                field_data["field_info"] = field_info_dict

            fields_info[field_name] = field_data

    return fields_info


def _extract_dataclass_field_info(cls: type[Any]) -> dict[str, dict[str, Any]]:
    """dataclassからフィールド情報を抽出(シンプル版)

    Args:
        cls: dataclassの型オブジェクト

    Returns:
        フィールド名とフィールド情報の辞書
    """
    from dataclasses import MISSING, fields

    fields_info: dict[str, dict[str, Any]] = {}

    for field in fields(cls):
        field_data: dict[str, Any] = {
            "type": _get_simple_type_name(field.type),  # type: ignore[arg-type]
            "required": field.default is MISSING and field.default_factory is MISSING,
        }

        # デフォルト値を取得
        if field.default is not MISSING:
            field_data["default"] = str(field.default)
        elif field.default_factory is not MISSING:
            factory = field.default_factory
            # 組み込み型の場合
            if factory in (list, dict, set, tuple, frozenset):
                field_data["default_factory"] = factory.__name__
            else:
                # lambda等の場合
                factory_name = getattr(factory, "__name__", str(factory))
                if factory_name == "<lambda>":
                    try:
                        result = factory()
                        if isinstance(result, list):
                            field_data["default_factory"] = "list"
                        elif isinstance(result, dict):
                            field_data["default_factory"] = "dict"
                        elif isinstance(result, set):
                            field_data["default_factory"] = "set"
                        else:
                            field_data["default_factory"] = factory_name
                    except Exception:
                        field_data["default_factory"] = factory_name
                else:
                    field_data["default_factory"] = factory_name

        fields_info[field.name] = field_data

    return fields_info


def _get_class_properties_with_docstrings(cls: type[Any]) -> dict[str, TypeSpecOrRef]:
    """クラスのプロパティとフィールドdocstringを取得"""
    properties: dict[str, TypeSpecOrRef] = {}

    # クラスアノテーションからフィールドを取得
    annotations = getattr(cls, "__annotations__", {})

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
                type="unknown",
                description=_get_field_docstring(cls, field_name),
                required=True,
            )

    return properties


def type_to_spec(typ: type[Any]) -> TypeSpec:
    """Python型をTypeSpecに変換(v1.1対応)

    Pythonの型オブジェクトをTypeSpec形式に変換します。v1.1対応版です。
    """
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
            return TypeSpec(  # type: ignore[call-arg]  # Pydantic BaseModel動的属性
                name=type_name, type=type_str, description=description
            )
        else:
            # カスタムクラスはdict型として扱い、フィールドのdocstringを取得
            properties = _get_class_properties_with_docstrings(typ)
            return DictTypeSpec(  # type: ignore[call-arg]  # Pydantic BaseModel動的属性
                name=type_name,
                type="dict",
                description=description,
                properties=properties,
            )

    elif origin is Generic:
        # Generic[T]型(カスタムGenericサポート)
        if args:
            generic_args = _recurse_generic_args(args)
            return GenericTypeSpec(  # type: ignore[call-arg]  # Pydantic BaseModel動的属性
                name=type_name, params=generic_args, description=description
            )
        else:
            return GenericTypeSpec(  # type: ignore[call-arg]  # Pydantic BaseModel動的属性
                name=type_name, params=[], description=description
            )

    elif origin is list:
        # List型は常にtype: "list" として処理
        if args:
            item_type = args[0]
            if get_origin(item_type) is None and item_type not in {
                str,
                int,
                float,
                bool,
            }:
                # カスタム型の場合、参照として保持
                return ListTypeSpec(  # type: ignore[call-arg]  # Pydantic BaseModel動的属性
                    name=type_name,
                    items=_get_type_name(item_type),  # 参照文字列として保持
                    description=description,
                )
            else:
                # 基本型の場合、TypeSpecとして展開
                items_spec = type_to_spec(item_type)
                return ListTypeSpec(  # type: ignore[call-arg]  # Pydantic BaseModel動的属性
                    name=type_name, items=items_spec, description=description
                )
        else:
            # 型パラメータなし
            return ListTypeSpec(  # type: ignore[call-arg]  # Pydantic BaseModel動的属性
                name=type_name,
                items=TypeSpec(  # type: ignore[call-arg]  # Pydantic BaseModel動的属性
                    name="any", type="any"
                ),
                description=description,
            )

    elif origin is dict:
        if args and len(args) >= 2:
            key_type, value_type = args[0], args[1]

            # Dict[str, T] のような場合、propertiesとして扱う
            if key_type is str:
                dict_properties: dict[str, TypeSpecOrRef] = {}

                # 値型がカスタム型の場合、参照として保持
                if get_origin(value_type) is None and value_type not in {
                    str,
                    int,
                    float,
                    bool,
                }:
                    # 各プロパティの型名をキーとして参照を保持
                    # (実際のプロパティ解決は別途)
                    dict_properties[_get_type_name(value_type)] = _get_type_name(value_type)
                else:
                    # 基本型の場合、TypeSpecとして展開
                    value_spec = type_to_spec(value_type)
                    dict_properties[_get_type_name(value_type)] = value_spec

                return DictTypeSpec(  # type: ignore[call-arg]  # Pydantic BaseModel動的属性
                    name=type_name, properties=dict_properties, description=description
                )
            else:
                # キーがstr以外の場合、簡易的にanyとして扱う
                return DictTypeSpec(  # type: ignore[call-arg]  # Pydantic BaseModel動的属性
                    name=type_name, properties={}, description=description
                )
        else:
            return DictTypeSpec(  # type: ignore[call-arg]  # Pydantic BaseModel動的属性
                name=type_name, properties={}, description=description
            )

    elif origin is TypingUnion or str(origin) == "<class 'types.UnionType'>":
        # Union型(Union[int, str] など)
        if args:
            variants: list[TypeSpecOrRef] = []

            for arg in args:
                # Noneやtype(None)は基本型として扱う
                if arg is type(None) or arg is None:
                    # None型は"null"として表現
                    variants.append(
                        TypeSpec(  # type: ignore[call-arg]
                            name="null", type="null", description="None type"
                        )
                    )
                elif get_origin(arg) is None and arg not in {str, int, float, bool}:
                    # カスタム型の場合、参照として保持
                    variants.append(_get_type_name(arg))
                else:
                    # 基本型の場合、TypeSpecとして展開
                    variant_spec = type_to_spec(arg)
                    variants.append(variant_spec)

            return UnionTypeSpec(  # type: ignore[call-arg]  # Pydantic BaseModel動的属性
                name=type_name, variants=variants, description=description
            )
        else:
            union_variants: list[TypeSpecOrRef] = []
            return UnionTypeSpec(  # type: ignore[call-arg]  # Pydantic BaseModel動的属性
                name=type_name, variants=union_variants, description=description
            )

    else:
        # 未サポート型
        return TypeSpec(  # type: ignore[call-arg]  # Pydantic BaseModel動的属性
            name=type_name, type="unknown", description=description
        )


def type_to_yaml(
    typ: type[Any], output_file: str | None = None, as_root: bool = True
) -> str | dict[str, dict[str, Any]]:
    """型をYAML文字列に変換、またはファイル出力 (v1.1対応)"""
    from io import StringIO

    from ruamel.yaml.comments import CommentedMap, CommentedSeq
    from ruamel.yaml.scalarstring import LiteralScalarString

    def _prepare_yaml_data(data: Any) -> Any:
        """複数行文字列を| 形式に変換し、CommentedMap/Seqに変換"""
        if isinstance(data, dict):
            cm = CommentedMap()
            for k, v in data.items():
                cm[k] = _prepare_yaml_data(v)
            return cm
        elif isinstance(data, list):
            cs = CommentedSeq()
            for v in data:
                cs.append(_prepare_yaml_data(v))
            return cs
        elif isinstance(data, str) and "\n" in data:
            # 改行を含む文字列はヒアドキュメント形式(| 形式)で出力
            return LiteralScalarString(data)
        else:
            return data

    spec = type_to_spec(typ)

    # v1.1構造: nameフィールドを除外して出力
    spec_data = _recursive_dump(spec.model_dump(exclude={"name"}))
    spec_data = _prepare_yaml_data(spec_data)

    if as_root:
        # 単一型: 型名をキーとして出力
        yaml_data = CommentedMap()
        yaml_data[_get_type_name(typ)] = spec_data
        yaml_parser = YAML()
        yaml_parser.preserve_quotes = True
        yaml_parser.default_flow_style = False
        yaml_parser.width = 4096  # 行折り返しを防止
        yaml_parser.indent(mapping=2, sequence=2, offset=0)

        output = StringIO()
        yaml_parser.dump(yaml_data, output)
        yaml_str = output.getvalue()
    else:
        # 従来形式 (互換性用)
        yaml_parser = YAML()
        yaml_parser.preserve_quotes = True
        yaml_parser.default_flow_style = False
        yaml_parser.width = 4096  # 行折り返しを防止
        yaml_parser.indent(mapping=2, sequence=2, offset=0)

        output = StringIO()
        yaml_parser.dump(spec.model_dump(), output)
        yaml_str = output.getvalue()

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(yaml_str)

    return yaml_str if as_root else yaml_str


def types_to_yaml_simple(
    types: dict[str, type[Any] | ASTEntry],
    source_module_path: str | None = None,
    source_file_path: Path | None = None,
) -> str:
    """複数型をシンプルなYAML形式に変換(Pydantic/dataclass/type/NewType対応、完全版)

    Args:
        types: 型名と型オブジェクトの辞書、またはAST解析結果の辞書
        source_module_path: ソースモジュールパス(例: "src.core.analyzer.models")
        source_file_path: ソースファイルパス(インポート情報抽出用)

    Returns:
        シンプルな形式のYAML文字列(_imports, base_classes, field_info含む)
    """
    from dataclasses import is_dataclass
    from io import StringIO

    from ruamel.yaml.comments import CommentedMap
    from ruamel.yaml.scalarstring import LiteralScalarString

    yaml_data = CommentedMap()

    # ファイルからインポート情報を抽出(ASTベース)
    file_imports: dict[str, str] = {}
    if source_file_path and source_file_path.exists():
        file_imports = extract_imports_from_file(source_file_path)

    # インポート情報を収集
    imports_map: dict[str, str] = {}

    for type_name, typ in types.items():
        type_data = CommentedMap()

        # AST解析結果(ASTEntry)の場合
        if isinstance(typ, dict):
            kind = typ.get("kind")

            # type文(型エイリアス)
            if kind == "type_alias":
                # 型ガード: TypeAliasEntry
                assert "target" in typ
                type_alias_entry: TypeAliasEntry = typ  # type: ignore[assignment]

                type_data["type"] = "type_alias"
                target = type_alias_entry["target"]
                type_data["target"] = target
                docstring = type_alias_entry.get("docstring")
                if docstring:
                    type_data["description"] = docstring

                # targetに外部型が含まれる場合、_importsに追加
                _collect_imports_from_type_string(target, file_imports, imports_map)

                yaml_data[type_name] = type_data

            # NewType
            elif kind == "newtype":
                # 型ガード: NewTypeEntry
                assert "base_type" in typ
                newtype_entry: NewTypeEntry = typ  # type: ignore[assignment]

                type_data["type"] = "newtype"
                base_type = newtype_entry["base_type"]
                type_data["base_type"] = base_type
                docstring = newtype_entry.get("docstring")
                if docstring:
                    type_data["description"] = docstring

                # base_typeに外部型が含まれる場合、_importsに追加
                _collect_imports_from_type_string(base_type, file_imports, imports_map)

                yaml_data[type_name] = type_data

            # dataclass(AST解析結果)
            elif kind == "dataclass":
                # 型ガード: DataclassEntry
                assert "frozen" in typ and "fields" in typ
                dataclass_entry: DataclassEntry = typ  # type: ignore[assignment]

                type_data["type"] = "dataclass"
                type_data["frozen"] = dataclass_entry.get("frozen", False)
                docstring = dataclass_entry.get("docstring")
                if docstring:
                    if "\n" in docstring:
                        type_data["description"] = LiteralScalarString(docstring)
                    else:
                        type_data["description"] = docstring
                if "fields" in dataclass_entry:
                    fields = dataclass_entry["fields"]
                    # 各フィールドの型から外部型を収集
                    for field_info in fields.values():
                        field_type = field_info["type"]
                        _collect_imports_from_type_string(field_type, file_imports, imports_map)
                    type_data["fields"] = CommentedMap(fields)
                yaml_data[type_name] = type_data

            continue

        # 型オブジェクトの場合(従来の処理)
        # クラスのdocstringを取得
        docstring = _get_docstring(typ)
        if docstring:
            # 複数行のdocstringはヒアドキュメント形式(| 形式)で出力
            if "\n" in docstring:
                type_data["description"] = LiteralScalarString(docstring)
            else:
                type_data["description"] = docstring

        # base_classesを取得
        if hasattr(typ, "__bases__"):
            base_classes = []
            for base in typ.__bases__:
                if base.__name__ == "object":
                    continue
                base_name, base_import_path = _resolve_type_import_path(base, source_module_path)
                base_classes.append(base_name)
                if base_import_path:
                    imports_map[base_name] = base_import_path
            if base_classes:
                type_data["base_classes"] = base_classes

        # Pydantic BaseModelの場合
        if isinstance(typ, type) and issubclass(typ, BaseModel):
            fields_info = _extract_pydantic_field_info_with_imports(typ, source_module_path, imports_map, file_imports)
            if fields_info:
                type_data["fields"] = CommentedMap(fields_info)
            yaml_data[type_name] = type_data

        # dataclassの場合(型オブジェクト)
        elif isinstance(typ, type) and is_dataclass(typ):
            type_data["type"] = "dataclass"
            # frozen属性をチェック(getattr を使って型チェックを回避)
            dataclass_params = getattr(typ, "__dataclass_params__", None)
            type_data["frozen"] = bool(dataclass_params and getattr(dataclass_params, "frozen", False))

            fields_info = _extract_dataclass_field_info(typ)
            if fields_info:
                type_data["fields"] = CommentedMap(fields_info)
            yaml_data[type_name] = type_data

    # _importsセクションを先頭に追加
    if imports_map:
        final_data = CommentedMap()
        final_data["_imports"] = CommentedMap(sorted(imports_map.items()))
        final_data.update(yaml_data)
        yaml_data = final_data

    # YAML出力
    yaml_parser = YAML()
    yaml_parser.preserve_quotes = True
    yaml_parser.default_flow_style = False
    yaml_parser.width = 4096
    yaml_parser.indent(mapping=2, sequence=2, offset=0)

    output = StringIO()
    yaml_parser.dump(yaml_data, output)
    return output.getvalue()


def types_to_yaml(types: dict[str, type[Any]], output_file: str | None = None) -> str:
    """複数型をYAML文字列に変換 (v1.1対応)"""
    from io import StringIO

    from ruamel.yaml.comments import CommentedMap, CommentedSeq
    from ruamel.yaml.scalarstring import LiteralScalarString

    def _prepare_yaml_data(data: Any) -> Any:
        """複数行文字列を| 形式に変換し、CommentedMap/Seqに変換"""
        if isinstance(data, dict):
            cm = CommentedMap()
            for k, v in data.items():
                cm[k] = _prepare_yaml_data(v)
            return cm
        elif isinstance(data, list):
            cs = CommentedSeq()
            for v in data:
                cs.append(_prepare_yaml_data(v))
            return cs
        elif isinstance(data, str) and "\n" in data:
            # 改行を含む文字列はヒアドキュメント形式(| 形式)で出力
            return LiteralScalarString(data)
        else:
            return data

    specs = CommentedMap()
    for name, typ in types.items():
        spec = type_to_spec(typ)
        # nameフィールドを除外
        spec_data = spec.model_dump(exclude={"name"})
        # 複数行文字列をLiteralScalarStringに変換
        specs[name] = _prepare_yaml_data(spec_data)

    # types: を省略して直接型定義を出力
    yaml_parser = YAML()
    yaml_parser.preserve_quotes = True
    yaml_parser.default_flow_style = False
    yaml_parser.width = 4096  # 行折り返しを防止
    # mapping: 辞書のインデント幅
    # sequence: リストのインデント幅
    # offset: リストハイフンと最初のキーの間のスペース数(0=改行してインデント)
    yaml_parser.indent(mapping=2, sequence=2, offset=0)

    output = StringIO()
    yaml_parser.dump(specs, output)
    yaml_str = output.getvalue()

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(yaml_str)

    return yaml_str


def extract_type_definitions_from_ast(module_path: Path) -> dict[str, ASTEntry]:
    """ASTを使って型定義を抽出(type/NewType/dataclass対応)

    Args:
        module_path: Pythonファイルのパス

    Returns:
        型名 → 型定義情報の辞書
        例: {
            "UserId": {"kind": "type_alias", "target": "str"},
            "Point": {"kind": "dataclass", "frozen": True, "fields": {...}}
        }
    """
    type_defs: dict[str, ASTEntry] = {}

    try:
        tree = ast.parse(module_path.read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            # 1. type文の抽出(Python 3.12+)
            if isinstance(node, ast.TypeAlias):
                type_name = node.name.id if isinstance(node.name, ast.Name) else str(node.name)
                target_type = ast.unparse(node.value)
                type_defs[type_name] = {
                    "kind": "type_alias",
                    "target": target_type,
                    "docstring": None,  # TypeAliasにはdocstringがない
                }

            # 2. dataclassの抽出
            elif isinstance(node, ast.ClassDef):
                is_dataclass = False
                frozen = False

                for decorator in node.decorator_list:
                    # @dataclass
                    if isinstance(decorator, ast.Name) and decorator.id == "dataclass":
                        is_dataclass = True
                    # @dataclasses.dataclass, @dc.dataclass などの属性参照
                    elif isinstance(decorator, ast.Attribute) and decorator.attr == "dataclass":
                        is_dataclass = True
                    # @dataclass(frozen=True)
                    elif isinstance(decorator, ast.Call):
                        func = decorator.func
                        # 関数名が "dataclass" の場合
                        if isinstance(func, ast.Name) and func.id == "dataclass":
                            is_dataclass = True
                        # @dataclasses.dataclass(frozen=True) などの属性参照
                        elif isinstance(func, ast.Attribute) and func.attr == "dataclass":
                            is_dataclass = True

                        # frozen引数をチェック
                        if is_dataclass:
                            for keyword in decorator.keywords:
                                if keyword.arg == "frozen":
                                    if isinstance(keyword.value, ast.Constant):
                                        frozen = bool(keyword.value.value)

                if is_dataclass:
                    # フィールド情報を抽出
                    fields: dict[str, Any] = {}
                    for item in node.body:
                        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                            field_name = item.target.id
                            field_type = ast.unparse(item.annotation)
                            fields[field_name] = {
                                "type": field_type,
                                "required": item.value is None,  # デフォルト値がなければ必須
                            }

                    type_defs[node.name] = {
                        "kind": "dataclass",
                        "frozen": frozen,
                        "fields": fields,
                        "docstring": ast.get_docstring(node),
                    }

            # 3. NewTypeの抽出(変数代入を検索)
            elif isinstance(node, ast.Assign):
                # NewType('UserId', str) のパターン
                if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    target_name = node.targets[0].id
                    if isinstance(node.value, ast.Call):
                        func = node.value.func
                        is_newtype = False

                        # NewType の検出(ast.Name または ast.Attribute)
                        if isinstance(func, ast.Name) and func.id == "NewType":
                            is_newtype = True
                        # typing.NewType, t.NewType などの属性参照
                        elif isinstance(func, ast.Attribute) and func.attr == "NewType":
                            is_newtype = True

                        if is_newtype and len(node.value.args) >= 2:
                            # 第2引数が基底型
                            base_type = ast.unparse(node.value.args[1])
                            type_defs[target_name] = {
                                "kind": "newtype",
                                "base_type": base_type,
                                "docstring": None,
                            }

    except Exception as e:
        print(f"Warning: AST解析エラー ({module_path}): {e}")

    return type_defs


def extract_types_from_module(module_path: str | Path) -> str | None:
    """Pythonモジュールから型を抽出してYAML形式で返す

    Args:
        module_path: Pythonモジュールのパス(.pyファイル)

    Returns:
        YAML形式の型定義文字列、または型定義がない場合 None
    """
    import ast

    module_path = Path(module_path)

    # モジュールから型定義を抽出
    type_definitions: dict[str, Any] = {}

    try:
        # AST解析で型定義を抽出
        with open(module_path, encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source)

        for node in ast.walk(tree):
            # クラス定義(Pydantic BaseModelなど)
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                # 基底クラスを取得
                base_classes = []
                if node.bases:
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            base_classes.append(base.id)
                        elif isinstance(base, ast.Attribute):
                            # typing.List などの場合
                            base_classes.append(ast.unparse(base))

                # クラス情報を記録
                type_definitions[class_name] = {
                    "type": "class",
                    "bases": base_classes,
                    "docstring": ast.get_docstring(node),
                }

            # 変数アノテーション付きの代入(型エイリアスとして扱う)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                var_name = node.target.id
                if node.annotation:
                    var_type = ast.unparse(node.annotation)
                    type_definitions[var_name] = {
                        "type": "type_alias",
                        "alias_to": var_type,
                        # AnnAssignにはdocstringがないため、Noneを返す
                        "docstring": None,
                    }

            # 関数定義はスキップ(独自型ではないため)
            # elif isinstance(node, ast.FunctionDef):
            #     ... (コメントアウト: function混入を防ぐ)

    except Exception as e:
        # AST解析に失敗した場合はNoneを返す
        print(f"AST解析エラー: {e}")
        return None

    # 抽出された型定義をYAML形式に変換(空ならNone)
    if type_definitions:
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=4, offset=2)

        # 出力用の構造を作成(types: を省略して直接型定義を出力)
        output_data = type_definitions

        import io

        output = io.StringIO()
        yaml.dump(output_data, output)
        return output.getvalue().strip()
    else:
        return None  # 空の場合、Noneを返す(ノイズ回避)


def graph_to_yaml(graph: TypeDependencyGraph, output_file: str | None = None) -> str:
    """
    TypeDependencyGraphからYAML形式の依存仕様を生成します。

    Args:
        graph: 型依存グラフ
        output_file: 出力ファイルパス(Noneの場合、文字列として返す)

    Returns:
        YAML形式の依存仕様文字列
    """
    from src.core.analyzer.graph_processor import GraphProcessor

    processor = GraphProcessor()
    yaml_data = processor.convert_graph_to_yaml_spec(graph)

    yaml_parser = YAML()
    yaml_parser.preserve_quotes = True
    yaml_parser.indent(mapping=2, sequence=4, offset=2)

    import io

    output = io.StringIO()
    yaml_parser.dump(yaml_data, output)
    yaml_str = output.getvalue().strip()

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(yaml_str)

    return yaml_str


# 例
if __name__ == "__main__":
    # from typing import List, Dict, Union  # Not needed with built-in types

    # テスト型
    UserId = str  # 簡易的な型エイリアス
    Users = list[dict[str, str]]
    Result = int | str

    print("v1.1形式出力:")
    print(type_to_yaml(Users, as_root=True))
    print("\n従来形式出力:")
    print(type_to_yaml(type(Result), as_root=False))
