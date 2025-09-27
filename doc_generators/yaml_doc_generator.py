from pathlib import Path

from .base import DocumentGenerator
from .config import TypeDocConfig
from .markdown_builder import MarkdownBuilder

from schemas.yaml_type_spec import TypeSpec, ListTypeSpec, DictTypeSpec, UnionTypeSpec

class YamlDocGenerator(DocumentGenerator):
    """YAML型仕様からドキュメントを生成"""

    def generate(self, output_path: Path, **kwargs: object) -> None:
        spec = kwargs.get('spec')
        if spec is None:
            raise ValueError("spec parameter is required")
        if not isinstance(spec, TypeSpec):
            raise ValueError("spec must be a TypeSpec instance")
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

    def _generate_body(self, spec: TypeSpec | str) -> None:
        self.md.heading(2, "型情報")
        if isinstance(spec, str):
            self.md.paragraph(f"参照: {spec}")
        else:
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

    def _spec_to_yaml(self, spec: TypeSpec | str) -> str:
        if isinstance(spec, str):
            return f'"{spec}"'  # 参照文字列の場合は引用符で囲む
        import yaml
        return yaml.dump(spec.model_dump(), default_flow_style=False, allow_unicode=True, indent=2)  # type: ignore[no-any-return]

# 統合関数
def generate_yaml_docs(spec: TypeSpec, output_dir: str = "docs/yaml_types") -> None:
    """YAML仕様からドキュメント生成"""
    config = TypeDocConfig(output_directory=Path(output_dir))
    generator = YamlDocGenerator(filesystem=config.filesystem)  # 依存注入
    output_path = Path(output_dir) / f"{spec.name}.md"
    generator.generate(output_path, spec=spec)
