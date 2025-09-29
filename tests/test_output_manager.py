"""
OutputPathManager のテスト

出力パス生成の統一的な仕組みをテストします。
"""

import tempfile
from pathlib import Path

import pytest

from src.core.schemas.pylay_config import PylayConfig
from src.core.output_manager import OutputPathManager


class TestOutputPathManager:
    """OutputPathManager のテスト

    OutputPathManagerクラスの機能が正しく動作することを確認します。
    """

    def test_yaml_path_generation(self):
        """YAML パス生成のテスト

        YAMLファイルのパスが正しく生成されることを確認します。
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 設定ファイルを作成
            pyproject_content = """
[tool.pylay]
target_dirs = ["src/"]
output_dir = "docs/"
generate_markdown = true
"""
            (temp_path / "pyproject.toml").write_text(pyproject_content)

            # テストファイル構造
            src_dir = temp_path / "src"
            src_dir.mkdir()
            test_file = src_dir / "cli" / "main.py"
            test_file.parent.mkdir(parents=True)
            test_file.write_text("# Test file")

            config = PylayConfig.from_pyproject_toml(temp_path)
            manager = OutputPathManager(config, temp_path)

            yaml_path = manager.get_yaml_path(test_file)

            # パスが正しく生成されることを確認
            expected_path = temp_path / "docs" / "src" / "cli" / "main.types.yaml"
            assert yaml_path == expected_path
            assert yaml_path.parent.exists()

    def test_markdown_path_generation(self):
        """Markdown パス生成のテスト

        Markdownファイルのパスが正しく生成されることを確認します。
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 設定ファイルを作成
            pyproject_content = """
[tool.pylay]
target_dirs = ["src/"]
output_dir = "docs/"
generate_markdown = true
"""
            (temp_path / "pyproject.toml").write_text(pyproject_content)

            config = PylayConfig.from_pyproject_toml(temp_path)
            manager = OutputPathManager(config, temp_path)

            # ファイル別生成
            test_file = temp_path / "src" / "main.py"
            md_path = manager.get_markdown_path(source_file=test_file)

            expected_path = temp_path / "docs" / "documents" / "src" / "main_docs.md"
            assert md_path == expected_path

            # 固定ファイル名生成
            md_path_fixed = manager.get_markdown_path(filename="index.md")
            expected_fixed = temp_path / "docs" / "documents" / "index.md"
            assert md_path_fixed == expected_fixed

    def test_dependency_graph_path_generation(self):
        """依存関係グラフ パス生成のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # pyproject.toml を作成
            pyproject_content = """
[tool.pylay]
target_dirs = ["src/"]
output_dir = "docs/"
generate_markdown = true
"""
            (temp_path / "pyproject.toml").write_text(pyproject_content)

            config = PylayConfig.from_pyproject_toml(temp_path)
            manager = OutputPathManager(config, temp_path)

            graph_path = manager.get_dependency_graph_path("test.png")

            expected_path = temp_path / "docs" / "test.png"
            assert graph_path == expected_path

    def test_output_structure(self):
        """出力構造のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # pyproject.toml を作成
            pyproject_content = """
[tool.pylay]
target_dirs = ["src/"]
output_dir = "docs/"
generate_markdown = true
"""
            (temp_path / "pyproject.toml").write_text(pyproject_content)

            config = PylayConfig.from_pyproject_toml(temp_path)
            manager = OutputPathManager(config, temp_path)

            structure = manager.get_output_structure()

            assert "yaml" in structure
            assert "markdown" in structure
            assert "graph" in structure

            # パスが正しいことを確認
            assert structure["yaml"] == temp_path / "docs"
            assert structure["markdown"] == temp_path / "docs" / "documents"

    def test_error_handling(self):
        """エラーハンドリングのテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # pyproject.toml を作成
            pyproject_content = """
[tool.pylay]
target_dirs = ["src/"]
output_dir = "docs/"
generate_markdown = true
"""
            (temp_path / "pyproject.toml").write_text(pyproject_content)

            config = PylayConfig.from_pyproject_toml(temp_path)
            manager = OutputPathManager(config, temp_path)

            # source_file と filename の両方が None の場合
            with pytest.raises(
                ValueError,
                match="source_file または filename のいずれかを指定してください",
            ):
                manager.get_markdown_path()

    def test_config_not_found_fallback(self):
        """設定ファイルがない場合のフォールバックテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # pyproject.toml がない場合
            config = PylayConfig()
            manager = OutputPathManager(config, temp_path)

            # デフォルトパスが使用される
            yaml_path = manager.get_yaml_path(temp_path / "test.py")
            assert "docs" in str(yaml_path)

            md_path = manager.get_markdown_path(filename="test.md")
            assert "docs" in str(md_path)
