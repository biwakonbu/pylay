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
"""
    )

    # AST解析
    type_defs = extract_type_definitions_from_ast(test_file)

    # 検証
    assert "UserId" in type_defs
    assert type_defs["UserId"]["kind"] == "type_alias"
    assert type_defs["UserId"]["target"] == "str"

    assert "Point" in type_defs
    assert type_defs["Point"]["kind"] == "type_alias"
    assert type_defs["Point"]["target"] == "tuple[float, float]"


def test_extract_newtype_from_ast(tmp_path: Path) -> None:
    """NewTypeがAST解析で正しく抽出されることを確認"""
    # テストファイルを作成
    test_file = tmp_path / "test_newtypes.py"
    test_file.write_text(
        """
from typing import NewType

UserId = NewType('UserId', str)
Count = NewType('Count', int)
"""
    )

    # AST解析
    type_defs = extract_type_definitions_from_ast(test_file)

    # 検証
    assert "UserId" in type_defs
    assert type_defs["UserId"]["kind"] == "newtype"
    assert type_defs["UserId"]["base_type"] == "str"

    assert "Count" in type_defs
    assert type_defs["Count"]["kind"] == "newtype"
    assert type_defs["Count"]["base_type"] == "int"


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
'''
    )

    # AST解析
    type_defs = extract_type_definitions_from_ast(test_file)

    # 検証
    assert "Point" in type_defs
    assert type_defs["Point"]["kind"] == "dataclass"
    assert type_defs["Point"]["frozen"] is True
    assert type_defs["Point"]["docstring"] == "2D座標点"
    assert "x" in type_defs["Point"]["fields"]
    assert type_defs["Point"]["fields"]["x"]["type"] == "float"

    assert "User" in type_defs
    assert type_defs["User"]["kind"] == "dataclass"
    assert type_defs["User"]["frozen"] is False
    assert type_defs["User"]["docstring"] == "ユーザー情報"
    assert "name" in type_defs["User"]["fields"]


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
'''
    )

    # AST解析
    type_defs = extract_type_definitions_from_ast(test_file)

    # 検証: Product（frozen=False）
    assert "Product" in type_defs
    assert type_defs["Product"]["kind"] == "dataclass"
    assert type_defs["Product"]["frozen"] is False
    assert type_defs["Product"]["docstring"] == "商品情報"
    assert "name" in type_defs["Product"]["fields"]
    assert type_defs["Product"]["fields"]["name"]["type"] == "str"
    assert "price" in type_defs["Product"]["fields"]
    assert type_defs["Product"]["fields"]["price"]["type"] == "int"

    # 検証: Location（frozen=True）
    assert "Location" in type_defs
    assert type_defs["Location"]["kind"] == "dataclass"
    assert type_defs["Location"]["frozen"] is True
    assert type_defs["Location"]["docstring"] == "位置情報"
    assert "latitude" in type_defs["Location"]["fields"]
    assert type_defs["Location"]["fields"]["latitude"]["type"] == "float"
    assert "longitude" in type_defs["Location"]["fields"]
    assert type_defs["Location"]["fields"]["longitude"]["type"] == "float"


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
'''
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
