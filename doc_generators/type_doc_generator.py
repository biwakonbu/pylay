"""Type documentation generators for automated type documentation."""

from pathlib import Path
from typing import Any

from .base import DocumentGenerator
from .config import TypeDocConfig
from .type_inspector import TypeInspector


class LayerDocGenerator(DocumentGenerator):
    """Generator for layer-specific type documentation."""

    def __init__(
        self,
        config: TypeDocConfig | None = None,
        **kwargs: object,
    ) -> None:
        """Initialize layer documentation generator.

        Args:
            config: Configuration for type documentation generation
            **kwargs: Additional arguments passed to parent constructor
        """
        # Extract filesystem and markdown_builder from kwargs with proper typing
        from .filesystem import FileSystemInterface
        from .markdown_builder import MarkdownBuilder

        filesystem = kwargs.pop('filesystem', None)
        markdown_builder = kwargs.pop('markdown_builder', None)

        # Type assertions for dependency injection
        fs_typed = filesystem if isinstance(filesystem, FileSystemInterface) or filesystem is None else None
        md_typed = markdown_builder if isinstance(markdown_builder, MarkdownBuilder) or markdown_builder is None else None

        super().__init__(filesystem=fs_typed, markdown_builder=md_typed)
        self.config = config or TypeDocConfig()
        self.inspector = TypeInspector(skip_types=self.config.skip_types)

    def generate(
        self,
        layer: str,
        types: dict[str, type[Any]],
        output_path: Path | None = None,
        **kwargs: object,
    ) -> None:
        """Generate layer documentation.

        Args:
            layer: Layer name
            types: Dictionary of types in the layer
            output_path: Optional override for output path
            **kwargs: Additional configuration parameters
        """
        if output_path is None:
            filename = self.config.layer_filename_template.format(layer=layer)
            output_path = self.config.output_directory / filename

        # Clear markdown builder
        self.md.clear()

        # Build document
        self._generate_header(layer)
        self._generate_auto_growth_section(layer)
        self._generate_layer_specific_section(layer)
        self._generate_type_sections(layer, types)
        self._add_footer()

        # Write to file
        content = self.md.build()
        self._write_file(output_path, content)

        print(f"✅ Generated {output_path}: {len(types)} types")

    def _generate_header(self, layer: str) -> None:
        """Generate document header.

        Args:
            layer: Layer name
        """
        title = f"{layer.upper()} レイヤー型カタログ（完全自動成長）"
        self.md.heading(1, title).line_break()

    def _generate_auto_growth_section(self, layer: str) -> None:
        """Generate auto-growth explanation section.

        Args:
            layer: Layer name
        """
        self.md.heading(2, "🎯 完全自動成長について").line_break()

        explanation = (
            "このレイヤーの型は、定義を追加するだけで自動的に利用可能になります。\n"
            "新しい型を追加すると、以下の方法ですぐに使用できます："
        )
        self.md.paragraph(explanation).line_break()

        code_example = (
            "from schemas.core_types import TypeFactory\n\n"
            "# 完全自動成長（レイヤー自動検知）\n"
            "MyNewType = TypeFactory.get_auto('MyNewType')"
        )
        self.md.code_block("python", code_example).line_break()

    def _generate_layer_specific_section(self, layer: str) -> None:
        """Generate layer-specific usage section.

        Args:
            layer: Layer name
        """
        if layer in self.config.layer_methods:
            self.md.heading(2, "💡 このレイヤーでの型取得").line_break()

            method_name = self.config.layer_methods[layer]
            code_example = (
                "from schemas.core_types import TypeFactory\n\n"
                "# レイヤー指定での取得（オプション）\n"
                f"MyType = TypeFactory.{method_name}('MyTypeName')"
            )
            self.md.code_block("python", code_example).line_break()

    def _generate_type_sections(self, layer: str, types: dict[str, type[Any]]) -> None:
        """Generate documentation sections for all types.

        Args:
            layer: Layer name
            types: Dictionary of types in the layer, or list of types
        """
        if isinstance(types, dict):
            # Dictionary形式の場合
            for name, type_cls in types.items():
                if self.inspector.should_skip_type(name):
                    continue
                self._generate_single_type_section(name, type_cls, layer)
        elif isinstance(types, list):
            # List形式の場合
            for type_cls in types:
                if self.inspector.should_skip_type(type_cls.__name__):
                    continue
                self._generate_single_type_section(type_cls.__name__, type_cls, layer)

    def _generate_single_type_section(
        self, name: str, type_cls: type[Any], layer: str
    ) -> None:
        """Generate documentation section for a single type.

        Args:
            name: Type name
            type_cls: Type class
            layer: Layer name
        """
        self.md.heading(2, name).line_break()

        # Description
        self._generate_type_description(name, type_cls)

        # Usage examples
        self._generate_usage_examples(name, layer)

        # Layer-specific method
        self._generate_layer_method_example(name, layer)

        # Type definition
        self._generate_type_definition(name, type_cls)

    def _generate_type_description(self, name: str, type_cls: type[Any]) -> None:
        """Generate type description section.

        Args:
            name: Type name
            type_cls: Type class
        """
        # Check for custom descriptions first
        if name in self.config.type_alias_descriptions:
            description = self.config.type_alias_descriptions[name]
            self.md.heading(3, "説明").paragraph(description).line_break()
            return

        # Get docstring
        docstring = self.inspector.get_docstring(type_cls)
        if not docstring:
            self.md.heading(3, "説明").paragraph(f"{name} 型の定義").line_break()
            return

        # Handle standard NewType documentation
        if self.inspector.is_standard_newtype_doc(docstring):
            if name == "NewType":
                return  # Skip NewType itself
            else:
                description = f"{name} - カスタム型定義（型安全性のためのNewType）"
                self.md.heading(3, "説明").paragraph(description).line_break()
                return

        # Process complex docstrings with code blocks
        description_lines, code_blocks = self.inspector.extract_code_blocks(docstring)

        if description_lines:
            description = " ".join(description_lines)
            self.md.heading(3, "説明").paragraph(description).line_break()

        for i, code in enumerate(code_blocks):
            self.md.heading(3, f"コード例 {i+1}").code_block("python", code).line_break()

    def _generate_usage_examples(self, name: str, layer: str) -> None:
        """Generate usage examples section.

        Args:
            name: Type name
            layer: Layer name
        """
        self.md.heading(3, "利用方法（完全自動成長）")

        usage_code = (
            "from schemas.core_types import TypeFactory\n\n"
            "# 完全自動成長（レイヤー自動検知）\n"
            f"{name}Type = TypeFactory.get_auto('{name}')\n"
        )

        # Add layer-specific usage example
        if layer == "primitives":
            usage_code += f'instance = {name}Type("example_value")'
        elif layer == "domain":
            usage_code += f'{name}Type(field1="value1", field2="value2")'
        elif layer == "api":
            usage_code += f'{name}Type(service_name="MyService")'
        else:
            usage_code += f"instance = {name}Type()"

        self.md.code_block("python", usage_code).line_break()

    def _generate_layer_method_example(self, name: str, layer: str) -> None:
        """Generate layer-specific method example.

        Args:
            name: Type name
            layer: Layer name
        """
        self.md.heading(3, "レイヤー指定方法（オプション）")

        layer_code = f"{name}Type = TypeFactory.get_by_layer('{layer}', '{name}')"
        self.md.code_block("python", layer_code).line_break()

    def _generate_type_definition(self, name: str, type_cls: type[Any]) -> None:
        """Generate type definition section.

        Args:
            name: Type name
            type_cls: Type class
        """
        if self.inspector.is_pydantic_model(type_cls):
            self.md.heading(3, "型定義（JSONSchema）")
            schema = self.inspector.get_pydantic_schema(type_cls)
            if schema:
                import json
                schema_json = json.dumps(schema, indent=2, ensure_ascii=False)
                self.md.code_block("json", schema_json).line_break()
        else:
            self.md.heading(3, "型定義")
            definition = self.inspector.format_type_definition(name, type_cls)
            self.md.raw(definition).line_break()

    def _add_footer(self) -> None:
        """Add generation footer."""
        footer = self._format_generation_footer()
        self.md.raw(footer)


class IndexDocGenerator(DocumentGenerator):
    """Generator for type documentation index."""

    def __init__(
        self,
        config: TypeDocConfig | None = None,
        **kwargs: object,
    ) -> None:
        """Initialize index documentation generator.

        Args:
            config: Configuration for type documentation generation
            **kwargs: Additional arguments passed to parent constructor
        """
        # Extract filesystem and markdown_builder from kwargs with proper typing
        from .filesystem import FileSystemInterface
        from .markdown_builder import MarkdownBuilder

        filesystem = kwargs.pop('filesystem', None)
        markdown_builder = kwargs.pop('markdown_builder', None)

        # Type assertions for dependency injection
        fs_typed = filesystem if isinstance(filesystem, FileSystemInterface) or filesystem is None else None
        md_typed = markdown_builder if isinstance(markdown_builder, MarkdownBuilder) or markdown_builder is None else None

        super().__init__(filesystem=fs_typed, markdown_builder=md_typed)
        self.config = config or TypeDocConfig()

    def generate(
        self,
        type_registry: dict[str, dict[str, type[Any]]],
        output_path: Path | None = None,
        **kwargs: object,
    ) -> None:
        """Generate index documentation.

        Args:
            type_registry: Registry of all types organized by layer
            output_path: Optional override for output path
            **kwargs: Additional configuration parameters
        """
        if output_path is None:
            output_path = self.config.output_directory / self.config.index_filename

        # Clear markdown builder
        self.md.clear()

        # Build document
        self._generate_header()
        self._generate_unified_usage_section()
        self._generate_layer_sections(type_registry)
        self._generate_statistics(type_registry)
        self._add_footer()

        # Write to file
        content = self.md.build()
        self._write_file(output_path, content)

        total_types = sum(len(layer_types) for layer_types in type_registry.values())
        print(f"✅ Generated index {output_path}: {total_types} total types")

    def _generate_header(self) -> None:
        """Generate document header."""
        self.md.heading(1, "型インデックス（完全自動成長対応）").line_break()

    def _generate_unified_usage_section(self) -> None:
        """Generate unified usage method section."""
        self.md.heading(2, "🚀 統一的な型取得方法").line_break()

        explanation = (
            "すべての型に対して統一的な方法で取得可能です。"
            "型を追加するだけで自動的に利用可能になります。"
        )
        self.md.paragraph(explanation).line_break()

        usage_example = (
            "from schemas.core_types import TypeFactory\n\n"
            "# 完全自動成長（レイヤー自動検知）\n"
            "UserIdType = TypeFactory.get_auto('UserId')\n"
            "HeroContentType = TypeFactory.get_auto('HeroContent')\n"
            "APIRequestType = TypeFactory.get_auto('LPGenerationRequest')\n\n"
            "# インスタンス化\n"
            'user_id = UserIdType("user123")\n'
            'hero_data = HeroContentType(headline="Hello", subheadline="World")\n'
            'request = APIRequestType(service_name="MyService")'
        )
        self.md.code_block("python", usage_example).line_break()

    def _generate_layer_sections(
        self, type_registry: dict[str, dict[str, type[Any]]]
    ) -> None:
        """Generate layer detail sections.

        Args:
            type_registry: Registry of all types organized by layer
        """
        self.md.heading(2, "📁 レイヤー別詳細").line_break()

        for layer, layer_types in type_registry.items():
            self._generate_single_layer_section(layer, layer_types)

    def _generate_single_layer_section(
        self, layer: str, layer_types: dict[str, type[Any]]
    ) -> None:
        """Generate section for a single layer.

        Args:
            layer: Layer name
            layer_types: Types in the layer
        """
        self.md.heading(3, f"{layer.upper()} レイヤー")

        type_count = len(layer_types)
        self.md.bullet_point(f"**型数**: {type_count}")

        # Link to detailed documentation
        layer_doc_link = f"types/{layer}.md"
        link_text = self.md.link("詳細を見る", layer_doc_link)
        self.md.bullet_point(link_text).line_break()

        # Preview of main types
        type_names = list(layer_types.keys())[:5]  # First 5 types
        if type_names:
            types_text = ", ".join(type_names)
            self.md.bullet_point(f"**主な型**: {types_text}")

            if type_count > 5:
                self.md.bullet_point(f"**他**: +{type_count - 5} 型")

        self.md.line_break()

    def _generate_statistics(
        self, type_registry: dict[str, dict[str, type[Any]]]
    ) -> None:
        """Generate statistics section.

        Args:
            type_registry: Registry of all types organized by layer
        """
        total_types = sum(len(layer_types) for layer_types in type_registry.values())

        self.md.heading(2, "📊 統計情報").line_break()
        self.md.bullet_point(f"**総型数**: {total_types}")

        # TODO: Add TypeRegistry.get_available_types_all() when available
        # all_types = TypeRegistry.get_available_types_all()
        # self.md.bullet_point(f"**全レイヤー型一覧**: {all_types}")

    def _add_footer(self) -> None:
        """Add generation footer."""
        footer = self._format_generation_footer()
        self.md.raw(footer)
