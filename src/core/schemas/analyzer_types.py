"""
アナライザー関連の型定義

mypy strict準拠のためのTypedDictと型定義を提供します。
Pydanticモデルは models.py から再エクスポートします。
"""

from typing import TypedDict, Literal
from enum import Enum

# Pydanticモデルを再エクスポート
from src.core.analyzer.models import InferResult, MypyResult  # noqa: F401


class RelationType(str, Enum):
    """関係の種類を定義する列挙型（graph_types.pyと統合可能）"""

    DEPENDS_ON = "depends_on"
    INHERITS_FROM = "inherits_from"
    REFERENCES = "references"
    USES = "uses"
    RETURNS = "returns"
    CALLS = "calls"


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


class TempFileConfig(TypedDict):
    """一時ファイル設定の型"""

    code: str
    suffix: str
    mode: str


class AnalyzerConfig(TypedDict):
    """Analyzer設定の型（PylayConfig拡張）

    Analyzer固有の設定を管理するPylayConfigの拡張クラスです。
    """

    infer_level: Literal["loose", "normal", "strict"]
    max_depth: int
    visualize: bool
