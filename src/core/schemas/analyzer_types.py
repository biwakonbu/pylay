"""
アナライザー関連の型定義

mypy strict準拠のためのTypedDictと型定義を提供します。
Pydanticモデルは models.py から再エクスポートします。
"""

from typing import TypedDict, Literal
from pydantic import BaseModel, Field

# Pydanticモデルを再エクスポート（analyzer.models からの型参照用）
from src.core.analyzer.models import InferResult, MypyResult

# RelationTypeはgraph_types.pyに統合（重複排除）
from src.core.schemas.graph_types import RelationType

__all__ = ["InferResult", "MypyResult", "RelationType"]


class CheckSummary(TypedDict):
    """analyze_issues.pyのサマリー型"""

    total_checks: int
    successful_checks: int
    failed_checks: int
    checks_with_issues: int
    results: list[dict[str, object]]


class MypyError(TypedDict):
    """mypyエラーの構造化型"""

    line: int
    message: str
    severity: str


class Issue(TypedDict):
    """ツール出力のIssue型"""

    tool: str
    line: int
    message: str
    severity: str


class GraphMetrics(TypedDict):
    """グラフメトリクスの型"""

    node_count: int
    edge_count: int
    density: float
    cycles: list[list[str]]


class TempFileConfig(BaseModel):
    """一時ファイル設定のPydanticモデル

    Attributes:
        code: 一時ファイルに書き込むコード内容
        suffix: ファイルの拡張子（デフォルト: ".py"）
        mode: ファイルオープンモード（デフォルト: "w"）
    """

    code: str = Field(..., description="一時ファイルに書き込むコード内容", min_length=1)
    suffix: str = Field(default=".py", description="ファイルの拡張子")
    mode: str = Field(
        default="w", description="ファイルオープンモード", pattern="^[wab]\\+?$"
    )


class AnalyzerConfig(TypedDict):
    """Analyzer設定の型（PylayConfig拡張）

    Analyzer固有の設定を管理するPylayConfigの拡張クラスです。
    """

    infer_level: Literal["loose", "normal", "strict"]
    max_depth: int
    visualize: bool
