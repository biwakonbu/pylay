"""CLI単一ファイルモード向けの回帰テスト（Issue #77）

pylay yaml コマンドの単一ファイルモード（pylay yaml src/core/schemas/types.py）向けのテストを提供します。
"""

from pathlib import Path

import pytest

from src.cli.commands.yaml import run_yaml


class TestBasicTypeConversion:
    """基本的な型定義の変換テスト"""

    def test_type_alias_conversion(self, tmp_path: Path) -> None:
        """type文（型エイリアス）の変換をテスト"""
        # フィクスチャファイルをコピー
        fixture_file = Path("tests/fixtures/type_alias.py")
        input_file = tmp_path / "type_alias.py"
        input_file.write_text(fixture_file.read_text())

        # 出力ファイルパス
        output_file = tmp_path / "type_alias.lay.yaml"

        # YAML変換実行
        run_yaml(str(input_file), str(output_file))

        # アサーション
        assert output_file.exists()
        content = output_file.read_text()

        # 型定義が含まれていることを確認
        assert "UserId:" in content
        assert "ProductId:" in content
        assert "Point:" in content
        assert "type: type_alias" in content

        # メタデータが含まれていることを確認
        assert "_metadata:" in content
        assert "generated_by: pylay yaml" in content

    def test_newtype_conversion(self, tmp_path: Path) -> None:
        """NewTypeの変換をテスト"""
        # フィクスチャファイルをコピー
        fixture_file = Path("tests/fixtures/newtype.py")
        input_file = tmp_path / "newtype.py"
        input_file.write_text(fixture_file.read_text())

        # 出力ファイルパス
        output_file = tmp_path / "newtype.lay.yaml"

        # YAML変換実行
        run_yaml(str(input_file), str(output_file))

        # アサーション
        assert output_file.exists()
        content = output_file.read_text()

        # 型定義が含まれていることを確認
        assert "UserId:" in content
        assert "Email:" in content
        assert "Count:" in content
        assert "type: newtype" in content
        assert "base_type: str" in content
        assert "base_type: int" in content

        # メタデータが含まれていることを確認
        assert "_metadata:" in content

    def test_dataclass_conversion(self, tmp_path: Path) -> None:
        """dataclassの変換をテスト"""
        # フィクスチャファイルをコピー
        fixture_file = Path("tests/fixtures/dataclass.py")
        input_file = tmp_path / "dataclass.py"
        input_file.write_text(fixture_file.read_text())

        # 出力ファイルパス
        output_file = tmp_path / "dataclass.lay.yaml"

        # YAML変換実行
        run_yaml(str(input_file), str(output_file))

        # アサーション
        assert output_file.exists()
        content = output_file.read_text()

        # 型定義が含まれていることを確認
        assert "Point:" in content
        assert "User:" in content
        assert "Product:" in content
        assert "type: dataclass" in content

        # dataclass固有の属性が含まれていることを確認
        assert "frozen: true" in content  # Point
        assert "frozen: false" in content  # User, Product
        assert "fields:" in content

        # メタデータが含まれていることを確認
        assert "_metadata:" in content


class TestMixedTypesConversion:
    """複数種類の型定義が混在するファイルの変換テスト"""

    def test_mixed_types_conversion(self, tmp_path: Path) -> None:
        """複数種類の型定義が混在するファイルの変換をテスト"""
        # フィクスチャファイルをコピー
        fixture_file = Path("tests/fixtures/mixed_types.py")
        input_file = tmp_path / "mixed_types.py"
        input_file.write_text(fixture_file.read_text())

        # 出力ファイルパス
        output_file = tmp_path / "mixed_types.lay.yaml"

        # YAML変換実行
        run_yaml(str(input_file), str(output_file))

        # アサーション
        assert output_file.exists()
        content = output_file.read_text()

        # すべての型が含まれていることを確認
        # type文
        assert "UserId:" in content
        assert "Point:" in content
        assert "type: type_alias" in content

        # NewType
        assert "Email:" in content
        assert "Count:" in content
        assert "type: newtype" in content

        # dataclass
        assert "User:" in content
        assert "Product:" in content
        assert "type: dataclass" in content

        # メタデータが含まれていることを確認
        assert "_metadata:" in content


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_empty_file(self, tmp_path: Path, capsys) -> None:
        """型定義が含まれないファイルのエラーハンドリング"""
        # フィクスチャファイルをコピー
        fixture_file = Path("tests/fixtures/empty.py")
        input_file = tmp_path / "empty.py"
        input_file.write_text(fixture_file.read_text())

        # 出力ファイルパス
        output_file = tmp_path / "empty.lay.yaml"

        # 型定義がない場合、エラーメッセージが表示される
        run_yaml(str(input_file), str(output_file))

        # 出力ファイルは生成されない
        assert not output_file.exists()

        # エラーメッセージが出力されていることを確認
        captured = capsys.readouterr()
        assert "変換可能な型がモジュール内に見つかりませんでした" in captured.out

    def test_invalid_syntax(self, tmp_path: Path) -> None:
        """構文エラーを含むファイルのエラーハンドリング"""
        # フィクスチャファイルをコピー
        fixture_file = Path("tests/fixtures/invalid.py")
        input_file = tmp_path / "invalid.py"
        input_file.write_text(fixture_file.read_text())

        # 出力ファイルパス
        output_file = tmp_path / "invalid.lay.yaml"

        # 構文エラーの場合、SystemExitが発生することを確認
        with pytest.raises(SystemExit) as exc_info:
            run_yaml(str(input_file), str(output_file))

        # 終了コードが1であることを確認
        assert exc_info.value.code == 1


class TestRoundtrip:
    """ラウンドトリップテスト（Python → YAML → Python）"""

    def test_roundtrip_type_alias(self, tmp_path: Path) -> None:
        """type文のラウンドトリップ変換"""
        from src.core.converters.yaml_to_type import yaml_to_spec

        # 1. フィクスチャファイルからYAML生成
        fixture_file = Path("tests/fixtures/type_alias.py")
        input_file = tmp_path / "type_alias.py"
        input_file.write_text(fixture_file.read_text())

        output_file = tmp_path / "type_alias.lay.yaml"
        run_yaml(str(input_file), str(output_file))

        # 2. YAML → Spec変換
        yaml_content = output_file.read_text()
        result = yaml_to_spec(yaml_content)

        # 3. 型定義が正しく復元されていることを確認
        from src.core.schemas.yaml_spec import TypeAliasSpec, TypeRoot

        assert isinstance(result, TypeRoot)
        specs = result.types

        # UserId
        assert "UserId" in specs
        user_id_spec = specs["UserId"]
        assert isinstance(user_id_spec, TypeAliasSpec)
        assert user_id_spec.type == "type_alias"
        assert user_id_spec.target == "str"

        # Point
        assert "Point" in specs
        point_spec = specs["Point"]
        assert isinstance(point_spec, TypeAliasSpec)
        assert point_spec.type == "type_alias"
        assert point_spec.target == "tuple[float, float]"

    def test_roundtrip_newtype(self, tmp_path: Path) -> None:
        """NewTypeのラウンドトリップ変換"""
        from src.core.converters.yaml_to_type import yaml_to_spec

        # 1. フィクスチャファイルからYAML生成
        fixture_file = Path("tests/fixtures/newtype.py")
        input_file = tmp_path / "newtype.py"
        input_file.write_text(fixture_file.read_text())

        output_file = tmp_path / "newtype.lay.yaml"
        run_yaml(str(input_file), str(output_file))

        # 2. YAML → Spec変換
        yaml_content = output_file.read_text()
        result = yaml_to_spec(yaml_content)

        # 3. 型定義が正しく復元されていることを確認
        from src.core.schemas.yaml_spec import NewTypeSpec, TypeRoot

        assert isinstance(result, TypeRoot)
        specs = result.types

        # UserId
        assert "UserId" in specs
        user_id_spec = specs["UserId"]
        assert isinstance(user_id_spec, NewTypeSpec)
        assert user_id_spec.type == "newtype"
        assert user_id_spec.base_type == "str"

        # Count
        assert "Count" in specs
        count_spec = specs["Count"]
        assert isinstance(count_spec, NewTypeSpec)
        assert count_spec.type == "newtype"
        assert count_spec.base_type == "int"

    def test_roundtrip_dataclass(self, tmp_path: Path) -> None:
        """dataclassのラウンドトリップ変換"""
        from src.core.converters.yaml_to_type import yaml_to_spec

        # 1. フィクスチャファイルからYAML生成
        fixture_file = Path("tests/fixtures/dataclass.py")
        input_file = tmp_path / "dataclass.py"
        input_file.write_text(fixture_file.read_text())

        output_file = tmp_path / "dataclass.lay.yaml"
        run_yaml(str(input_file), str(output_file))

        # 2. YAML → Spec変換
        yaml_content = output_file.read_text()
        result = yaml_to_spec(yaml_content)

        # 3. 型定義が正しく復元されていることを確認
        from src.core.schemas.yaml_spec import DataclassSpec, TypeRoot, TypeSpec

        assert isinstance(result, TypeRoot)
        specs = result.types

        # Point（frozen=True）
        assert "Point" in specs
        point_spec = specs["Point"]
        assert isinstance(point_spec, DataclassSpec)
        assert point_spec.type == "dataclass"
        assert point_spec.frozen is True
        assert "x" in point_spec.fields
        assert isinstance(point_spec.fields["x"], TypeSpec)
        assert point_spec.fields["x"].type == "float"

        # User（frozen=False）
        assert "User" in specs
        user_spec = specs["User"]
        assert isinstance(user_spec, DataclassSpec)
        assert user_spec.type == "dataclass"
        assert user_spec.frozen is False
        assert "name" in user_spec.fields
        assert isinstance(user_spec.fields["name"], TypeSpec)
        assert user_spec.fields["name"].type == "str"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
