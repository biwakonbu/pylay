"""
.lay.py / .lay.yaml ファイル生成のテスト

Issue #51: クリーン再生成、警告ヘッダー、拡張子の検証
"""

from pathlib import Path

import pytest


class TestLayPyGeneration:
    """.lay.py ファイル生成のテスト"""

    def test_lay_py_file_has_warning_header(self, tmp_path: Path) -> None:
        """生成された.lay.pyファイルに警告ヘッダーが含まれることを確認"""
        from src.cli.commands.types import run_types

        # テスト用YAMLファイルを作成
        yaml_content = """
User:
  type: dict
  description: User型
  properties:
    name:
      type: str
      required: true
    age:
      type: int
      required: true
"""
        yaml_file = tmp_path / "test.lay.yaml"
        yaml_file.write_text(yaml_content)

        # .lay.py生成
        output_file = tmp_path / "test.lay.py"
        run_types(str(yaml_file), str(output_file))

        # 生成されたファイルを確認
        content = output_file.read_text()
        assert "pylay自動生成ファイル" in content
        assert "このファイルを直接編集しないでください" in content
        assert "次回の pylay types 実行時に削除・再生成されます" in content

    def test_lay_py_file_has_source_path(self, tmp_path: Path) -> None:
        """生成された.lay.pyファイルにソースパスが記録されることを確認"""
        from src.cli.commands.types import run_types

        yaml_content = """
User:
  type: dict
  properties:
    name:
      type: str
"""
        yaml_file = tmp_path / "source.lay.yaml"
        yaml_file.write_text(yaml_content)

        output_file = tmp_path / "output.lay.py"
        run_types(str(yaml_file), str(output_file))

        content = output_file.read_text()
        assert "Source:" in content
        assert "source.lay.yaml" in content

    def test_lay_py_extension_is_enforced(self, tmp_path: Path) -> None:
        """.lay.py拡張子が自動付与されることを確認"""
        from src.cli.commands.types import run_types

        yaml_content = """
User:
  type: dict
  properties:
    name:
      type: str
"""
        yaml_file = tmp_path / "test.lay.yaml"
        yaml_file.write_text(yaml_content)

        # 拡張子なしで指定
        output_file_base = tmp_path / "output"
        run_types(str(yaml_file), str(output_file_base))

        # .lay.pyが自動付与されることを期待
        expected_file = tmp_path / "output.lay.py"
        assert expected_file.exists()

    def test_clean_regeneration_removes_old_lay_py_files(self, tmp_path: Path) -> None:
        """再生成時に古い.lay.pyファイルが削除されることを確認"""

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # 既存の.lay.pyファイルを作成
        old_file1 = output_dir / "old1.lay.py"
        old_file2 = output_dir / "old2.lay.py"
        old_file1.write_text("# old content 1")
        old_file2.write_text("# old content 2")

        # 新しいYAMLから生成（old1とold2は含まれない）
        yaml_content = """
NewType:
  type: dict
  properties:
    field:
      type: str
"""
        yaml_file = tmp_path / "test.lay.yaml"
        yaml_file.write_text(yaml_content)

        # ディレクトリ指定で生成（クリーン再生成）
        # Note: この機能は後で実装するため、現時点ではスキップ
        pytest.skip("クリーン再生成機能は未実装")

    def test_manual_files_are_not_deleted(self, tmp_path: Path) -> None:
        """手動実装ファイル(.lay.py以外)が削除されないことを確認"""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # 手動実装ファイルを作成
        manual_file1 = output_dir / "models.py"
        manual_file2 = output_dir / "api.py"
        manual_file1.write_text("# manual implementation 1")
        manual_file2.write_text("# manual implementation 2")

        # Note: クリーン再生成機能は後で実装
        pytest.skip("クリーン再生成機能は未実装")


class TestLayYamlGeneration:
    """.lay.yaml ファイル生成のテスト"""

    def test_lay_yaml_file_has_warning_header(self, tmp_path: Path) -> None:
        """生成された.lay.yamlファイルに警告ヘッダーが含まれることを確認"""
        from src.cli.commands.yaml import run_yaml

        # テスト用Pythonファイルを作成
        py_content = '''
from pydantic import BaseModel

class User(BaseModel):
    """ユーザー型"""
    name: str
    age: int
'''
        py_file = tmp_path / "test_types.py"
        py_file.write_text(py_content)

        # .lay.yaml生成
        output_file = tmp_path / "test.lay.yaml"
        run_yaml(str(py_file), str(output_file))

        # 生成されたファイルを確認
        content = output_file.read_text()
        assert "pylay自動生成ファイル" in content
        assert "このファイルを直接編集しないでください" in content
        assert "次回の pylay yaml 実行時に削除・再生成されます" in content

    def test_lay_yaml_file_has_metadata(self, tmp_path: Path) -> None:
        """生成された.lay.yamlファイルに_metadataセクションが含まれることを確認"""
        pytest.skip(".lay.yaml生成機能は未実装")

    def test_lay_yaml_extension_is_enforced(self, tmp_path: Path) -> None:
        """.lay.yaml拡張子が自動付与されることを確認"""
        from src.cli.commands.yaml import run_yaml

        # テスト用Pythonファイルを作成
        py_content = """
from pydantic import BaseModel

class Product(BaseModel):
    name: str
    price: float
"""
        py_file = tmp_path / "test_product.py"
        py_file.write_text(py_content)

        # 拡張子なしで指定
        output_file_base = tmp_path / "output"
        run_yaml(str(py_file), str(output_file_base))

        # .lay.yamlが自動付与されることを期待
        expected_file = tmp_path / "output.lay.yaml"
        assert expected_file.exists()

    def test_package_structure_mirroring(self, tmp_path: Path) -> None:
        """パッケージ構造がdocs/pylay/配下にミラーリングされることを確認"""
        pytest.skip("パッケージ構造ミラーリング機能は未実装")


class TestConfigIntegration:
    """PylayConfigとの統合テスト"""

    def test_generation_config_is_used(self, tmp_path: Path) -> None:
        """PylayConfigのgeneration設定が使用されることを確認"""
        pytest.skip("設定統合は未実装")

    def test_output_config_is_used(self, tmp_path: Path) -> None:
        """PylayConfigのoutput設定が使用されることを確認"""
        pytest.skip("設定統合は未実装")
