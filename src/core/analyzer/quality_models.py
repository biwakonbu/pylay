"""
品質チェック関連のデータモデル

品質チェックの結果を表現するためのPydanticモデルを提供します。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import BaseModel, Field

from src.core.schemas.pylay_config import (
    LevelThresholds,
    SeverityLevel,
)

if TYPE_CHECKING:
    from src.core.analyzer.type_level_models import TypeStatistics

# 深刻度の型定義
type SeverityName = Literal["advice", "warning", "error"]


class CodeLocation(BaseModel):
    """コードの位置情報"""

    file: Path = Field(description="ファイルパス")
    line: int = Field(description="行番号")
    column: int = Field(description="列番号")
    context_before: list[str] = Field(
        default_factory=list, description="前後のコンテキスト行"
    )
    code: str = Field(default="", description="問題のあるコード行")
    context_after: list[str] = Field(
        default_factory=list, description="後方のコンテキスト行"
    )


class QualityIssue(BaseModel):
    """品質問題の情報"""

    issue_type: str = Field(description="問題の種類")
    severity: SeverityName = Field(default="advice", description="深刻度レベル")
    message: str = Field(description="問題の説明")
    location: CodeLocation | None = Field(default=None, description="問題の場所")
    suggestion: str = Field(description="簡単な解決策の提案")
    improvement_plan: str = Field(description="詳細な改善プラン")
    # グルーピング用の追加情報
    recommended_type: str | None = Field(
        default=None, description="推奨される型（Pydantic型など）"
    )
    primitive_type: str | None = Field(
        default=None, description="検出されたprimitive型"
    )
    # 優先度情報（自動計算）
    priority_score: int = Field(
        default=0, description="優先度スコア（低いほど優先度高）"
    )
    impact_score: int = Field(default=1, description="影響度スコア（高いほど影響大）")
    difficulty_score: int = Field(default=1, description="修正難易度（低いほど簡単）")


class QualityCheckResult(BaseModel):
    """品質チェックの結果"""

    # 全体統計
    total_issues: int = Field(ge=0, description="総問題数")
    error_count: int = Field(ge=0, description="エラー数")
    warning_count: int = Field(ge=0, description="警告数")
    advice_count: int = Field(ge=0, description="アドバイス数")
    has_errors: bool = Field(description="エラーが存在するか")
    overall_score: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        description="全体スコア（0.0〜1.0）"
    )

    # 問題リスト
    issues: list[QualityIssue] = Field(
        default_factory=list, description="検出された問題リスト"
    )

    # 統計情報（参照用）
    statistics: TypeStatistics = Field(description="型統計情報")
    thresholds: LevelThresholds = Field(description="使用された閾値設定")
    severity_levels: list[SeverityLevel] = Field(description="深刻度レベル設定")

    def get_issues_by_severity(self, severity: SeverityName) -> list[QualityIssue]:
        """深刻度別の問題を取得"""
        return [issue for issue in self.issues if issue.severity == severity]

    def get_issues_by_type(self, issue_type: str) -> list[QualityIssue]:
        """種類別の問題を取得"""
        return [issue for issue in self.issues if issue.issue_type == issue_type]


# Pydantic V2の前方参照を解決
from src.core.analyzer.type_level_models import TypeStatistics  # noqa: E402

QualityCheckResult.model_rebuild()
