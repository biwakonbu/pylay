from pathlib import Path

from .base import DocumentGenerator
from .config import TypeDocConfig
from .markdown_builder import MarkdownBuilder

from schemas.yaml_type_spec import TypeSpec, ListTypeSpec, DictTypeSpec, UnionTypeSpec

class YamlDocGenerator(DocumentGenerator):
    """YAML型仕様からドキュメントを生成"""

    def generate(self, spec: TypeSpec, output_path: Path) -> None:
        self.md.clear()  # 既存のコンテンツをクリア
        self.md = MarkdownBuilder()

        self._generate_header(spec)
        self._generate_body(spec)
        self._generate_footer()

        content = self.md.build()
        self._write_file(output_path, content)

    def _generate_header(self, spec: TypeSpec) -> None:
        self.md.heading(1, f"型仕様: {spec.name}")
        if spec.description:
            self.md.paragraph(spec.description)

    def _generate_body(self, spec: TypeSpec) -> None:
        self.md.heading(2, "型情報")
        self.md.code_block("yaml", self._spec_to_yaml(spec))

        if isinstance(spec, ListTypeSpec):
            self.md.heading(2, "要素型")
            self._generate_body(spec.items)
        elif isinstance(spec, DictTypeSpec):
            self.md.heading(2, "プロパティ")
            for name, prop in spec.properties.items():
                self.md.heading(3, name)
                self._generate_body(prop)
        elif isinstance(spec, UnionTypeSpec):
            self.md.heading(2, "バリアント")
            for variant in spec.variants:
                self._generate_body(variant)

    def _generate_footer(self) -> None:
        self.md.horizontal_rule()
        self.md.paragraph("このドキュメントは自動生成されました。")

    def _spec_to_yaml(self, spec: TypeSpec) -> str:
        import yaml
        return yaml.dump(spec.model_dump(), default_flow_style=False, allow_unicode=True, indent=2)

# 統合関数
def generate_yaml_docs(spec: TypeSpec, output_dir: str = "docs/yaml_types") -> None:
    """YAML仕様からドキュメント生成"""
    config = TypeDocConfig(output_directory=Path(output_dir))
    generator = YamlDocGenerator(filesystem=config.filesystem)  # 依存注入
    output_path = Path(output_dir) / f"{spec.name}.md"
    generator.generate(spec, output_path)
