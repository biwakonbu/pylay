"""Configuration classes for document generators."""

from dataclasses import dataclass, field
from pathlib import Path

from .filesystem import FileSystemInterface, RealFileSystem


@dataclass
class GeneratorConfig:
    """Base configuration for document generators."""

    output_path: Path = field(default_factory=lambda: Path("docs"))
    include_patterns: list[str] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=list)


@dataclass
class CatalogConfig(GeneratorConfig):
    """Configuration for test catalog generator."""

    test_directory: Path = field(default_factory=lambda: Path("tests"))
    output_path: Path = field(
        default_factory=lambda: Path("docs/types/test_catalog.md")
    )
    include_patterns: list[str] = field(default_factory=lambda: ["test_*.py"])
    exclude_patterns: list[str] = field(
        default_factory=lambda: ["__pycache__", "*.pyc"]
    )


@dataclass
class TypeDocConfig(GeneratorConfig):
    """Configuration for type documentation generator."""

    output_directory: Path = field(default_factory=lambda: Path("docs/types"))
    index_filename: str = "README.md"
    layer_filename_template: str = "{layer}.md"
    skip_types: set[str] = field(default_factory=lambda: {"NewType"})
    type_alias_descriptions: dict[str, str] = field(
        default_factory=lambda: {
            "JSONValue": "JSON値: 制約なしのJSON互換データ型（Anyのエイリアス）",
            "JSONObject": "JSONオブジェクト: 文字列キーと任意の値を持つ辞書型",
            "RestrictedJSONValue": "制限付きJSON値: 深さ3制限付きのJSONデータ",
            "RestrictedJSONObject": "制限付きJSONオブジェクト: 制限付きのJSON値を持つ辞書型",
        }
    )
    layer_methods: dict[str, str] = field(
        default_factory=lambda: {
            "primitives": "get_primitive",
            "domain": "get_domain",
            "api": "get_api",
            "activity": "get_activity",
        }
    )
    filesystem: FileSystemInterface = field(default_factory=lambda: RealFileSystem())
