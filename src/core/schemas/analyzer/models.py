"""
アナライザーモデル定義

アナライザー関連のPydanticモデルを定義します。
"""

from pydantic import BaseModel, Field

from src.core.schemas.types import (
    CheckCount,
    CheckResultData,
    Code,
    Density,
    EdgeCount,
    FileOpenMode,
    FileSuffix,
    InferLevel,
    LineNumber,
    MaxDepth,
    Message,
    NodeCount,
    NodeId,
    Severity,
    ToolName,
    VisualizeFlag,
)


class CheckSummary(BaseModel):
    """analyze_issues.pyのサマリー型"""

    total_checks: CheckCount
    successful_checks: CheckCount
    failed_checks: CheckCount
    checks_with_issues: CheckCount
    results: list[CheckResultData]


class MypyError(BaseModel):
    """mypyエラーの構造化型"""

    line: LineNumber
    message: Message
    severity: Severity


class Issue(BaseModel):
    """ツール出力のIssue型"""

    tool: ToolName
    line: LineNumber
    message: Message
    severity: Severity


class GraphMetrics(BaseModel):
    """グラフメトリクスの型"""

    node_count: NodeCount
    edge_count: EdgeCount
    density: Density
    cycles: list[list[NodeId]]


class TempFileConfig(BaseModel):
    """一時ファイル設定のPydanticモデル

    Attributes:
        code: 一時ファイルに書き込むコード内容
        suffix: ファイルの拡張子（デフォルト: ".py"）
        mode: ファイルオープンモード（デフォルト: "w"）
    """

    code: Code = Field(
        ..., description="一時ファイルに書き込むコード内容", min_length=1
    )
    suffix: FileSuffix = Field(default=".py", description="ファイルの拡張子")
    mode: FileOpenMode = Field(
        default="w", description="ファイルオープンモード", pattern="^[wab]\\+?$"
    )


class AnalyzerConfig(BaseModel):
    """Analyzer設定の型（PylayConfig拡張）

    Analyzer固有の設定を管理するPylayConfigの拡張クラスです。
    """

    infer_level: InferLevel
    max_depth: MaxDepth
    visualize: VisualizeFlag


__all__ = [
    "CheckSummary",
    "MypyError",
    "Issue",
    "GraphMetrics",
    "TempFileConfig",
    "AnalyzerConfig",
]
