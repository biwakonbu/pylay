"""type/NewType/dataclassのYAML変換テスト（Issue #56）

このテストは、type文、NewType、dataclassが正しくYAMLに変換されることを確認します。
"""

from pathlib import Path

import pytest

from src.core.converters.type_to_yaml import (
    extract_type_definitions_from_ast,
    types_to_yaml_simple,
)


def test_extract_type_alias_from_ast(tmp_path: Path) -> None:
    """type文（型エイリアス）がAST解析で正しく抽出されることを確認"""
    # テストファイルを作成
    test_file = tmp_path / "test_types.py"
    test_file.write_text(
        """
type UserId = str
type Point = tuple[float, float]
""",
    )

    # AST解析
    type_defs = extract_type_definitions_from_ast(test_file)

    # 検証
    assert "UserId" in type_defs
    assert type_defs["UserId"]["kind"] == "type_alias"
    assert type_defs["UserId"]["target"] == "str"  # type: ignore[typeddict-item]

    assert "Point" in type_defs
    assert type_defs["Point"]["kind"] == "type_alias"
    assert type_defs["Point"]["target"] == "tuple[float, float]"  # type: ignore[typeddict-item]


def test_extract_newtype_from_ast(tmp_path: Path) -> None:
    """NewTypeがAST解析で正しく抽出されることを確認"""
    # テストファイルを作成
    test_file = tmp_path / "test_newtypes.py"
    test_file.write_text(
        """
from typing import NewType

UserId = NewType('UserId', str)
Count = NewType('Count', int)
""",
    )

    # AST解析
    type_defs = extract_type_definitions_from_ast(test_file)

    # 検証
    assert "UserId" in type_defs
    assert type_defs["UserId"]["kind"] == "newtype"
    assert type_defs["UserId"]["base_type"] == "str"  # type: ignore[typeddict-item]

    assert "Count" in type_defs
    assert type_defs["Count"]["kind"] == "newtype"
    assert type_defs["Count"]["base_type"] == "int"  # type: ignore[typeddict-item]


def test_extract_newtype_with_attribute_reference(tmp_path: Path) -> None:
    """typing.NewType や t.NewType などの属性参照形式のNewTypeが正しく抽出されることを確認（Issue #74）"""
    # テストファイルを作成
    test_file = tmp_path / "test_attribute_newtypes.py"
    test_file.write_text(
        """
import typing
import typing as t

# typing.NewType(...) 形式
UserId = typing.NewType('UserId', str)
Count = typing.NewType('Count', int)

# t.NewType(...) 形式（エイリアス）
Email = t.NewType('Email', str)
Score = t.NewType('Score', float)
""",
    )

    # AST解析
    type_defs = extract_type_definitions_from_ast(test_file)

    # 検証: typing.NewType
    assert "UserId" in type_defs
    assert type_defs["UserId"]["kind"] == "newtype"
    assert type_defs["UserId"]["base_type"] == "str"  # type: ignore[typeddict-item]

    assert "Count" in type_defs
    assert type_defs["Count"]["kind"] == "newtype"
    assert type_defs["Count"]["base_type"] == "int"  # type: ignore[typeddict-item]

    # 検証: t.NewType
    assert "Email" in type_defs
    assert type_defs["Email"]["kind"] == "newtype"
    assert type_defs["Email"]["base_type"] == "str"  # type: ignore[typeddict-item]

    assert "Score" in type_defs
    assert type_defs["Score"]["kind"] == "newtype"
    assert type_defs["Score"]["base_type"] == "float"  # type: ignore[typeddict-item]


def test_extract_dataclass_from_ast(tmp_path: Path) -> None:
    """dataclassがAST解析で正しく抽出されることを確認"""
    # テストファイルを作成
    test_file = tmp_path / "test_dataclasses.py"
    test_file.write_text(
        '''
from dataclasses import dataclass

@dataclass(frozen=True)
class Point:
    """2D座標点"""
    x: float
    y: float

@dataclass
class User:
    """ユーザー情報"""
    name: str
    age: int
''',
    )

    # AST解析
    type_defs = extract_type_definitions_from_ast(test_file)

    # 検証
    assert "Point" in type_defs
    assert type_defs["Point"]["kind"] == "dataclass"
    assert type_defs["Point"]["frozen"] is True  # type: ignore[typeddict-item]
    assert type_defs["Point"]["docstring"] == "2D座標点"
    assert "x" in type_defs["Point"]["fields"]  # type: ignore[typeddict-item]
    assert type_defs["Point"]["fields"]["x"]["type"] == "float"  # type: ignore[typeddict-item]

    assert "User" in type_defs
    assert type_defs["User"]["kind"] == "dataclass"
    assert type_defs["User"]["frozen"] is False  # type: ignore[typeddict-item]
    assert type_defs["User"]["docstring"] == "ユーザー情報"
    assert "name" in type_defs["User"]["fields"]  # type: ignore[typeddict-item]


def test_extract_dataclass_with_module_qualified_decorator(tmp_path: Path) -> None:
    """モジュール修飾付きdataclassデコレーター（@dataclasses.dataclass）が正しく抽出されることを確認"""
    # テストファイルを作成
    test_file = tmp_path / "test_qualified_dataclasses.py"
    test_file.write_text(
        '''
import dataclasses

@dataclasses.dataclass
class Product:
    """商品情報"""
    name: str
    price: int

@dataclasses.dataclass(frozen=True)
class Location:
    """位置情報"""
    latitude: float
    longitude: float
''',
    )

    # AST解析
    type_defs = extract_type_definitions_from_ast(test_file)

    # 検証: Product（frozen=False）
    assert "Product" in type_defs
    assert type_defs["Product"]["kind"] == "dataclass"
    assert type_defs["Product"]["frozen"] is False  # type: ignore[typeddict-item]
    assert type_defs["Product"]["docstring"] == "商品情報"
    assert "name" in type_defs["Product"]["fields"]  # type: ignore[typeddict-item]
    assert type_defs["Product"]["fields"]["name"]["type"] == "str"  # type: ignore[typeddict-item]
    assert "price" in type_defs["Product"]["fields"]  # type: ignore[typeddict-item]
    assert type_defs["Product"]["fields"]["price"]["type"] == "int"  # type: ignore[typeddict-item]

    # 検証: Location（frozen=True）
    assert "Location" in type_defs
    assert type_defs["Location"]["kind"] == "dataclass"
    assert type_defs["Location"]["frozen"] is True  # type: ignore[typeddict-item]
    assert type_defs["Location"]["docstring"] == "位置情報"
    assert "latitude" in type_defs["Location"]["fields"]  # type: ignore[typeddict-item]
    assert type_defs["Location"]["fields"]["latitude"]["type"] == "float"  # type: ignore[typeddict-item]
    assert "longitude" in type_defs["Location"]["fields"]  # type: ignore[typeddict-item]
    assert type_defs["Location"]["fields"]["longitude"]["type"] == "float"  # type: ignore[typeddict-item]


def test_types_to_yaml_simple_with_ast_types() -> None:
    """AST解析結果がtypes_to_yaml_simpleで正しくYAMLに変換されることを確認"""
    # AST解析結果のモックデータ
    ast_types = {
        "UserId": {
            "kind": "type_alias",
            "target": "str",
            "docstring": None,
        },
        "Email": {
            "kind": "newtype",
            "base_type": "str",
            "docstring": None,
        },
        "Point": {
            "kind": "dataclass",
            "frozen": True,
            "fields": {
                "x": {"type": "float", "required": True},
                "y": {"type": "float", "required": True},
            },
            "docstring": "2D座標点",
        },
    }

    # YAML変換
    yaml_output = types_to_yaml_simple(ast_types)

    # 検証
    assert "UserId:" in yaml_output
    assert "type: type_alias" in yaml_output
    assert "target: str" in yaml_output

    assert "Email:" in yaml_output
    assert "type: newtype" in yaml_output
    assert "base_type: str" in yaml_output

    assert "Point:" in yaml_output
    assert "type: dataclass" in yaml_output
    assert "frozen: true" in yaml_output
    assert "description: 2D座標点" in yaml_output
    assert "fields:" in yaml_output


def test_integration_type_to_yaml(tmp_path: Path) -> None:
    """統合テスト: type/NewType/dataclassを含むファイルの完全変換"""
    # テストファイルを作成
    test_file = tmp_path / "integration_test.py"
    test_file.write_text(
        '''
"""統合テスト用の型定義"""

from typing import NewType
from dataclasses import dataclass

# type文
type UserId = str
type Point = tuple[float, float]

# NewType
Email = NewType('Email', str)
Count = NewType('Count', int)

# dataclass
@dataclass(frozen=True)
class User:
    """ユーザー情報"""
    id: str
    name: str
    email: str

@dataclass
class Product:
    """商品情報"""
    name: str
    price: float
    stock: int = 0
''',
    )

    # AST解析
    type_defs = extract_type_definitions_from_ast(test_file)

    # YAML変換
    yaml_output = types_to_yaml_simple(type_defs, source_file_path=test_file)

    # 検証: すべての型が含まれている
    assert "UserId:" in yaml_output
    assert "Point:" in yaml_output
    assert "Email:" in yaml_output
    assert "Count:" in yaml_output
    assert "User:" in yaml_output
    assert "Product:" in yaml_output

    # 検証: 各型の属性が正しい
    assert "type: type_alias" in yaml_output
    assert "type: newtype" in yaml_output
    assert "type: dataclass" in yaml_output
    assert "frozen: true" in yaml_output  # User
    assert "frozen: false" in yaml_output  # Product


def test_yaml_roundtrip_with_type_alias_newtype_dataclass() -> None:
    """ラウンドトリップテスト: YAML→Spec変換でTypeAliasSpec/NewTypeSpec/DataclassSpecが正しく生成されることを確認"""
    from src.core.converters.yaml_to_type import yaml_to_spec
    from src.core.schemas.yaml_spec import (
        DataclassSpec,
        NewTypeSpec,
        TypeAliasSpec,
    )

    yaml_content = """
UserId:
  type: type_alias
  target: str
  description: ユーザーID

Email:
  type: newtype
  base_type: str
  description: メールアドレス

Point:
  type: dataclass
  frozen: true
  fields:
    x:
      type: float
      required: true
    y:
      type: float
      required: true
  description: 2D座標点

User:
  type: dataclass
  frozen: false
  fields:
    name:
      type: str
      required: true
    age:
      type: int
      required: true
  description: ユーザー情報
"""

    # YAML → Spec変換
    result = yaml_to_spec(yaml_content)

    # TypeRootから型定義を取得
    from src.core.schemas.yaml_spec import TypeRoot

    assert isinstance(result, TypeRoot)
    specs = result.types

    # 検証: TypeAliasSpec
    assert "UserId" in specs
    user_id_spec = specs["UserId"]
    assert isinstance(user_id_spec, TypeAliasSpec)
    assert user_id_spec.type == "type_alias"
    assert user_id_spec.target == "str"
    assert user_id_spec.description == "ユーザーID"

    # 検証: NewTypeSpec
    assert "Email" in specs
    email_spec = specs["Email"]
    assert isinstance(email_spec, NewTypeSpec)
    assert email_spec.type == "newtype"
    assert email_spec.base_type == "str"
    assert email_spec.description == "メールアドレス"

    # 検証: DataclassSpec（frozen=True）
    assert "Point" in specs
    point_spec = specs["Point"]
    assert isinstance(point_spec, DataclassSpec)
    assert point_spec.type == "dataclass"
    assert point_spec.frozen is True
    assert point_spec.description == "2D座標点"
    assert "x" in point_spec.fields
    assert "y" in point_spec.fields
    # fieldsの値はTypeSpecオブジェクトなので、.typeでアクセス
    from src.core.schemas.yaml_spec import TypeSpec

    assert isinstance(point_spec.fields["x"], TypeSpec)
    assert point_spec.fields["x"].type == "float"
    assert isinstance(point_spec.fields["y"], TypeSpec)
    assert point_spec.fields["y"].type == "float"

    # 検証: DataclassSpec（frozen=False）
    assert "User" in specs
    user_spec = specs["User"]
    assert isinstance(user_spec, DataclassSpec)
    assert user_spec.type == "dataclass"
    assert user_spec.frozen is False
    assert user_spec.description == "ユーザー情報"
    assert "name" in user_spec.fields
    assert "age" in user_spec.fields
    assert isinstance(user_spec.fields["name"], TypeSpec)
    assert user_spec.fields["name"].type == "str"
    assert isinstance(user_spec.fields["age"], TypeSpec)
    assert user_spec.fields["age"].type == "int"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
