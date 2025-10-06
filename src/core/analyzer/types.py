"""
型解析モジュールの型定義

このモジュールでは、型解析機能に関連する型定義を提供します。
主に以下のカテゴリの型を定義します：

1. 型定義情報関連の型
2. ドキュメント解析関連の型
3. 統計情報関連の型
4. 品質評価関連の型
"""

from pathlib import Path
from typing import Annotated, Literal, NewType

from pydantic import AfterValidator, BaseModel, Field


def _validate_positive_int(v: int) -> int:
    """正の整数であることを検証するバリデーター"""
    if v <= 0:
        raise ValueError(f"正の整数である必要がありますが、{v}が指定されました")
    return v


def _validate_non_negative_int(v: int) -> int:
    """非負の整数であることを検証するバリデーター"""
    if v < 0:
        raise ValueError(f"非負の整数である必要がありますが、{v}が指定されました")
    return v


def _validate_percentage(v: float) -> float:
    """パーセンテージ値が適切な範囲内であることを検証するバリデーター"""
    if v < 0.0 or v > 1.0:
        raise ValueError(
            f"パーセンテージは0.0〜1.0の範囲である必要がありますが、{v}が指定されました"
        )
    return v


def _validate_file_path(v: str | Path) -> str | Path:
    """ファイルパスが存在することを検証するバリデーター"""
    path = Path(v)
    if not path.exists():
        raise ValueError(f"ファイルパスが存在しません: {v}")
    return v


# Level 1: 単純な型エイリアス（制約なし）
type FilePath = str | Path
type TypeName = str
type CategoryName = str
type FormatStyle = Literal["google", "numpy", "restructured", "unknown"]
type TypeLevel = Literal["level1", "level2", "level3", "other"]
type TargetLevel = Literal["level1", "level2", "level3"] | None

# Level 2: NewType + Annotated（制約付き、型レベル区別）
# NOTE: FilePath は str | Path なので、NewTypeでは扱えない（Union型のため）
type ValidatedFilePath = Annotated[FilePath, AfterValidator(_validate_file_path)]

PositiveInt = NewType(
    "PositiveInt", Annotated[int, Field(gt=0), AfterValidator(_validate_positive_int)]
)

NonNegativeInt = NewType(
    "NonNegativeInt",
    Annotated[int, Field(ge=0), AfterValidator(_validate_non_negative_int)],
)

Percentage = NewType(
    "Percentage",
    Annotated[float, Field(ge=0.0, le=1.0), AfterValidator(_validate_percentage)],
)


class TypeDefinition(BaseModel):
    """
    型定義の情報

    このクラスは、型定義の詳細情報を保持します。
    """

    name: TypeName = Field(description="型の名前")
    level: TypeLevel = Field(description="型定義レベル（level1/level2/level3/other）")
    file_path: ValidatedFilePath = Field(description="ファイルパス")
    line_number: PositiveInt = Field(description="行番号")
    definition: str = Field(description="型定義のコード")
    category: CategoryName = Field(
        description="型のカテゴリ（type_alias/annotated/basemodel/class/dataclass等）"
    )
    docstring: str | None = Field(default=None, description="docstring（存在する場合）")
    has_docstring: bool = Field(default=False, description="docstringが存在するか")
    docstring_lines: NonNegativeInt = Field(default=0, description="docstringの行数")  # type: ignore[assignment]
    target_level: TargetLevel = Field(
        default=None, description="docstringで指定された目標レベル"
    )
    keep_as_is: bool = Field(default=False, description="現状維持フラグ")

    class Config:
        """Pydantic設定"""

        frozen = True


class DocstringDetail(BaseModel):
    """
    docstringの詳細情報

    このクラスは、docstringの詳細な解析結果を保持します。
    """

    has_summary: bool = Field(description="概要行が存在するか")
    has_description: bool = Field(description="詳細説明が存在するか")
    has_attributes: bool = Field(description="Attributesセクションが存在するか")
    has_args: bool = Field(description="Argsセクションが存在するか")
    has_returns: bool = Field(description="Returnsセクションが存在するか")
    has_examples: bool = Field(description="Examplesセクションが存在するか")
    format_style: FormatStyle = Field(description="docstringフォーマット")
    line_count: NonNegativeInt = Field(description="docstringの行数")
    detail_score: Percentage = Field(description="詳細度スコア（0.0-1.0）")

    class Config:
        """Pydantic設定"""

        frozen = True


class DocumentationStatistics(BaseModel):
    """
    ドキュメント統計情報

    このクラスは、プロジェクト全体のドキュメント統計を保持します。
    """

    total_types: NonNegativeInt = Field(description="型定義の総数")
    documented_types: NonNegativeInt = Field(description="docstringが存在する型の数")
    undocumented_types: NonNegativeInt = Field(
        description="docstringが存在しない型の数"
    )
    implementation_rate: Percentage = Field(description="実装率（0.0-1.0）")
    minimal_docstrings: NonNegativeInt = Field(
        description="最低限のdocstring（1行のみ）の数"
    )
    detailed_docstrings: NonNegativeInt = Field(description="詳細なdocstringの数")
    detail_rate: Percentage = Field(description="詳細度率（0.0-1.0）")
    avg_docstring_lines: float = Field(description="平均docstring行数")
    quality_score: Percentage = Field(description="総合品質スコア（実装率 × 詳細度）")
    by_level: dict[TypeLevel, dict[str, NonNegativeInt]] = Field(
        description="レベル別のdocstring統計（カウント値のみ）"
    )
    by_level_avg_lines: dict[TypeLevel, float] = Field(
        description="レベル別の平均docstring行数"
    )
    by_format: dict[FormatStyle, NonNegativeInt] = Field(
        description="フォーマット別のdocstring数"
    )

    class Config:
        """Pydantic設定"""

        frozen = True


class TypeLevelInfo(BaseModel):
    """
    型レベル別の統計情報

    このクラスは、特定の型レベルに関する統計情報を保持します。
    """

    level: TypeLevel = Field(description="型レベル")
    count: NonNegativeInt = Field(description="型定義の数")
    documented_count: NonNegativeInt = Field(description="ドキュメント付きの型定義数")
    avg_docstring_lines: float = Field(description="平均docstring行数")
    upgrade_candidates: NonNegativeInt = Field(description="レベルアップ候補の数")
    keep_as_is_count: NonNegativeInt = Field(description="現状維持指定の数")

    class Config:
        """Pydantic設定"""

        frozen = True


class FileAnalysisResult(BaseModel):
    """
    ファイル解析結果

    このクラスは、単一ファイルの解析結果を保持します。
    """

    file_path: ValidatedFilePath = Field(description="解析対象のファイルパス")
    type_definitions: list[TypeDefinition] = Field(
        default_factory=list, description="検出された型定義のリスト"
    )
    total_types: NonNegativeInt = Field(description="型定義の総数")
    documented_types: NonNegativeInt = Field(description="ドキュメント付き型定義数")
    analysis_time_ms: float = Field(description="解析時間（ミリ秒）")
    has_errors: bool = Field(description="解析エラーがあるかどうか")
    error_messages: list[str] = Field(
        default_factory=list, description="エラーメッセージのリスト"
    )

    class Config:
        """Pydantic設定"""

        frozen = True


class ProjectAnalysisResult(BaseModel):
    """
    プロジェクト全体の解析結果

    このクラスは、プロジェクト全体の解析結果を保持します。
    """

    project_path: ValidatedFilePath = Field(description="プロジェクトのルートパス")
    total_files: PositiveInt = Field(description="解析対象のファイル総数")
    analyzed_files: PositiveInt = Field(description="解析完了したファイル数")
    failed_files: PositiveInt = Field(description="解析失敗したファイル数")
    all_type_definitions: list[TypeDefinition] = Field(
        default_factory=list, description="全型定義のリスト"
    )
    documentation_stats: DocumentationStatistics = Field(
        description="ドキュメント統計情報"
    )
    level_stats: dict[TypeLevel, TypeLevelInfo] = Field(
        description="レベル別の統計情報"
    )
    total_analysis_time_ms: float = Field(description="総解析時間（ミリ秒）")
    analysis_timestamp: str = Field(description="解析実行時刻（ISO形式）")

    class Config:
        """Pydantic設定"""

        frozen = True


class AnalysisConfig(BaseModel):
    """
    型解析の設定

    このクラスは、型解析処理の設定を管理します。
    """

    include_patterns: list[str] = Field(
        default_factory=lambda: ["*.py"], description="解析対象のファイルパターン"
    )
    exclude_patterns: list[str] = Field(
        default_factory=lambda: ["test_*", "__pycache__", "*.pyc"],
        description="除外対象のパターン",
    )
    max_file_size: PositiveInt = Field(  # type: ignore[assignment]
        default=10 * 1024 * 1024, description="処理可能な最大ファイルサイズ（バイト）"
    )
    max_files: PositiveInt | None = Field(
        default=None, description="最大処理ファイル数（Noneで無制限）"
    )
    analyze_docstrings: bool = Field(default=True, description="docstringも解析するか")
    analyze_dependencies: bool = Field(default=True, description="依存関係も解析するか")
    detect_type_levels: bool = Field(default=True, description="型レベルを検出するか")

    class Config:
        """Pydantic設定"""

        frozen = True


class QualityMetrics(BaseModel):
    """
    品質指標

    このクラスは、コード品質の各種指標を保持します。
    """

    overall_score: Percentage = Field(description="総合スコア（0.0-1.0）")
    type_coverage: Percentage = Field(description="型定義カバー率")
    documentation_coverage: Percentage = Field(description="ドキュメントカバー率")
    type_level_balance: Percentage = Field(description="型レベルバランススコア")
    maintainability_score: Percentage = Field(description="保守性スコア")
    complexity_score: Percentage = Field(description="複雑度スコア")

    class Config:
        """Pydantic設定"""

        frozen = True


class TypeUpgradeSuggestion(BaseModel):
    """
    型レベルアップの提案

    このクラスは、型定義のレベルアップ提案情報を保持します。
    """

    type_name: TypeName = Field(description="対象の型名")
    current_level: TypeLevel = Field(description="現在のレベル")
    suggested_level: TypeLevel = Field(description="提案レベル")
    reason: str = Field(description="提案理由")
    priority: Literal["high", "medium", "low"] = Field(description="優先度")
    effort_estimate: Literal["small", "medium", "large"] = Field(
        description="実装工数の見積もり"
    )

    class Config:
        """Pydantic設定"""

        frozen = True
