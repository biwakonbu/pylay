"""
Comprehensive tests for refactored type documentation generator.

Tests the new modular architecture with TypeInspector, LayerDocGenerator,
and IndexDocGenerator components.
"""

from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from src.core.doc_generators.config import TypeDocConfig
from src.core.doc_generators.filesystem import InMemoryFileSystem
from src.core.doc_generators.markdown_builder import MarkdownBuilder
from src.core.doc_generators.type_doc_generator import (
    IndexDocGenerator,
    LayerDocGenerator,
)
from src.core.doc_generators.type_inspector import TypeInspector


# Test fixtures
class MockPydanticModel(BaseModel):
    """Mock Pydantic model for testing."""

    name: str
    value: int


class TestTypeInspector:
    """Test the TypeInspector utility class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.inspector = TypeInspector()

    def test_initialization_with_default_skip_types(self) -> None:
        """Test that TypeInspector initializes with default skip types."""
        assert self.inspector.skip_types == set()

    def test_initialization_with_custom_skip_types(self) -> None:
        """Test initialization with custom skip types."""
        custom_skip = {"CustomType", "IgnoreMe"}
        inspector = TypeInspector(skip_types=custom_skip)
        assert inspector.skip_types == custom_skip

    def test_get_docstring_from_class(self) -> None:
        """Test extracting docstring from a class."""

        class TestClass:
            """This is a test docstring."""

        docstring = self.inspector.get_docstring(TestClass)
        assert docstring == "This is a test docstring."

    def test_get_docstring_from_class_without_docstring(self) -> None:
        """Test extracting docstring from class without docstring."""

        class TestClass:
            pass

        docstring = self.inspector.get_docstring(TestClass)
        assert docstring is None

    def test_extract_code_blocks_with_markdown(self) -> None:
        """Test extracting code blocks from docstring with markdown."""
        docstring = """
        This is a description.

        ```python
        print("hello")
        x = 1 + 2
        ```

        More description.

        ```javascript
        console.log("world");
        ```
        """

        description_lines, code_blocks = self.inspector.extract_code_blocks(docstring)

        assert "This is a description." in description_lines
        assert "More description." in description_lines
        assert len(code_blocks) == 2
        assert 'print("hello")' in code_blocks[0]
        assert 'console.log("world");' in code_blocks[1]

    def test_extract_code_blocks_without_markdown(self):
        """Test extracting from docstring without code blocks."""
        docstring = "Simple description without code."

        description_lines, code_blocks = self.inspector.extract_code_blocks(docstring)

        assert description_lines == ["Simple description without code."]
        assert code_blocks == []

    def test_is_pydantic_model_with_pydantic_class(self):
        """Test Pydantic model detection with actual Pydantic class."""
        assert self.inspector.is_pydantic_model(MockPydanticModel) is True

    def test_is_pydantic_model_with_regular_class(self):
        """Test Pydantic model detection with regular class."""

        class RegularClass:
            pass

        assert self.inspector.is_pydantic_model(RegularClass) is False

    def test_get_pydantic_schema(self):
        """Test getting Pydantic JSON schema."""
        schema = self.inspector.get_pydantic_schema(MockPydanticModel)

        assert schema is not None
        assert "properties" in schema
        assert "name" in schema["properties"]
        assert "value" in schema["properties"]

    def test_get_pydantic_schema_with_non_pydantic(self):
        """Test getting schema from non-Pydantic class."""

        class RegularClass:
            pass

        schema = self.inspector.get_pydantic_schema(RegularClass)
        assert schema is None

    def test_should_skip_type(self):
        """Test type skipping logic."""
        assert self.inspector.should_skip_type("CustomType") is False
        custom_inspector = TypeInspector(skip_types={"SkipMe"})
        assert custom_inspector.should_skip_type("SkipMe") is True

    def test_format_type_definition_with_pydantic(self):
        """Test formatting Pydantic type definition."""
        definition = self.inspector.format_type_definition("MockModel", MockPydanticModel)

        assert "```json" in definition
        assert "properties" in definition
        assert "name" in definition

    def test_format_type_definition_fallback(self):
        """Test formatting with fallback for unknown types."""

        class UnknownType:
            pass

        definition = self.inspector.format_type_definition("Unknown", UnknownType)

        assert "```python" in definition
        assert "Unknown" in definition


class TestLayerDocGenerator:
    """Test the LayerDocGenerator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.filesystem = InMemoryFileSystem()
        self.output_path = Path("/test/output/layer.md")
        self.config = TypeDocConfig(
            output_path=Path("/test/output"),
        )

    def test_generator_initialization(self):
        """Test generator initializes correctly."""
        generator = LayerDocGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        assert generator.config == self.config
        assert generator.fs == self.filesystem
        assert isinstance(generator.md, MarkdownBuilder)
        assert isinstance(generator.inspector, TypeInspector)

    def test_generate_creates_output_file(self):
        """Test that generate() creates output file."""
        generator = LayerDocGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        layer = "test_layer"
        types = {"TestType": str}

        generator.generate(layer, types, self.output_path)

        assert self.filesystem.exists(self.output_path)
        content = self.filesystem.get_content(self.output_path)
        assert "TEST_LAYER レイヤー型カタログ" in content

    def test_generate_includes_auto_growth_section(self):
        """Test that generated document includes auto-growth explanation."""
        generator = LayerDocGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        layer = "primitives"
        types = {"UserId": str}

        generator.generate(layer, types, self.output_path)

        content = self.filesystem.get_content(self.output_path)
        assert "🎯 完全自動成長について" in content
        assert "TypeFactory.get_auto" in content

    def test_generate_with_pydantic_types(self):
        """Test generation with Pydantic model types."""
        generator = LayerDocGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        layer = "domain"
        types = {"MockModel": MockPydanticModel}

        generator.generate(layer, types, self.output_path)

        content = self.filesystem.get_content(self.output_path)
        assert "MockModel" in content
        assert "型定義（JSONSchema）" in content
        assert "properties" in content

    def test_generate_with_custom_output_path(self):
        """Test generation with custom output path override."""
        custom_path = Path("/custom/output.md")
        generator = LayerDocGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        layer = "test"
        types = {"TestType": str}

        generator.generate(layer, types, custom_path)

        assert self.filesystem.exists(custom_path)
        assert not self.filesystem.exists(self.output_path)

    def test_generate_skips_configured_types(self):
        """Test that generation skips types in skip_types configuration."""
        config = TypeDocConfig(
            output_path=Path("/test/output"),
            skip_types={"SkipMe"},
        )
        generator = LayerDocGenerator(
            config=config,
            filesystem=self.filesystem,
        )

        layer = "test"
        types = {"KeepMe": str, "SkipMe": int}

        generator.generate(layer, types, self.output_path)

        content = self.filesystem.get_content(self.output_path)
        assert "KeepMe" in content
        assert "SkipMe" not in content

    def test_generate_layer_specific_usage(self):
        """Test that layer-specific usage examples are included."""
        generator = LayerDocGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        layer = "primitives"
        types = {"UserId": str}

        generator.generate(layer, types, self.output_path)

        content = self.filesystem.get_content(self.output_path)
        assert "利用方法（完全自動成長）" in content
        assert "UserId" in content
        assert "TypeFactory.get_auto" in content

    def test_generate_includes_footer(self):
        """Test that generated document includes footer."""
        generator = LayerDocGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        layer = "test"
        types = {"TestType": str}

        generator.generate(layer, types, self.output_path)

        content = self.filesystem.get_content(self.output_path)
        assert "**生成日**:" in content


class TestIndexDocGenerator:
    """Test the IndexDocGenerator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.filesystem = InMemoryFileSystem()
        self.output_path = Path("/test/output/index.md")
        self.config = TypeDocConfig(
            output_path=Path("/test/output"),
        )

    def test_generator_initialization(self):
        """Test generator initializes correctly."""
        generator = IndexDocGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        assert generator.config == self.config
        assert generator.fs == self.filesystem
        assert isinstance(generator.md, MarkdownBuilder)

    def test_generate_creates_output_file(self):
        """Test that generate() creates output file."""
        generator = IndexDocGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        type_registry = {
            "primitives": {"UserId": str, "Email": str},
            "domain": {"User": MockPydanticModel},
        }

        generator.generate(type_registry, self.output_path)

        assert self.filesystem.exists(self.output_path)
        content = self.filesystem.get_content(self.output_path)
        assert "型インデックス（完全自動成長対応）" in content

    def test_generate_includes_unified_usage_section(self):
        """Test that generated index includes unified usage section."""
        generator = IndexDocGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        type_registry = {"primitives": {"UserId": str}}

        generator.generate(type_registry, self.output_path)

        content = self.filesystem.get_content(self.output_path)
        assert "🚀 統一的な型取得方法" in content
        assert "TypeFactory.get_auto" in content
        assert "UserIdType" in content

    def test_generate_includes_layer_sections(self):
        """Test that generated index includes layer detail sections."""
        generator = IndexDocGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        type_registry = {
            "primitives": {"UserId": str, "Email": str},
            "domain": {"User": MockPydanticModel, "Order": str},
        }

        generator.generate(type_registry, self.output_path)

        content = self.filesystem.get_content(self.output_path)
        assert "📁 レイヤー別詳細" in content
        assert "PRIMITIVES レイヤー" in content
        assert "DOMAIN レイヤー" in content
        assert "**型数**: 2" in content  # Each layer has 2 types

    def test_generate_includes_statistics(self):
        """Test that generated index includes statistics section."""
        generator = IndexDocGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        type_registry = {
            "primitives": {"UserId": str, "Email": str},
            "domain": {"User": MockPydanticModel},
        }

        generator.generate(type_registry, self.output_path)

        content = self.filesystem.get_content(self.output_path)
        assert "📊 統計情報" in content
        assert "**総型数**: 3" in content  # 2 + 1 = 3 total types

    def test_generate_with_custom_output_path(self):
        """Test generation with custom output path override."""
        custom_path = Path("/custom/index.md")
        generator = IndexDocGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        type_registry = {"primitives": {"UserId": str}}

        generator.generate(type_registry, custom_path)

        assert self.filesystem.exists(custom_path)
        assert not self.filesystem.exists(self.output_path)

    def test_generate_layer_links(self):
        """Test that layer sections include links to detailed documentation."""
        generator = IndexDocGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        type_registry = {"primitives": {"UserId": str}}

        generator.generate(type_registry, self.output_path)

        content = self.filesystem.get_content(self.output_path)
        assert "types/primitives.md" in content
        assert "詳細を見る" in content

    def test_generate_type_preview(self):
        """Test that layer sections show preview of main types."""
        generator = IndexDocGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        type_registry = {
            "primitives": {
                "Type1": str,
                "Type2": str,
                "Type3": str,
                "Type4": str,
                "Type5": str,
                "Type6": str,
            },
        }

        generator.generate(type_registry, self.output_path)

        content = self.filesystem.get_content(self.output_path)
        assert "**主な型**: Type1, Type2, Type3, Type4, Type5" in content
        assert "**他**: +1 型" in content  # 6 total, showing first 5

    def test_generate_includes_footer(self):
        """Test that generated index includes footer."""
        generator = IndexDocGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        type_registry = {"primitives": {"UserId": str}}

        generator.generate(type_registry, self.output_path)

        content = self.filesystem.get_content(self.output_path)
        assert "**生成日**:" in content


class TestGeneratorErrorHandling:
    """Test error handling in generators."""

    def setup_method(self):
        """Set up test fixtures."""
        self.filesystem = InMemoryFileSystem()
        self.config = TypeDocConfig()

    def test_layer_generator_handles_missing_docstring(self):
        """Test LayerDocGenerator handles types without docstrings."""
        generator = LayerDocGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        class NoDocstringType:
            pass

        layer = "test"
        types = {"NoDocType": NoDocstringType}
        output_path = Path("/test/output.md")

        # Should not raise exception
        generator.generate(layer, types, output_path)

        content = self.filesystem.get_content(output_path)
        assert "NoDocType" in content
        assert "NoDocType 型の定義" in content

    def test_layer_generator_handles_pydantic_schema_errors(self):
        """Test LayerDocGenerator handles Pydantic schema generation errors."""
        generator = LayerDocGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        # Mock a Pydantic-like class that fails schema generation
        class FaultyPydanticModel:
            @classmethod
            def model_json_schema(cls):
                raise ValueError("Schema generation failed")

        # Override inspector to identify as Pydantic model
        def mock_is_pydantic(type_cls):
            return type_cls is FaultyPydanticModel

        generator.inspector.is_pydantic_model = mock_is_pydantic

        layer = "test"
        types = {"FaultyModel": FaultyPydanticModel}
        output_path = Path("/test/output.md")

        # Should not raise exception
        generator.generate(layer, types, output_path)

        content = self.filesystem.get_content(output_path)
        assert "FaultyModel" in content

    def test_index_generator_handles_empty_registry(self):
        """Test IndexDocGenerator handles empty type registry."""
        generator = IndexDocGenerator(
            config=self.config,
            filesystem=self.filesystem,
        )

        type_registry: dict[str, dict[str, type[Any]]] = {}
        output_path = Path("/test/output.md")

        # Should not raise exception
        generator.generate(type_registry, output_path)

        content = self.filesystem.get_content(output_path)
        assert "型インデックス" in content
        assert "**総型数**: 0" in content


class TestConfigurationIntegration:
    """Test configuration integration with generators."""

    def test_layer_generator_uses_config_skip_types(self):
        """Test LayerDocGenerator respects skip_types configuration."""
        config = TypeDocConfig(
            skip_types={"SkipThis", "AndThis"},
        )
        filesystem = InMemoryFileSystem()
        generator = LayerDocGenerator(
            config=config,
            filesystem=filesystem,
        )

        layer = "test"
        types = {"KeepThis": str, "SkipThis": int, "AndThis": float}
        output_path = Path("/test/output.md")

        generator.generate(layer, types, output_path)

        content = filesystem.get_content(output_path)
        assert "KeepThis" in content
        assert "SkipThis" not in content
        assert "AndThis" not in content

    def test_layer_generator_uses_config_descriptions(self):
        """Test LayerDocGenerator uses custom type descriptions."""
        config = TypeDocConfig(
            type_alias_descriptions={
                "CustomType": "This is a custom description for testing",
            },
        )
        filesystem = InMemoryFileSystem()
        generator = LayerDocGenerator(
            config=config,
            filesystem=filesystem,
        )

        layer = "test"
        types = {"CustomType": str}
        output_path = Path("/test/output.md")

        generator.generate(layer, types, output_path)

        content = filesystem.get_content(output_path)
        assert "CustomType" in content
        assert "This is a custom description for testing" in content

    def test_generators_use_config_output_directory(self):
        """Test generators respect output directory configuration."""
        config = TypeDocConfig(
            output_path=Path("/custom/output/dir"),
        )
        filesystem = InMemoryFileSystem()

        layer_generator = LayerDocGenerator(
            config=config,
            filesystem=filesystem,
        )

        index_generator = IndexDocGenerator(
            config=config,
            filesystem=filesystem,
        )

        # Test layer generator default path
        layer = "test"
        types = {"TestType": str}
        layer_generator.generate(layer, types)

        expected_layer_path = Path("/custom/output/dir/test.md")
        assert filesystem.exists(expected_layer_path)

        # Test index generator default path
        type_registry = {"test": types}
        index_generator.generate(type_registry)

        expected_index_path = Path("/custom/output/dir/README.md")
        assert filesystem.exists(expected_index_path)


class TestTypeDocConfigBackwardCompatibility:
    """Test backward compatibility alias behavior for TypeDocConfig."""

    def test_output_directory_property_deprecation_warning(self) -> None:
        """Test that accessing output_directory property issues deprecation warning."""
        config = TypeDocConfig(output_path=Path("/test/output"))

        # Test getter issues deprecation warning
        with pytest.warns(DeprecationWarning, match="output_directoryは非推奨です。output_pathを使用してください。"):
            directory = config.output_directory
            assert directory == Path("/test/output")

    def test_output_directory_setter_deprecation_warning(self) -> None:
        """Test that setting output_directory property issues deprecation warning."""
        config = TypeDocConfig(output_path=Path("/test/output"))

        # Test setter issues deprecation warning
        with pytest.warns(DeprecationWarning, match="output_directoryは非推奨です。output_pathを使用してください。"):
            config.output_directory = Path("/new/output")
            assert config.output_path == Path("/new/output")

    def test_output_directory_alias_functionality(self) -> None:
        """Test that output_directory alias works correctly as getter/setter."""
        config = TypeDocConfig(output_path=Path("/initial/output"))

        # Test that getter returns current output_path value
        with pytest.warns(DeprecationWarning):
            assert config.output_directory == Path("/initial/output")

        # Test that setter updates output_path value
        with pytest.warns(DeprecationWarning):
            config.output_directory = Path("/updated/output")

        # Verify the underlying output_path was updated
        assert config.output_path == Path("/updated/output")

        # Verify getter returns the updated value
        with pytest.warns(DeprecationWarning):
            assert config.output_directory == Path("/updated/output")

    def test_backward_compatibility_with_constructor(self) -> None:
        """Test that old code using output_directory in constructor still works."""
        # This should work but issue a deprecation warning when accessing the property
        config = TypeDocConfig(output_path=Path("/test/output"))

        # Accessing the property should issue warning
        with pytest.warns(DeprecationWarning):
            _ = config.output_directory

        # But setting it should also work
        with pytest.warns(DeprecationWarning):
            config.output_directory = Path("/new/path")

        assert config.output_path == Path("/new/path")
