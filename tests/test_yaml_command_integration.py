"""pylay yamlコマンドの統合テスト

ファイル/ディレクトリ/pyproject.toml の3パターンをテスト
"""

from pathlib import Path

from src.cli.commands.yaml import (
    _calculate_file_hash,
    _generate_metadata_section,
    _has_type_definitions,
    _validate_metadata,
    find_python_files_with_type_definitions,
    run_yaml,
)
from src.core.schemas.pylay_config import PylayConfig


class TestTypeDefinitionDetection:
    """型定義検出機能のテスト"""

    def test_has_basemodel(self, tmp_path: Path) -> None:
        """BaseModelを含むファイルを検出"""
        test_file = tmp_path / "models.py"
        test_file.write_text(
            """
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
"""
        )
        assert _has_type_definitions(test_file)

    def test_has_type_alias(self, tmp_path: Path) -> None:
        """type文を含むファイルを検出"""
        test_file = tmp_path / "types.py"
        test_file.write_text(
            """
type UserId = str
type Point = tuple[float, float]
"""
        )
        assert _has_type_definitions(test_file)

    def test_has_newtype(self, tmp_path: Path) -> None:
        """NewTypeを含むファイルを検出"""
        test_file = tmp_path / "types.py"
        test_file.write_text(
            """
from typing import NewType

UserId = NewType('UserId', str)
"""
        )
        assert _has_type_definitions(test_file)

    def test_has_dataclass(self, tmp_path: Path) -> None:
        """dataclassを含むファイルを検出"""
        test_file = tmp_path / "models.py"
        test_file.write_text(
            """
from dataclasses import dataclass

@dataclass
class Point:
    x: float
    y: float
"""
        )
        assert _has_type_definitions(test_file)

    def test_has_enum(self, tmp_path: Path) -> None:
        """Enumを含むファイルを検出"""
        test_file = tmp_path / "enums.py"
        test_file.write_text(
            """
from enum import Enum

class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
"""
        )
        assert _has_type_definitions(test_file)

    def test_no_type_definitions(self, tmp_path: Path) -> None:
        """型定義を含まないファイルは検出しない"""
        test_file = tmp_path / "utils.py"
        test_file.write_text(
            """
def process_data(data):
    return data.upper()

class Helper:
    def __init__(self):
        pass
"""
        )
        assert not _has_type_definitions(test_file)


class TestFindPythonFilesWithTypeDefinitions:
    """ディレクトリ内の型定義ファイル検索のテスト"""

    def test_find_files_in_directory(self, tmp_path: Path) -> None:
        """ディレクトリ内の型定義ファイルを検索"""
        # テストファイルを作成
        (tmp_path / "models.py").write_text(
            """
from pydantic import BaseModel

class User(BaseModel):
    id: int
"""
        )
        (tmp_path / "types.py").write_text(
            """
type UserId = str
"""
        )
        (tmp_path / "utils.py").write_text(
            """
def helper():
    pass
"""
        )

        # 検索実行
        files = find_python_files_with_type_definitions(tmp_path)

        # アサーション
        assert len(files) == 2
        assert any(f.name == "models.py" for f in files)
        assert any(f.name == "types.py" for f in files)
        assert not any(f.name == "utils.py" for f in files)

    def test_exclude_test_files(self, tmp_path: Path) -> None:
        """テストファイルを除外"""
        (tmp_path / "test_models.py").write_text(
            """
from pydantic import BaseModel

class User(BaseModel):
    id: int
"""
        )

        files = find_python_files_with_type_definitions(tmp_path)
        assert len(files) == 0

    def test_exclude_init_files(self, tmp_path: Path) -> None:
        """__init__.pyを除外"""
        (tmp_path / "__init__.py").write_text(
            """
from pydantic import BaseModel

class User(BaseModel):
    id: int
"""
        )

        files = find_python_files_with_type_definitions(tmp_path)
        assert len(files) == 0

    def test_recursive_search(self, tmp_path: Path) -> None:
        """再帰的にディレクトリを検索"""
        # サブディレクトリを作成
        subdir = tmp_path / "core" / "schemas"
        subdir.mkdir(parents=True)

        (subdir / "models.py").write_text(
            """
from pydantic import BaseModel

class User(BaseModel):
    id: int
"""
        )

        files = find_python_files_with_type_definitions(tmp_path)
        assert len(files) == 1
        assert files[0].name == "models.py"
        assert "core/schemas" in str(files[0])


class TestYamlCommandIntegration:
    """pylay yamlコマンドの統合テスト"""

    def test_single_file_conversion(self, tmp_path: Path) -> None:
        """単一ファイル変換"""
        # テストファイル作成
        input_file = tmp_path / "models.py"
        input_file.write_text(
            """
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
"""
        )

        # 出力ファイルパス
        output_file = tmp_path / "models.lay.yaml"

        # YAML変換実行
        run_yaml(str(input_file), str(output_file))

        # アサーション
        assert output_file.exists()
        content = output_file.read_text()
        assert "User" in content
        assert "_metadata" in content
        assert "pylay yaml" in content

    def test_directory_conversion(self, tmp_path: Path, monkeypatch) -> None:
        """ディレクトリ再帰変換"""
        # テスト用ディレクトリ構造作成
        (tmp_path / "core").mkdir()
        (tmp_path / "core" / "models.py").write_text(
            """
from pydantic import BaseModel

class User(BaseModel):
    id: int
"""
        )
        (tmp_path / "core" / "types.py").write_text(
            """
type UserId = str
"""
        )

        # 出力先ディレクトリ
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # pyproject.tomlを設定（モック）
        from src.core.schemas.pylay_config import OutputConfig

        config = PylayConfig(output_dir=str(output_dir))
        config.output = OutputConfig(yaml_output_dir=str(output_dir))
        monkeypatch.setattr(
            "src.cli.commands.yaml.PylayConfig.from_pyproject_toml",
            lambda: config,
        )

        # ディレクトリ変換実行
        run_yaml(str(tmp_path / "core"), None)

        # アサーション: ディレクトリ全体の型が schema.lay.yaml に集約される
        # 出力先は tmp_path/core の相対パスになるため、core/schema.lay.yamlが生成される
        assert (output_dir / "core" / "schema.lay.yaml").exists()

        # types.pyは型定義を含むが、BaseModelがないため変換されない
        # （現状の実装では_process_single_fileがBaseModel/Enumのみ対応）

    def test_pyproject_toml_conversion(self, tmp_path: Path, monkeypatch) -> None:
        """pyproject.toml使用パターン"""
        # テスト用ディレクトリ構造
        (tmp_path / "src" / "core").mkdir(parents=True)
        (tmp_path / "src" / "core" / "models.py").write_text(
            """
from pydantic import BaseModel

class User(BaseModel):
    id: int
"""
        )

        # 出力先
        output_dir = tmp_path / "docs" / "pylay"
        output_dir.mkdir(parents=True)

        # pyproject.toml設定をモック
        from src.core.schemas.pylay_config import OutputConfig

        config = PylayConfig(
            target_dirs=["src"],
            output_dir=str(output_dir),
        )
        config.output = OutputConfig(yaml_output_dir=str(output_dir))
        monkeypatch.setattr(
            "src.cli.commands.yaml.PylayConfig.from_pyproject_toml",
            lambda: config,
        )

        # 作業ディレクトリを変更
        monkeypatch.chdir(tmp_path)

        # 引数なしで実行
        run_yaml(None, None)

        # アサーション: 階層ごとに schema.lay.yaml が生成される（新仕様）
        # src/core/ にファイルがあるので、そこにschema.lay.yamlが生成される
        expected_output = output_dir / "src" / "core" / "schema.lay.yaml"
        assert expected_output.exists()


class TestDirectoryStructurePreservation:
    """ディレクトリ構造保持のテスト"""

    def test_preserves_directory_structure(self, tmp_path: Path, monkeypatch) -> None:
        """ディレクトリ構造が保持されることを確認"""
        # 複雑なディレクトリ構造を作成
        (tmp_path / "src" / "core" / "schemas").mkdir(parents=True)
        (tmp_path / "src" / "core" / "converters").mkdir(parents=True)

        (tmp_path / "src" / "core" / "schemas" / "models.py").write_text(
            """
from pydantic import BaseModel

class User(BaseModel):
    id: int
"""
        )

        (tmp_path / "src" / "core" / "converters" / "models.py").write_text(
            """
from pydantic import BaseModel

class Converter(BaseModel):
    name: str
"""
        )

        # 出力先
        output_dir = tmp_path / "docs" / "pylay"
        output_dir.mkdir(parents=True)

        # 設定をモック
        from src.core.schemas.pylay_config import OutputConfig

        config = PylayConfig(output_dir=str(output_dir))
        config.output = OutputConfig(yaml_output_dir=str(output_dir))
        monkeypatch.setattr(
            "src.cli.commands.yaml.PylayConfig.from_pyproject_toml",
            lambda: config,
        )
        monkeypatch.chdir(tmp_path)

        # ディレクトリ変換実行
        run_yaml(str(tmp_path / "src"), None)

        # アサーション: 階層ごとに schema.lay.yaml が生成される（新仕様）
        # 各ディレクトリ階層ごとに個別のschema.lay.yamlが生成される
        assert (output_dir / "src" / "core" / "schemas" / "schema.lay.yaml").exists()
        assert (output_dir / "src" / "core" / "converters" / "schema.lay.yaml").exists()

        # 個別のファイルごとのYAMLは生成されない
        assert not (output_dir / "src" / "core" / "schemas" / "models.lay.yaml").exists()
        assert not (output_dir / "src" / "core" / "converters" / "models.lay.yaml").exists()


class TestMetadataFunctions:
    """メタデータ関連機能のテスト"""

    def test_calculate_file_hash(self, tmp_path: Path) -> None:
        """ファイルハッシュ計算"""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        hash1 = _calculate_file_hash(test_file)

        # ハッシュは64文字の16進数文字列
        assert len(hash1) == 64
        assert all(c in "0123456789abcdef" for c in hash1)

        # 同じファイルは同じハッシュ
        hash2 = _calculate_file_hash(test_file)
        assert hash1 == hash2

        # ファイル変更でハッシュが変わる
        test_file.write_text("print('world')")
        hash3 = _calculate_file_hash(test_file)
        assert hash1 != hash3

    def test_validate_metadata_success(self, tmp_path: Path) -> None:
        """メタデータバリデーション成功"""
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        errors = _validate_metadata(str(test_file), "2025-10-08T12:00:00+00:00", "0.5.0")

        assert len(errors) == 0

    def test_validate_metadata_file_not_exists(self) -> None:
        """ソースファイルが存在しない場合のバリデーション"""
        errors = _validate_metadata("/nonexistent/file.py", "2025-10-08T12:00:00+00:00", "0.5.0")

        assert len(errors) == 1
        assert "does not exist" in errors[0]

    def test_validate_metadata_invalid_datetime(self, tmp_path: Path) -> None:
        """無効な日時形式のバリデーション"""
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        errors = _validate_metadata(str(test_file), "invalid-datetime", "0.5.0")

        assert len(errors) == 1
        assert "Invalid generated_at format" in errors[0]

    def test_validate_metadata_empty_version(self, tmp_path: Path) -> None:
        """空のバージョンのバリデーション"""
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        errors = _validate_metadata(str(test_file), "2025-10-08T12:00:00+00:00", "")

        assert len(errors) == 1
        assert "pylay_version is empty" in errors[0]

    def test_generate_metadata_section(self, tmp_path: Path) -> None:
        """メタデータセクション生成"""
        test_file = tmp_path / "test.py"
        test_file.write_text("from pydantic import BaseModel")

        metadata = _generate_metadata_section(str(test_file), validate=True)

        # 必須フィールドの存在確認
        assert "_metadata:" in metadata
        assert "generated_by: pylay yaml" in metadata
        # sourceは相対パスに変換されるため、完全一致チェックは避ける
        assert "source:" in metadata
        assert "source_hash:" in metadata
        assert "source_size:" in metadata
        assert "source_modified_at:" in metadata
        # generated_atは再現性向上のため削除済み
        # assert "generated_at:" in metadata
        assert "pylay_version:" in metadata

    def test_generate_metadata_section_validation_error(self) -> None:
        """バリデーションエラーが発生する場合"""
        import pytest

        with pytest.raises(ValueError, match="Metadata validation failed"):
            _generate_metadata_section("/nonexistent/file.py", validate=True)

    def test_yaml_output_contains_metadata(self, tmp_path: Path) -> None:
        """YAML出力にメタデータが含まれることを確認"""
        # テストファイル作成
        input_file = tmp_path / "models.py"
        input_file.write_text(
            """
from pydantic import BaseModel

class User(BaseModel):
    id: int
"""
        )

        # 出力ファイルパス
        output_file = tmp_path / "models.lay.yaml"

        # YAML変換実行
        run_yaml(str(input_file), str(output_file))

        # 出力ファイルを読み込んで確認
        content = output_file.read_text()

        # メタデータフィールドの存在確認
        assert "_metadata:" in content
        assert "source_hash:" in content
        assert "source_size:" in content
        assert "source_modified_at:" in content
        # generated_atは再現性向上のため削除済み
        # assert "generated_at:" in content
        assert "pylay_version:" in content
