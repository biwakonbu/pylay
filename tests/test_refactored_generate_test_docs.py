"""
Improved tests for refactored test documentation generator.

Tests the new modular architecture with proper dependency injection and mocking.
"""

from pathlib import Path

import pytest

from doc_generators.config import CatalogConfig
from doc_generators.filesystem import InMemoryFileSystem
from doc_generators.markdown_builder import MarkdownBuilder
from doc_generators.test_catalog_generator import CatalogGenerator


class TestCatalogGenerator:
    """リファクタリングされたCatalogGeneratorクラスのテスト

    CatalogGeneratorクラスのリファクタリング版が正しく動作することを確認します。
    """

    def setup_method(self):
        """テストフィクスチャをセットアップ

テストに必要な共通の設定やオブジェクトを準備します。
"""
        self.filesystem = InMemoryFileSystem()
        self.output_path = Path("/test/output/catalog.md")
        self.config = CatalogConfig(
            test_directory=Path("tests"),
            output_path=self.output_path,
        )

    def test_generator_initialization(self):
        """生成器が正しく初期化されることをテスト

        CatalogGeneratorが適切に初期化され、必要な属性が設定されることを確認します。
        """
        generator = CatalogGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        assert generator.config == self.config
        assert generator.fs == self.filesystem
        assert isinstance(generator.md, MarkdownBuilder)

    def test_generate_creates_output_file(self):
        """Test that generate() creates output file."""
        generator = CatalogGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        generator.generate()

        assert self.filesystem.exists(self.output_path)
        content = self.filesystem.get_content(self.output_path)
        assert "# テストカタログ" in content

    def test_generate_includes_timestamp(self):
        """Test that generated document includes timestamp."""
        generator = CatalogGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        generator.generate()

        content = self.filesystem.get_content(self.output_path)
        assert "**生成日**:" in content
        # Check ISO format timestamp
        lines = content.split("\n")
        timestamp_line = next(line for line in lines if "**生成日**:" in line)
        assert "T" in timestamp_line  # ISO format includes T

    def test_generate_handles_test_classes(self):
        """Test that generator correctly handles test classes and methods."""
        generator = CatalogGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        generator.generate()

        content = self.filesystem.get_content(self.output_path)

        # Should find test classes and methods
        assert "TestGenerateTestDocs" in content
        assert "test_generate_test_docs_with_valid_files" in content
        assert (
            "pytest tests/test_generate_test_docs.py::TestGenerateTestDocs" in content
        )

    def test_generate_with_custom_output_path(self):
        """Test generation with custom output path override."""
        custom_path = Path("/custom/output.md")
        generator = CatalogGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        generator.generate(output_path=custom_path)

        assert self.filesystem.exists(custom_path)
        assert not self.filesystem.exists(self.output_path)

    def test_scan_test_modules_filters_correctly(self):
        """Test that module scanning respects include/exclude patterns."""
        config = CatalogConfig(
            test_directory=Path("tests"),
            include_patterns=["test_*.py"],
            exclude_patterns=["__pycache__", "*.pyc"],
        )
        generator = CatalogGenerator(
            config=config,
            filesystem=self.filesystem,
        )

        test_files = generator._scan_test_modules()

        # Should find test files
        assert len(test_files) > 0
        assert all(f.name.startswith("test_") for f in test_files)
        assert all(f.suffix == ".py" for f in test_files)

    def test_extract_test_functions_finds_methods(self):
        """Test that function extraction finds both functions and class methods."""
        import tests.test_generate_test_docs

        generator = CatalogGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        test_functions = generator._extract_test_functions(
            tests.test_generate_test_docs
        )

        # Should find test methods from test classes
        assert len(test_functions) > 0

        function_names = [name for name, _ in test_functions]
        # Check that we have test functions (some may be class methods, some may be standalone)
        assert len(function_names) >= 4  # At least the 4 test methods we saw

        # Should include class.method format
        assert any("TestGenerateTestDocs." in name for name in function_names)

    def test_import_module_handles_errors_gracefully(self):
        """Test that module import errors are handled gracefully."""
        # Create a config with non-existent directory
        config = CatalogConfig(
            test_directory=Path("nonexistent/directory"),
        )
        generator = CatalogGenerator(
            config=config,
            filesystem=self.filesystem,
        )

        # Should not raise exception
        generator.generate()

        content = self.filesystem.get_content(config.output_path)
        assert "# テストカタログ" in content
        # Should have summary even with no modules
        assert "**総テストモジュール数**: 0" in content

    def test_count_test_modules_accurate(self):
        """Test that module counting is accurate."""
        generator = CatalogGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        count = generator._count_test_modules()

        # Should count actual test modules in tests/scripts
        assert (
            count >= 2
        )  # At least test_generate_test_docs and test_generate_type_docs

    def test_format_generation_footer(self):
        """Test generation footer formatting."""
        generator = CatalogGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        footer = generator._format_generation_footer("Additional info")

        assert "**生成日**:" in footer
        assert "Additional info" in footer


class TestCatalogGeneratorErrorHandling:
    """Test error handling in CatalogGenerator."""

    def setup_method(self):
        """テストフィクスチャをセットアップ

テストに必要な共通の設定やオブジェクトを準備します。
"""
        self.filesystem = InMemoryFileSystem()
        self.config = CatalogConfig(
            test_directory=Path("tests"),
            output_path=Path("/test/catalog.md"),
        )

    def test_handles_module_import_errors(self):
        """Test graceful handling of module import errors."""
        generator = CatalogGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        # Mock _import_module to raise ImportError
        original_import = generator._import_module

        def mock_import(test_file):
            if "failing" in str(test_file):
                raise ImportError("Mock import error")
            return original_import(test_file)

        generator._import_module = mock_import

        # Should not raise exception
        generator.generate()

        content = self.filesystem.get_content(self.config.output_path)
        assert "# テストカタログ" in content

    def test_handles_recursion_errors(self):
        """Test graceful handling of recursion errors."""
        generator = CatalogGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        # Mock _import_module to raise RecursionError
        def mock_import(test_file):
            raise RecursionError("Mock recursion error")

        generator._import_module = mock_import

        # Should not raise exception
        generator.generate()

        content = self.filesystem.get_content(self.config.output_path)
        assert "# テストカタログ" in content
        # Should include error message
        assert "⚠️ モジュールの処理に失敗" in content


class TestMarkdownBuilder:
    """Test the MarkdownBuilder utility class."""

    def setup_method(self):
        """テストフィクスチャをセットアップ

テストに必要な共通の設定やオブジェクトを準備します。
"""
        self.md = MarkdownBuilder()

    def test_heading_generation(self):
        """Test heading generation with different levels."""
        result = self.md.heading(1, "Title").build()
        assert result == "# Title\n"

        self.md.clear()
        result = self.md.heading(3, "Subtitle").build()
        assert result == "### Subtitle\n"

    def test_invalid_heading_level(self):
        """Test that invalid heading levels raise error."""
        with pytest.raises(ValueError, match="Heading level must be 1-6"):
            self.md.heading(0, "Invalid")

        with pytest.raises(ValueError, match="Heading level must be 1-6"):
            self.md.heading(7, "Invalid")

    def test_paragraph_and_line_break(self):
        """Test paragraph and line break generation."""
        result = (
            self.md.paragraph("First paragraph")
            .line_break()
            .paragraph("Second paragraph")
            .build()
        )

        expected = "First paragraph\n\nSecond paragraph\n"
        assert result == expected

    def test_code_block(self):
        """Test code block generation."""
        result = self.md.code_block("python", "print('hello')").build()
        expected = "```python\nprint('hello')\n```\n"
        assert result == expected

    def test_bullet_points(self):
        """Test bullet point generation."""
        result = self.md.bullet_point("Item 1").bullet_point("Item 2", level=2).build()

        expected = "- Item 1\n  - Item 2\n"
        assert result == expected

    def test_formatting_helpers(self):
        """Test text formatting helpers."""
        assert self.md.bold("text") == "**text**"
        assert self.md.italic("text") == "*text*"
        assert self.md.link("text", "url") == "[text](url)"

    def test_table_generation(self):
        """Test table generation."""
        result = (
            self.md.table_header(["Col1", "Col2"]).table_row(["Data1", "Data2"]).build()
        )

        expected = "| Col1 | Col2 |\n| --- | --- |\n| Data1 | Data2 |\n"
        assert result == expected

    def test_fluent_api_chaining(self):
        """Test that all methods return self for chaining."""
        result = (
            self.md.heading(1, "Title")
            .paragraph("Content")
            .bullet_point("Item")
            .line_break()
            .horizontal_rule()
        )

        assert result is self.md
        content = result.build()
        assert "# Title" in content
        assert "Content" in content
        assert "- Item" in content
        assert "---" in content

    def test_clear_functionality(self):
        """Test that clear() empties the content."""
        self.md.heading(1, "Title").paragraph("Content")
        assert len(self.md.build()) > 0

        self.md.clear()
        assert self.md.build() == ""


class TestInMemoryFileSystem:
    """Test the InMemoryFileSystem utility class."""

    def setup_method(self):
        """テストフィクスチャをセットアップ

テストに必要な共通の設定やオブジェクトを準備します。
"""
        self.fs = InMemoryFileSystem()

    def test_write_and_read_file(self):
        """Test writing and reading files."""
        path = Path("/test/file.txt")
        content = "Test content"

        self.fs.write_text(path, content)

        assert self.fs.exists(path)
        assert self.fs.get_content(path) == content

    def test_mkdir_creates_directories(self):
        """Test directory creation."""
        path = Path("/test/deep/directory")

        self.fs.mkdir(path)

        assert self.fs.exists(path)

    def test_write_creates_parent_directories(self):
        """Test that writing files creates parent directories."""
        path = Path("/deep/nested/file.txt")

        self.fs.write_text(path, "content")

        assert self.fs.exists(path.parent)
        assert self.fs.exists(path)

    def test_list_files(self):
        """Test listing files."""
        files = [
            Path("/file1.txt"),
            Path("/dir/file2.txt"),
            Path("/dir/subdir/file3.txt"),
        ]

        for file_path in files:
            self.fs.write_text(file_path, "content")

        listed_files = self.fs.list_files()
        assert len(listed_files) == len(files)
        assert all(f in listed_files for f in files)

    def test_file_not_found_error(self):
        """Test FileNotFoundError for non-existent files."""
        with pytest.raises(FileNotFoundError):
            self.fs.get_content(Path("/nonexistent.txt"))
