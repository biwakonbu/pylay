"""
ReviewProviderの型定義モジュール

docs/typing-rule.md の原則に従い、primitive型を直接使わず、
ドメイン特有の型を定義します。

3つのレベル:
- Level 1: type エイリアス（制約なし、単純な意味付け）
- Level 2: Annotated + AfterValidator（制約付き、NewType代替）
- Level 3: BaseModel（複雑なドメイン型・ビジネスロジック）
"""

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

# =============================================================================
# Level 1: type エイリアス（制約なし、単純な意味付け）
# =============================================================================

type ProviderName = str
"""レビュープロバイダー名（claudecode, cursor, codex, coderabbit, generic）"""

type ReviewTaskId = str
"""レビュータスクの一意識別子"""

type ReviewCommentId = str
"""レビューコメントの一意識別子"""

type FilePath = str
"""ファイルパス"""

type LineNumber = int
"""行番号（1以上）"""

type ColumnNumber = int
"""列番号（1以上）"""

type SeverityLevel = Literal["error", "warning", "info", "suggestion"]
"""重要度レベル"""

type ReviewStatus = Literal["pending", "in_progress", "completed", "failed"]
"""レビューステータス"""

type ProviderConfigPath = str
"""プロバイダー設定ファイルのパス"""

type SystemPrompt = str
"""システムプロンプト内容"""

type UserPrompt = str
"""ユーザープロンプト内容"""

type CommandName = str
"""コマンド名"""

type ToolName = str
"""ツール名"""

type VerificationResult = Literal["passed", "failed", "skipped"]
"""検証結果"""

type CodeBlock = str
"""コードブロック内容"""

type IssueDescription = str
"""問題の説明"""

type Suggestion = str
"""提案内容"""

type FixCommand = str
"""修正コマンド"""

type TaskTitle = str
"""タスクのタイトル"""

type TaskDescription = str
"""タスクの詳細説明"""

type ChangeType = Literal["add", "modify", "delete", "move", "rename"]
"""変更の種類"""

# =============================================================================
# Level 2: Annotated + AfterValidator（制約付き、NewType代替）
# =============================================================================


def validate_provider_name(v: str) -> str:
    """プロバイダー名のバリデーション"""
    valid_providers = {"claudecode", "cursor", "codex", "coderabbit", "generic"}
    if v not in valid_providers:
        raise ValueError(f"無効なプロバイダー名です: {v}。有効な値: {valid_providers}")
    return v


type ValidatedProviderName = Annotated[str, AfterValidator(validate_provider_name)]
"""バリデーション済みプロバイダー名"""


def validate_severity_level(v: str) -> str:
    """重要度レベルのバリデーション"""
    valid_levels = {"error", "warning", "info", "suggestion"}
    if v not in valid_levels:
        raise ValueError(f"無効な重要度レベルです: {v}。有効な値: {valid_levels}")
    return v


type ValidatedSeverityLevel = Annotated[str, AfterValidator(validate_severity_level)]
"""バリデーション済み重要度レベル"""


def validate_review_status(v: str) -> str:
    """レビューステータスのバリデーション"""
    valid_statuses = {"pending", "in_progress", "completed", "failed"}
    if v not in valid_statuses:
        raise ValueError(
            f"無効なレビューステータスです: {v}。有効な値: {valid_statuses}"
        )
    return v


type ValidatedReviewStatus = Annotated[str, AfterValidator(validate_review_status)]
"""バリデーション済みレビューステータス"""


def validate_verification_result(v: str) -> str:
    """検証結果のバリデーション"""
    valid_results = {"passed", "failed", "skipped"}
    if v not in valid_results:
        raise ValueError(f"無効な検証結果です: {v}。有効な値: {valid_results}")
    return v


type ValidatedVerificationResult = Annotated[
    str, AfterValidator(validate_verification_result)
]
"""バリデーション済み検証結果"""


def validate_positive_line_number(v: int) -> int:
    """正の行番号のバリデーション"""
    if v < 1:
        raise ValueError("行番号は1以上である必要があります")
    return v


type ValidatedLineNumber = Annotated[
    int, AfterValidator(validate_positive_line_number), Field(ge=1)
]
"""バリデーション済み行番号"""


def validate_positive_column_number(v: int) -> int:
    """正の列番号のバリデーション"""
    if v < 1:
        raise ValueError("列番号は1以上である必要があります")
    return v


type ValidatedColumnNumber = Annotated[
    int, AfterValidator(validate_positive_column_number), Field(ge=1)
]
"""バリデーション済み列番号"""

# =============================================================================
# Level 3: BaseModel（複雑なドメイン型・ビジネスロジック）
# =============================================================================


class ProviderConfig(BaseModel):
    """
    プロバイダー設定の構造化型

    各プロバイダーの設定情報を管理します。
    """

    model_config = ConfigDict(frozen=True)

    provider: ValidatedProviderName = Field(..., description="プロバイダー名")
    config_path: ProviderConfigPath | None = Field(
        default=None, description="設定ファイルパス"
    )
    enabled: bool = Field(default=True, description="有効化フラグ")
    timeout: int = Field(
        default=300, ge=1, le=3600, description="タイムアウト時間（秒）"
    )

    def is_enabled(self) -> bool:
        """プロバイダーが有効かを判定"""
        return self.enabled

    def get_config_path(self) -> ProviderConfigPath | None:
        """設定ファイルパスを取得"""
        return self.config_path


class ReviewLocation(BaseModel):
    """
    レビュー対象の場所を表す構造化型

    ファイルの特定の場所を特定するための情報。
    """

    model_config = ConfigDict(frozen=True)

    file_path: FilePath = Field(..., description="ファイルパス")
    line_number: ValidatedLineNumber = Field(..., description="行番号")
    column_number: ValidatedColumnNumber | None = Field(
        default=None, description="列番号（オプション）"
    )

    def __str__(self) -> str:
        """文字列表現"""
        if self.column_number is not None:
            return f"{self.file_path}:{self.line_number}:{self.column_number}"
        return f"{self.file_path}:{self.line_number}"

    def is_same_file(self, other: "ReviewLocation") -> bool:
        """同じファイルかを判定"""
        return self.file_path == other.file_path


class ReviewComment(BaseModel):
    """
    レビューコメントの構造化型

    コードレビューの指摘事項を表します。
    """

    model_config = ConfigDict(frozen=True)

    id: ReviewCommentId = Field(..., description="コメントID")
    location: ReviewLocation = Field(..., description="指摘場所")
    severity: ValidatedSeverityLevel = Field(..., description="重要度")
    message: str = Field(..., description="コメントメッセージ")
    suggestion: Suggestion | None = Field(default=None, description="提案内容")
    code_block: CodeBlock | None = Field(default=None, description="関連コードブロック")

    def has_suggestion(self) -> bool:
        """提案があるかを判定"""
        return self.suggestion is not None

    def has_code_block(self) -> bool:
        """コードブロックがあるかを判定"""
        return self.code_block is not None

    def is_error(self) -> bool:
        """エラーかを判定"""
        return self.severity == "error"

    def is_warning(self) -> bool:
        """警告かを判定"""
        return self.severity == "warning"


class ReviewTask(BaseModel):
    """
    レビュータスクの構造化型

    レビューコメントから生成される修正タスク。
    """

    model_config = ConfigDict(frozen=True)

    id: ReviewTaskId = Field(..., description="タスクID")
    title: TaskTitle = Field(..., description="タスクタイトル")
    description: TaskDescription = Field(..., description="タスク詳細")
    comment_id: ReviewCommentId = Field(..., description="関連コメントID")
    location: ReviewLocation = Field(..., description="修正対象場所")
    change_type: ChangeType = Field(..., description="変更の種類")
    fix_command: FixCommand | None = Field(default=None, description="修正コマンド")
    status: ValidatedReviewStatus = Field(
        default="pending", description="タスクステータス"
    )

    def is_pending(self) -> bool:
        """保留中かを判定"""
        return self.status == "pending"

    def is_completed(self) -> bool:
        """完了済みかを判定"""
        return self.status == "completed"

    def can_execute(self) -> bool:
        """実行可能かを判定"""
        return self.fix_command is not None and self.status == "pending"


class ReviewSummary(BaseModel):
    """
    レビュー結果のサマリー構造化型

    レビュー全体の統計情報と結果。
    """

    model_config = ConfigDict(frozen=True)

    total_comments: int = Field(..., description="コメント総数")
    error_count: int = Field(..., description="エラー数")
    warning_count: int = Field(..., description="警告数")
    info_count: int = Field(..., description="情報数")
    suggestion_count: int = Field(..., description="提案数")
    total_tasks: int = Field(..., description="タスク総数")
    completed_tasks: int = Field(..., description="完了タスク数")
    failed_tasks: int = Field(..., description="失敗タスク数")

    def get_completion_rate(self) -> float:
        """完了率を取得"""
        if self.total_tasks == 0:
            return 0.0
        return self.completed_tasks / self.total_tasks

    def has_issues(self) -> bool:
        """問題があるかを判定"""
        return self.error_count > 0 or self.failed_tasks > 0

    def get_issue_summary(self) -> str:
        """問題の概要を取得"""
        if not self.has_issues():
            return "問題なし"

        issues = []
        if self.error_count > 0:
            issues.append(f"エラー: {self.error_count}")
        if self.failed_tasks > 0:
            issues.append(f"失敗タスク: {self.failed_tasks}")

        return ", ".join(issues)
