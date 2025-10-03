"""
型定義レベル分析のためのデータ構造

Level 1/2/3の型定義とドキュメント品質の分析・監視機能で
使用されるモデルを定義します。
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ========================================
# 型定義情報
# ========================================


class TypeDefinition(BaseModel):
    """型定義の情報

    Attributes:
        name: 型の名前
        level: 型定義レベル（level1/level2/level3/other）
        file_path: ファイルパス
        line_number: 行番号
        definition: 型定義のコード
        category: 型のカテゴリ（type_alias/annotated/basemodel/class/dataclass等）
        docstring: docstring（存在する場合）
        has_docstring: docstringが存在するか
        docstring_lines: docstringの行数
        target_level: docstringで指定された目標レベル
            （@target-level: level1/level2/level3）
        keep_as_is: 現状維持フラグ（@keep-as-is: trueの場合はレベルアップ推奨しない）
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    name: str
    level: Literal["level1", "level2", "level3", "other"]
    file_path: str
    line_number: int
    definition: str
    category: str
    docstring: str | None = None
    has_docstring: bool = False
    docstring_lines: int = 0
    target_level: Literal["level1", "level2", "level3"] | None = None
    keep_as_is: bool = False


# ========================================
# ドキュメント解析
# ========================================


class DocstringDetail(BaseModel):
    """docstringの詳細情報

    Attributes:
        has_summary: 概要行が存在するか
        has_description: 詳細説明が存在するか
        has_attributes: Attributesセクションが存在するか
        has_args: Argsセクションが存在するか
        has_returns: Returnsセクションが存在するか
        has_examples: Examplesセクションが存在するか
        format_style: docstringフォーマット
        line_count: docstringの行数
        detail_score: 詳細度スコア（0.0-1.0）
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    has_summary: bool
    has_description: bool
    has_attributes: bool
    has_args: bool
    has_returns: bool
    has_examples: bool
    format_style: Literal["google", "numpy", "restructured", "unknown"]
    line_count: int
    detail_score: float = Field(ge=0.0, le=1.0)


class DocumentationStatistics(BaseModel):
    """ドキュメント統計情報

    Attributes:
        total_types: 型定義の総数
        documented_types: docstringが存在する型の数
        undocumented_types: docstringが存在しない型の数
        implementation_rate: 実装率（0.0-1.0）
        minimal_docstrings: 最低限のdocstring（1行のみ）の数
        detailed_docstrings: 詳細なdocstringの数
        detail_rate: 詳細度率（0.0-1.0）
        avg_docstring_lines: 平均docstring行数
        quality_score: 総合品質スコア（実装率 × 詳細度）
        by_level: レベル別のdocstring統計
        by_format: フォーマット別のdocstring数
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    total_types: int
    documented_types: int
    undocumented_types: int
    implementation_rate: float = Field(ge=0.0, le=1.0)

    minimal_docstrings: int
    detailed_docstrings: int
    detail_rate: float = Field(ge=0.0, le=1.0)

    avg_docstring_lines: float
    quality_score: float = Field(ge=0.0, le=1.0)

    by_level: dict[str, dict[str, float]]
    by_format: dict[str, int]


class DocstringRecommendation(BaseModel):
    """docstring改善推奨

    Attributes:
        type_name: 型名
        file_path: ファイルパス
        line_number: 行番号
        current_status: 現在の状態
        recommended_action: 推奨アクション
        priority: 優先度
        reasons: 推奨理由
        suggested_template: 推奨docstringテンプレート
        detail_gaps: 不足しているセクション
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    type_name: str
    file_path: str
    line_number: int
    current_status: Literal["missing", "minimal", "partial", "complete"]
    recommended_action: Literal["add", "expand", "reformat", "none"]
    priority: Literal["high", "medium", "low"]
    reasons: list[str]
    suggested_template: str | None = None
    detail_gaps: list[str] = Field(default_factory=list)


# ========================================
# 統計情報
# ========================================


class TypeStatistics(BaseModel):
    """型定義の統計情報

    Attributes:
        total_count: 型定義の総数
        level1_count: Level 1の数
        level2_count: Level 2の数
        level3_count: Level 3の数
        other_count: その他の数
        level1_ratio: Level 1の比率
        level2_ratio: Level 2の比率
        level3_ratio: Level 3の比率
        other_ratio: その他の比率
        by_directory: ディレクトリ別の統計
        by_category: カテゴリ別の統計
        documentation: ドキュメント統計
        primitive_usage_count: primitive型の直接使用数
        deprecated_typing_count: 非推奨typing使用数
        primitive_usage_ratio: primitive型の直接使用比率
        deprecated_typing_ratio: 非推奨typing使用比率
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    total_count: int
    level1_count: int
    level2_count: int
    level3_count: int
    other_count: int
    level1_ratio: float = Field(ge=0.0, le=1.0)
    level2_ratio: float = Field(ge=0.0, le=1.0)
    level3_ratio: float = Field(ge=0.0, le=1.0)
    other_ratio: float = Field(ge=0.0, le=1.0)
    by_directory: dict[str, dict[str, int]]
    by_category: dict[str, int]
    documentation: DocumentationStatistics
    primitive_usage_count: int = 0
    deprecated_typing_count: int = 0
    primitive_usage_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    deprecated_typing_ratio: float = Field(default=0.0, ge=0.0, le=1.0)


# ========================================
# 型レベルアップ推奨
# ========================================


class UpgradeRecommendation(BaseModel):
    """型レベルアップ・ダウンの推奨事項

    Attributes:
        type_name: 型名
        current_level: 現在のレベル
        recommended_level: 推奨レベル（level1/level2/level3/investigate）
        confidence: 確信度（0.0-1.0）
        reasons: 推奨理由
        suggested_validator: Level 2への昇格時のバリデータコード
        suggested_implementation: Level 3への昇格時の実装例
        priority: 優先度
        is_downgrade: レベルダウン推奨の場合True
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    type_name: str
    current_level: Literal["level1", "level2", "level3", "other"]
    recommended_level: Literal["level1", "level2", "level3", "investigate"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: list[str]
    suggested_validator: str | None = None
    suggested_implementation: str | None = None
    priority: Literal["high", "medium", "low"]
    is_downgrade: bool = False


# ========================================
# 分析レポート
# ========================================


class TypeAnalysisReport(BaseModel):
    """型定義分析レポート

    Attributes:
        statistics: 統計情報
        type_definitions: 型定義リスト
        recommendations: 一般的な推奨事項
        upgrade_recommendations: 型レベルアップ推奨
        docstring_recommendations: docstring改善推奨
        threshold_ratios: 警告閾値（level1_max/level2_min/level3_min）
        deviation_from_threshold: 警告閾値との乖離
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    statistics: TypeStatistics
    type_definitions: list[TypeDefinition]
    recommendations: list[str]
    upgrade_recommendations: list[UpgradeRecommendation]
    docstring_recommendations: list[DocstringRecommendation]
    threshold_ratios: dict[str, float]
    deviation_from_threshold: dict[str, float]
