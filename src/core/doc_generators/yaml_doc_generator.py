"""YAML型仕様からMarkdownドキュメントを生成するモジュール。

このモジュールは、TypeSpecオブジェクトからMarkdownドキュメントを生成します。
"""

from collections.abc import Mapping
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


class MissingSpecError(ValueError):
    """specパラメータが指定されていない場合のエラー。"""


class InvalidSpecError(TypeError):
    """無効なspecタイプが指定された場合のエラー。"""


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
            MissingSpecError: specが指定されていない場合
            InvalidSpecError: specが無効な場合
        """
        spec_obj = kwargs.get("spec")
        if spec_obj is None:
            raise MissingSpecError()

        # 単一の正規化ステップ: Mappingの場合、"types"またはroot type fieldがある場合TypeRoot、そうでなければTypeSpec
        if isinstance(spec_obj, Mapping):
            obj_type_field = spec_obj.get("type")
            if "types" in spec_obj or obj_type_field in ("root", "typeroot"):
                spec_obj = TypeRoot.model_validate(spec_obj)
            else:
                spec_obj = TypeSpec.model_validate(spec_obj)
        elif not isinstance(spec_obj, (TypeSpec, TypeRoot)):
            obj_type = type(spec_obj).__name__
            raise InvalidSpecError(obj_type)

        self.md = MarkdownBuilder()

        # TypeRoot の場合は TypeSpec に変換し、型を確定
        spec: TypeSpec
        if isinstance(spec_obj, TypeRoot):
            # TypeRoot の場合は最初の型定義を使用
            if spec_obj.types:
                spec = next(iter(spec_obj.types.values()))
            else:
                raise InvalidSpecError("empty TypeRoot")
        elif isinstance(spec_obj, TypeSpec):
            # この時点で spec_obj は TypeSpec として確定
            spec = spec_obj
        else:
            # このelse節は到達しないはずだが、型チェッカーのために追加
            raise InvalidSpecError(f"unexpected type: {type(spec_obj).__name__}")

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
def generate_yaml_docs(spec: TypeSpec | TypeRoot, output_dir: str | None = None) -> None:
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

    config = TypeDocConfig(output_path=Path(output_dir))
    # filesystem が設定されていない場合はデフォルト値を使用
    filesystem = getattr(config, "filesystem", None)
    generator = YamlDocGenerator(filesystem=filesystem)  # 依存注入

    # TypeRoot の場合、最初の型を使用
    from src.core.schemas.yaml_spec import TypeRoot

    if isinstance(spec, TypeRoot) and spec.types:
        layer = next(iter(spec.types.keys()))
    elif isinstance(spec, TypeSpec):
        layer = spec.type
    else:
        # 適切なデフォルト値またはエラー処理
        layer = "unknown"

    output_path = Path(output_dir) / f"{layer}.md"
    generator.generate(output_path, spec=spec)
