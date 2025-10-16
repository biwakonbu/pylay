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


@dataclass(init=False)
class TypeDocConfig:
    """型ドキュメントジェネレーターの設定。"""

    # 基本設定(GeneratorConfigから継承せず、独自に定義)
    output_path: Path
    include_patterns: list[GlobPattern]
    exclude_patterns: list[GlobPattern]

    # TypeDocConfig独自の設定
    index_filename: IndexFilename
    layer_filename_template: LayerFilenameTemplate
    skip_types: set[TypeName]
    type_alias_descriptions: dict[TypeName, Description]
    layer_methods: dict[LayerName, MethodName]
    filesystem: FileSystemInterface

    def __init__(
        self,
        output_path: Path | None = None,
        include_patterns: list[GlobPattern] | None = None,
        exclude_patterns: list[GlobPattern] | None = None,
        index_filename: IndexFilename | None = None,
        layer_filename_template: LayerFilenameTemplate | None = None,
        skip_types: set[TypeName] | None = None,
        type_alias_descriptions: dict[TypeName, Description] | None = None,
        layer_methods: dict[LayerName, MethodName] | None = None,
        filesystem: FileSystemInterface | None = None,
        output_directory: Path | None = None,  # 非推奨: 後方互換性のため
    ) -> None:
        """TypeDocConfigの初期化。

        Args:
            output_path: 出力ディレクトリパス。デフォルト: docs/types
            include_patterns: 含めるグロブパターンのリスト。
            exclude_patterns: 除外するグロブパターンのリスト。
            index_filename: インデックスファイル名。デフォルト: README.md
            layer_filename_template: レイヤーファイル名テンプレート。デフォルト: {layer}.md
            skip_types: スキップする型名のセット。
            type_alias_descriptions: 型エイリアスの説明辞書。
            layer_methods: レイヤーメソッドの辞書。
            filesystem: ファイルシステムインターフェース。
            output_directory: 非推奨。output_pathを使用してください。

        """
        # 後方互換性処理: output_directoryが指定された場合、output_pathに設定
        if output_directory is not None:
            import warnings

            warnings.warn(
                "output_directoryは非推奨です。output_pathを使用してください。",
                DeprecationWarning,
                stacklevel=2,
            )
            output_path = output_directory

        self.output_path = output_path if output_path is not None else Path("docs/types")
        self.include_patterns = include_patterns if include_patterns is not None else []
        self.exclude_patterns = exclude_patterns if exclude_patterns is not None else []
        self.index_filename = index_filename if index_filename is not None else IndexFilename("README.md")
        self.layer_filename_template = (
            layer_filename_template if layer_filename_template is not None else LayerFilenameTemplate("{layer}.md")
        )
        self.skip_types = skip_types if skip_types is not None else set()
        self.type_alias_descriptions = (
            type_alias_descriptions
            if type_alias_descriptions is not None
            else {
                "JSONValue": "JSON値: 制約なしのJSON互換データ型（Anyのエイリアス）",
                "JSONObject": "JSONオブジェクト: 文字列キーと任意の値を持つ辞書型",
                "RestrictedJSONValue": "制限付きJSON値: 深さ3制限付きのJSONデータ",
                "RestrictedJSONObject": "制限付きJSONオブジェクト: 制限付きのJSON値を持つ辞書型",
            }
        )
        self.layer_methods = (
            layer_methods
            if layer_methods is not None
            else {
                "primitives": "get_primitive",
                "domain": "get_domain",
                "api": "get_api",
                "activity": "get_activity",
            }
        )
        self.filesystem = filesystem if filesystem is not None else RealFileSystem()

    @property
    def output_directory(self) -> Path:
        """後方互換性のためのoutput_directoryプロパティ。

        警告: このプロパティは非推奨です。output_pathを使用してください。
        """
        import warnings

        warnings.warn("output_directoryは非推奨です。output_pathを使用してください。", DeprecationWarning, stacklevel=2)
        return self.output_path

    @output_directory.setter
    def output_directory(self, value: Path) -> None:
        """後方互換性のためのoutput_directoryセッター。

        警告: このプロパティは非推奨です。output_pathを使用してください。
        """
        import warnings

        warnings.warn("output_directoryは非推奨です。output_pathを使用してください。", DeprecationWarning, stacklevel=2)
        self.output_path = value
