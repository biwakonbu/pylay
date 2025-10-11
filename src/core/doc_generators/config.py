"""ドキュメントジェネレーター用の設定クラス。"""

from dataclasses import dataclass, field
from pathlib import Path

from src.core.schemas.types import (
    Description,
    GlobPattern,
    IndexFilename,
    LayerFilenameTemplate,
    LayerName,
    MethodName,
    TypeName,
)

from .filesystem import FileSystemInterface, RealFileSystem


@dataclass
class GeneratorConfig:
    """ドキュメントジェネレーターの基本設定。"""

    output_path: Path = field(default=Path("docs"))
    include_patterns: list[GlobPattern] = field(default_factory=list)
    exclude_patterns: list[GlobPattern] = field(default_factory=list)


@dataclass
class CatalogConfig(GeneratorConfig):
    """テストカタログジェネレーターの設定。"""

    test_directory: Path = field(default=Path("tests"))
    output_path: Path = field(default=Path("docs/types/test_catalog.md"))
    include_patterns: list[GlobPattern] = field(default_factory=lambda: ["test_*.py"])
    exclude_patterns: list[GlobPattern] = field(default_factory=lambda: ["__pycache__", "*.pyc"])


@dataclass
class TypeDocConfig(GeneratorConfig):
    """型ドキュメントジェネレーターの設定。"""

    output_directory: Path = field(default=Path("docs/types"))
    index_filename: IndexFilename = field(default=IndexFilename("README.md"))
    layer_filename_template: LayerFilenameTemplate = field(default=LayerFilenameTemplate("{layer}.md"))
    skip_types: set[TypeName] = field(default_factory=set)
    type_alias_descriptions: dict[TypeName, Description] = field(
        default_factory=lambda: {
            "JSONValue": "JSON値: 制約なしのJSON互換データ型（Anyのエイリアス）",
            "JSONObject": ("JSONオブジェクト: 文字列キーと任意の値を持つ辞書型"),
            "RestrictedJSONValue": ("制限付きJSON値: 深さ3制限付きのJSONデータ"),
            "RestrictedJSONObject": ("制限付きJSONオブジェクト: 制限付きのJSON値を持つ辞書型"),
        }
    )
    layer_methods: dict[LayerName, MethodName] = field(
        default_factory=lambda: {
            "primitives": "get_primitive",
            "domain": "get_domain",
            "api": "get_api",
            "activity": "get_activity",
        }
    )
    filesystem: FileSystemInterface = field(default_factory=lambda: RealFileSystem())
