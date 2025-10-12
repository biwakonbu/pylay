"""YAML型仕様からMarkdownドキュメントを生成するモジュール。

このモジュールは、TypeSpecオブジェクトからMarkdownドキュメントを生成します。
"""

from pathlib import Path

from src.core.schemas.pylay_config import PylayConfig
from src.core.schemas.yaml_spec import (
    DictTypeSpec,
    ListTypeSpec,
    RefPlaceholder,
    TypeRoot,
    TypeSpec,
    UnionTypeSpec,
)

from .base import DocumentGenerator
from .config import TypeDocConfig
from .markdown_builder import MarkdownBuilder


class YamlDocGenerator(DocumentGenerator):
    """YAML型仕様からドキュメントを生成します。

    TypeSpecオブジェクトを受け取り、Markdownフォーマットのドキュメントを生成します。
    """

    def generate(self, output_path: Path, **kwargs: object) -> None:
        """ドキュメントを生成し、ファイルに書き出します。

        Args:
            output_path: 出力先ファイルパス
            **kwargs: 追加パラメータ
                spec: 型仕様オブジェクト（TypeSpec | TypeRoot）

        Raises:
            ValueError: specが指定されていない、または無効な場合
        """
        spec_obj = kwargs.get("spec")
        if spec_obj is None:
            raise ValueError("spec parameter is required")

        # 型チェック: spec は TypeSpec または TypeRoot である必要がある
        # 互換オブジェクト(type/name属性を持つdictなど)も受け入れる
        if isinstance(spec_obj, (TypeSpec, TypeRoot)):  # noqa: UP038
            # 既に適切な型なのでそのまま使用
            pass
        else:
            # 互換オブジェクトの可能性をチェック
            obj_type = type(spec_obj).__name__
            has_type_attr = hasattr(spec_obj, "type")
            has_name_attr = hasattr(spec_obj, "name")

            if has_type_attr and has_name_attr:
                # TypeSpec/TypeRoot互換オブジェクトの場合、適切なモデルで変換を試行
                try:
                    # typeフィールドの値でTypeSpecかTypeRootかを判定
                    obj_type_field = getattr(spec_obj, "type", None)
                    if obj_type_field == "root" or obj_type_field == "typeroot":
                        # TypeRoot互換オブジェクトの場合
                        spec_obj = TypeRoot.model_validate(spec_obj)
                    else:
                        # TypeSpec互換オブジェクトの場合
                        spec_obj = TypeSpec.model_validate(spec_obj)
                except Exception as e:
                    raise TypeError(
                        f"Failed to convert compatible object {obj_type} to TypeSpec or TypeRoot: {e}. "
                        f"Please ensure the object has valid structure."
                    ) from e
            else:
                raise TypeError(f"spec must be TypeSpec, TypeRoot, or TypeSpec-compatible object, got {obj_type}")

        self.md = MarkdownBuilder()

        # TypeRoot の場合は TypeSpec に変換し、型を確定
        spec: TypeSpec
        if isinstance(spec_obj, TypeRoot):
            # TypeRoot の場合は最初の型定義を使用
            if spec_obj.types:
                spec = next(iter(spec_obj.types.values()))
            else:
                raise TypeError("Empty TypeRoot")
        else:
            # この時点で spec_obj は TypeSpec として確定
            spec = spec_obj

        # この時点で spec は TypeSpec として確定している
        self._generate_header(spec)
        self._generate_body(spec)
        self._generate_footer()

        content = self.md.build()
        self._write_file(output_path, content)

    def _generate_header(self, spec: TypeSpec) -> None:
        """ドキュメントのヘッダー部分を生成します。

        Args:
            spec: 型仕様オブジェクト
        """
        self.md.heading(1, f"型仕様: {spec.name}")
        if spec.description:
            self.md.paragraph(spec.description)

    def _generate_body(self, spec: TypeSpec | RefPlaceholder | str, depth: int = 0) -> None:
        """再帰的に型情報を生成（深さ制限付き）"""
        if depth > 10:  # 深さ制限
            self.md.paragraph("... (深さ制限を超えました)")
            return

        self.md.heading(2, "型情報")
        if isinstance(spec, str):
            self.md.paragraph(f"参照: {spec}")
        elif isinstance(spec, RefPlaceholder):
            self.md.paragraph(f"参照: {spec.ref_name}")
        else:
            self.md.code_block("yaml", self._spec_to_yaml(spec))

        if isinstance(spec, ListTypeSpec):
            self.md.heading(2, "要素型")
            self._generate_body(spec.items, depth + 1)
        elif isinstance(spec, DictTypeSpec):
            self.md.heading(2, "プロパティ")
            for name, prop in spec.properties.items():
                self.md.heading(3, name)
                self._generate_body(prop, depth + 1)
        elif isinstance(spec, UnionTypeSpec):
            self.md.heading(2, "バリアント")
            for variant in spec.variants:
                self._generate_body(variant, depth + 1)

    def _generate_footer(self) -> None:
        """ドキュメントのフッター部分を生成します。"""
        self.md.horizontal_rule()
        self.md.paragraph("このドキュメントは自動生成されました。")

    def _spec_to_yaml(self, spec: TypeSpec | str) -> str:
        """TypeSpecをYAML文字列に変換します。

        Args:
            spec: 型仕様オブジェクトまたは参照文字列

        Returns:
            YAML形式の文字列
        """
        if isinstance(spec, str):
            return f'"{spec}"'  # 参照文字列の場合は引用符で囲む
        from ruamel.yaml import YAML

        yaml_parser = YAML()
        yaml_parser.preserve_quotes = True
        from io import StringIO

        output = StringIO()
        yaml_parser.dump(spec.model_dump(), output)
        return output.getvalue()


# 統合関数
def generate_yaml_docs(spec: TypeSpec, output_dir: str | None = None) -> None:
    """YAML仕様からドキュメント生成"""
    if output_dir is None:
        # 設定ファイルから出力ディレクトリを取得
        try:
            pylay_config = PylayConfig.from_pyproject_toml()
            pylay_config.ensure_output_structure(Path.cwd())
            output_dir = str(pylay_config.get_documents_output_dir(Path.cwd()))
        except Exception:
            # 設定ファイルがない場合はデフォルト値を使用
            output_dir = "docs/pylay-types/documents"

    config = TypeDocConfig(output_directory=Path(output_dir))
    generator = YamlDocGenerator(filesystem=config.filesystem)  # 依存注入

    # TypeRoot の場合、最初の型を使用
    from src.core.schemas.yaml_spec import TypeRoot

    if isinstance(spec, TypeRoot) and spec.types:
        layer = next(iter(spec.types.keys()))
    else:
        layer = spec.type

    output_path = Path(output_dir) / f"{layer}.md"
    generator.generate(output_path, spec=spec)
