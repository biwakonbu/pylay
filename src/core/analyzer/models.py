"""
アナライザー内部モデル定義

Pydantic BaseModelを活用した型安全な内部状態管理を提供します。
"""

from pathlib import Path
from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict

from src.core.schemas.graph_types import GraphNode, GraphEdge
from src.core.schemas.pylay_config import PylayConfig


class InferResult(BaseModel):
    """
    型推論結果を表すモデル

    Attributes:
        variable_name: 変数名
        inferred_type: 推論された型
        confidence: 信頼度（0.0-1.0）
        source_file: ソースファイルパス（オプション）
        line_number: 行番号（オプション）
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    variable_name: str = Field(..., min_length=1)
    inferred_type: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
    source_file: str | None = None
    line_number: int | None = Field(default=None, ge=1)

    def is_high_confidence(self) -> bool:
        """信頼度が高いか判定（>= 0.8）"""
        return self.confidence >= 0.8


class AnalyzerState(BaseModel):
    """
    Analyzerの内部状態を管理するモデル

    Attributes:
        nodes: ノードキャッシュ
        edges: エッジキャッシュ
        visited_nodes: 訪問済みノード
        processing_stack: 処理中ノード（循環参照防止）
    """

    model_config = ConfigDict(
        frozen=False, extra="forbid", arbitrary_types_allowed=True
    )

    nodes: dict[str, GraphNode] = Field(default_factory=dict)
    edges: dict[str, GraphEdge] = Field(default_factory=dict)
    visited_nodes: set[str] = Field(default_factory=set)
    processing_stack: set[str] = Field(default_factory=set)

    def reset(self) -> None:
        """状態をリセット"""
        self.nodes.clear()
        self.edges.clear()
        self.visited_nodes.clear()
        self.processing_stack.clear()

    def is_processing(self, node_name: str) -> bool:
        """ノードが処理中か確認"""
        return node_name in self.processing_stack

    def start_processing(self, node_name: str) -> None:
        """ノードの処理を開始"""
        self.processing_stack.add(node_name)

    def finish_processing(self, node_name: str) -> None:
        """ノードの処理を完了"""
        self.processing_stack.discard(node_name)


class ParseContext(BaseModel):
    """
    AST走査のコンテキスト情報

    Attributes:
        file_path: 解析対象ファイルパス
        module_name: モジュール名
        current_class: 現在処理中のクラス名
        current_function: 現在処理中の関数名
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    file_path: Path
    module_name: str = Field(..., min_length=1)
    current_class: str | None = None
    current_function: str | None = None

    def in_class_context(self) -> bool:
        """クラスコンテキスト内か判定"""
        return self.current_class is not None

    def in_function_context(self) -> bool:
        """関数コンテキスト内か判定"""
        return self.current_function is not None

    def get_qualified_name(self, name: str) -> str:
        """修飾名を取得"""
        if self.current_class:
            return f"{self.current_class}.{name}"
        return name


class InferenceConfig(BaseModel):
    """
    型推論設定の強い型定義

    Attributes:
        infer_level: 推論レベル
        max_depth: 最大探索深度
        enable_mypy: mypy統合を有効化
        mypy_flags: mypyフラグ
        timeout: タイムアウト（秒）
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    infer_level: Literal["loose", "normal", "strict"] = "normal"
    max_depth: int = Field(default=10, ge=1, le=100)
    enable_mypy: bool = True
    mypy_flags: list[str] = Field(
        default_factory=lambda: ["--infer", "--dump-type-stats"]
    )
    timeout: int = Field(default=60, ge=1, le=600)

    def is_strict_mode(self) -> bool:
        """Strictモードか判定"""
        return self.infer_level == "strict"

    def is_loose_mode(self) -> bool:
        """Looseモードか判定"""
        return self.infer_level == "loose"

    def should_use_mypy(self) -> bool:
        """mypy使用すべきか判定"""
        return self.enable_mypy and self.infer_level != "loose"

    @classmethod
    def from_pylay_config(cls, config: "PylayConfig") -> "InferenceConfig":
        """PylayConfigから変換"""
        max_depth = getattr(config, "max_depth", 10)
        if not isinstance(max_depth, int) or max_depth < 1:
            max_depth = 10

        return cls(
            infer_level=config.infer_level,
            max_depth=max_depth,
            enable_mypy=config.infer_level != "loose",
        )


class MypyResult(BaseModel):
    """
    mypy実行結果

    Attributes:
        stdout: 標準出力
        stderr: 標準エラー
        return_code: 終了コード
        inferred_types: 推論された型情報
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    stdout: str
    stderr: str
    return_code: int
    inferred_types: dict[str, InferResult] = Field(default_factory=dict)

    def is_success(self) -> bool:
        """実行成功か判定"""
        return self.return_code == 0

    def has_inferred_types(self) -> bool:
        """推論結果があるか判定"""
        return len(self.inferred_types) > 0
