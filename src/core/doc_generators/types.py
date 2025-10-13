"""
ドキュメント生成モジュールの型定義

このモジュールでは、ドキュメント生成機能に関連する型定義を提供します。
主に以下のカテゴリの型を定義します：

1. ドキュメント生成関連の型
2. 型検査関連の型
3. マークダウン生成関連の型
4. ファイルシステム関連の型
"""

from pathlib import Path
from typing import Annotated, Any, TypedDict

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from src.core.schemas.types import PositiveInt


def _validate_output_path(v: str | Path | None) -> str | Path | None:
    """出力先パスを検証するバリデーター(存在しないパスも許可)"""
    if v is None:
        return v
    # Pathオブジェクトに変換して返すだけ(存在チェックは行わない)
    return Path(v) if isinstance(v, str) else v


# TypedDict定義
class TocEntry(TypedDict):
    """目次エントリの型定義"""

    title: str
    level: int


class PydanticSchemaInfo(TypedDict, total=False):
    """
    Pydanticのmodel_json_schema()から返されるJSON Schemaの形状をモデル化

    JSON Schemaの標準フィールドを定義し、追加フィールドはdict[str, Any]でフォールバック
    """

    type: str
    properties: dict[str, "PydanticSchemaInfo"]  # ネストされたプロパティ定義
    required: list[str]
    additionalProperties: bool
    title: str
    description: str
    default: Any  # デフォルト値は任意の型
    examples: list[Any]  # 例は任意の型リスト
    format: str
    minimum: float | int
    maximum: float | int
    exclusiveMinimum: float | int
    exclusiveMaximum: float | int
    multipleOf: float | int
    # 追加の動的フィールド用フォールバック - JSON Schemaの拡張フィールドに対応
    # dict[str, Any]を使用: JSON Schemaは柔軟な拡張を許容するため


class DocumentMetadata(TypedDict, total=False):
    """
    ドキュメントのメタデータをモデル化

    一般的なメタデータキーを定義し、追加フィールドはdict[str, Any]でフォールバック
    """

    title: str
    description: str
    version: str
    author: str
    created_at: str  # ISO 8601形式のタイムスタンプ
    updated_at: str  # ISO 8601形式のタイムスタンプ
    tags: list[str]
    category: str
    language: str  # 言語コード (例: "ja", "en")
    encoding: str  # 文字エンコーディング (例: "utf-8")
    template: str  # 使用テンプレート名
    # 追加の動的メタデータフィールド用フォールバック - カスタムメタデータに対応
    # dict[str, Any]を使用: ドキュメント生成時の柔軟な拡張を許容するため


# Level 1: 単純な型エイリアス(制約なし)
# NOTE: OutputPathは ValidatedOutputPath でバリデーション済み版を提供
type OutputPath = str | Path | None

# @keep-as-is: true
# 理由: コンテンツ文字列は空文字列や任意の長さを許容する必要があるため、制約なしが適切
type ContentString = str

# @keep-as-is: true
# 理由: コードブロックは空文字列や任意の長さを許容する必要があるため、制約なしが適切
type CodeBlock = str

# @keep-as-is: true
# 理由: Markdownセクションは空文字列や任意の長さを許容する必要があるため、制約なしが適切
type MarkdownSection = str

# Level 2: Annotated + Field(制約付き)
# テンプレート名(空文字列禁止)
type TemplateName = Annotated[str, Field(min_length=1, description="テンプレート名(空文字列不可)")]

# 型名(空文字列禁止)
type TypeName = Annotated[str, Field(min_length=1, description="型名(空文字列不可)")]

# OutputPath のバリデーション済み版
# NOTE: OutputPath は str | Path | None なので、NewTypeでは扱えない(Union型のため)
type ValidatedOutputPath = Annotated[OutputPath, AfterValidator(_validate_output_path)]


class DocumentConfig(BaseModel):
    """
    ドキュメント生成の設定

    このクラスは、ドキュメント生成処理の設定を管理します。
    """

    output_path: ValidatedOutputPath = Field(description="出力ディレクトリのパス")
    template_name: TemplateName | None = Field(default=None, description="使用するテンプレート名")
    include_toc: bool = Field(default=True, description="目次を含めるかどうか")
    include_code_blocks: bool = Field(default=True, description="コードブロックを含めるかどうか")
    max_depth: int = Field(gt=0, default=3, description="ドキュメントの最大深さ")
    encoding: str = Field(default="utf-8", description="出力ファイルのエンコーディング")

    model_config = ConfigDict(frozen=True)


class TypeInspectionConfig(BaseModel):
    """
    型検査の設定

    このクラスは、型検査処理の設定を管理します。
    """

    skip_types: list[TypeName] = Field(default_factory=list, description="スキップする型のリスト")
    max_inspection_depth: int = Field(gt=0, default=5, description="検査の最大深さ")
    include_private_types: bool = Field(default=False, description="プライベート型を含めるかどうか")
    include_builtin_types: bool = Field(default=False, description="組み込み型を含めるかどうか")

    model_config = ConfigDict(frozen=True)


class MarkdownGenerationConfig(BaseModel):
    """
    マークダウン生成の設定

    このクラスは、マークダウン生成処理の設定を管理します。
    """

    section_level: int = Field(gt=0, default=1, description="セクションの見出しレベル")
    include_toc: bool = Field(default=True, description="目次を含めるかどうか")
    include_code_syntax: bool = Field(default=True, description="コード構文ハイライトを含めるかどうか")
    code_language: str = Field(default="python", description="コードブロックの言語指定")
    max_code_lines: PositiveInt | None = Field(default=None, description="コードブロックの最大行数(Noneで無制限)")
    include_type_hints: bool = Field(default=True, description="型ヒントを含めるかどうか")

    model_config = ConfigDict(frozen=True)


class FileSystemConfig(BaseModel):
    """
    ファイルシステム操作の設定

    このクラスは、ファイルシステム操作の設定を管理します。
    """

    create_directories: bool = Field(default=True, description="必要なディレクトリを作成するかどうか")
    overwrite_existing: bool = Field(default=False, description="既存ファイルを上書きするかどうか")
    backup_existing: bool = Field(default=True, description="既存ファイルをバックアップするかどうか")
    file_permissions: str | None = Field(default=None, description="ファイルのパーミッション(Noneでデフォルト)")

    model_config = ConfigDict(frozen=True)


class GenerationResult(BaseModel):
    """
    ドキュメント生成結果

    このクラスは、ドキュメント生成処理の結果を保持します。
    """

    success: bool = Field(description="生成が成功したかどうか")
    output_path: ValidatedOutputPath = Field(description="出力ファイルのパス")
    generated_files: list[OutputPath] = Field(default_factory=list, description="生成されたファイルのリスト")
    generation_time_ms: float = Field(ge=0.0, description="生成時間(ミリ秒)")
    error_message: str | None = Field(default=None, description="エラーメッセージ")
    files_count: int = Field(ge=0, description="生成されたファイル数")

    model_config = ConfigDict(frozen=True)


class TypeInspectionResult(BaseModel):
    """
    型検査結果

    このクラスは、型検査処理の結果を保持します。
    """

    type_name: TypeName = Field(description="検査対象の型名")
    is_pydantic_model: bool = Field(description="Pydanticモデルかどうか")
    has_docstring: bool = Field(description="docstringが存在するか")
    docstring_content: str | None = Field(default=None, description="docstringの内容")
    code_blocks: list[CodeBlock] = Field(default_factory=list, description="抽出されたコードブロック")
    schema_info: PydanticSchemaInfo | None = Field(
        default=None, description="Pydanticスキーマ情報(JSON Schema形式の型付きデータ)"
    )
    inspection_time_ms: float = Field(ge=0.0, description="検査時間(ミリ秒)")
    error_message: str | None = Field(default=None, description="エラーメッセージ")

    model_config = ConfigDict(frozen=True)


class MarkdownSectionInfo(BaseModel):
    """
    マークダウンセクション情報

    このクラスは、マークダウンセクションの情報を保持します。
    """

    title: str = Field(description="セクションタイトル")
    level: int = Field(gt=0, description="見出しレベル")
    content: ContentString = Field(description="セクション内容")
    subsections: list["MarkdownSectionInfo"] = Field(default_factory=list, description="サブセクションのリスト")
    code_blocks: list[CodeBlock] = Field(default_factory=list, description="コードブロックのリスト")

    model_config = ConfigDict(frozen=True)


def create_empty_metadata() -> DocumentMetadata:
    """
    空のDocumentMetadataを作成する

    DocumentMetadataはtotal=FalseのTypedDictなので、すべてのフィールドがオプショナルです。
    この関数は型安全に空のメタデータを生成します。

    Returns:
        DocumentMetadata: 空のドキュメントメタデータ
    """
    return {}


class DocumentStructure(BaseModel):
    """
    ドキュメント構造

    このクラスは、ドキュメントの全体構造を保持します。
    """

    title: str = Field(description="ドキュメントタイトル")
    sections: list[MarkdownSectionInfo] = Field(default_factory=list, description="メインセクションのリスト")
    toc: list[TocEntry] = Field(default_factory=list, description="目次情報")
    metadata: DocumentMetadata = Field(
        default_factory=create_empty_metadata, description="ドキュメントメタデータ(型付きの構造化データ)"
    )
    generation_timestamp: str = Field(description="生成時刻(ISO形式)")

    model_config = ConfigDict(frozen=True)


class TemplateConfig(BaseModel):
    """
    テンプレート設定

    このクラスは、ドキュメント生成で使用するテンプレートの設定を管理します。
    """

    template_name: TemplateName = Field(description="テンプレート名")
    template_path: ValidatedOutputPath | None = Field(default=None, description="テンプレートファイルのパス")
    variables: dict[str, Any] = Field(
        default_factory=dict,
        description="テンプレート変数の辞書(動的なkey-value)",
    )  # TODO: TypedDict/Union変換 - テンプレート変数の形状が判明したらTypedDictまたはUnion型に変換
    # 現在は完全に動的だが、既知の変数形状が確定したら型安全性を向上させる
    custom_sections: list[MarkdownSectionInfo] = Field(default_factory=list, description="カスタムセクションのリスト")

    model_config = ConfigDict(frozen=True)


class DocumentationMetrics(BaseModel):
    """
    ドキュメント指標

    このクラスは、ドキュメントの品質指標を保持します。
    """

    total_types: int = Field(ge=0, description="対象の型総数")
    documented_types: int = Field(ge=0, description="ドキュメント付きの型数")
    documentation_coverage: float = Field(description="ドキュメントカバー率(0.0-1.0)", ge=0.0, le=1.0)
    avg_docstring_lines: float = Field(ge=0.0, description="平均docstring行数")
    code_blocks_count: int = Field(ge=0, description="コードブロック総数")
    sections_count: int = Field(ge=0, description="セクション総数")

    model_config = ConfigDict(frozen=True)


class BatchGenerationConfig(BaseModel):
    """
    バッチ生成の設定

    このクラスは、複数のドキュメントを一括生成する際の設定を管理します。
    """

    input_paths: list[ValidatedOutputPath] = Field(description="入力ファイルパスのリスト")
    output_directory: ValidatedOutputPath = Field(description="出力ディレクトリ")
    parallel_processing: bool = Field(default=False, description="並列処理を使用するか")
    max_workers: PositiveInt | None = Field(default=None, description="最大ワーカー数(Noneで自動設定)")
    continue_on_error: bool = Field(default=True, description="エラー発生時に処理を継続するか")

    model_config = ConfigDict(frozen=True)


class BatchGenerationResult(BaseModel):
    """
    バッチ生成結果

    このクラスは、バッチ生成処理の結果を保持します。
    """

    success: bool = Field(description="全体の処理が成功したかどうか")
    total_files: int = Field(ge=0, description="処理対象のファイル総数")
    successful_files: int = Field(ge=0, description="成功したファイル数")
    failed_files: int = Field(ge=0, description="失敗したファイル数")
    total_generation_time_ms: float = Field(ge=0.0, description="総生成時間(ミリ秒)")
    results: list[GenerationResult] = Field(default_factory=list, description="個別結果のリスト")
    error_summary: dict[str, int] = Field(default_factory=dict, description="エラータイプ別の集計")

    model_config = ConfigDict(frozen=True)
