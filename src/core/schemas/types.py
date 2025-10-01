"""
ドメイン型定義モジュール

docs/typing-rule.md の原則1に従い、primitive型を直接使わず、
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

type NodeId = str
"""グラフノードの一意識別子"""

type ModuleName = str
"""Pythonモジュール名"""

type VariableName = str
"""変数名"""

type TypeName = str
"""型名"""

type QualifiedName = str
"""完全修飾名（例: module.ClassName.method）"""

type FilePath = str
"""ファイルパス"""

type NodeType = Literal[
    "class",
    "function",
    "module",
    "method",
    "variable",
    "inferred_variable",
    "imported_symbol",
    "function_call",
    "method_call",
    "attribute_access",
    "type_alias",
    "unknown",
]
"""ノードタイプ"""

type InferLevel = Literal["strict", "normal", "loose", "none"]
"""型推論レベル（strict, normal, loose, none）"""


def validate_index_filename(v: str) -> str:
    """インデックスファイル名のバリデーション"""
    if not v.endswith(".md"):
        raise ValueError("インデックスファイル名は.mdで終わる必要があります")
    return v


type IndexFilename = Annotated[str, AfterValidator(validate_index_filename)]
"""インデックスファイル名（.md拡張子必須）"""


def validate_layer_filename_template(v: str) -> str:
    """レイヤーファイル名テンプレートのバリデーション"""
    if not v.endswith(".md"):
        raise ValueError("レイヤーファイル名テンプレートは.mdで終わる必要があります")
    if "{layer}" not in v:
        raise ValueError(
            "レイヤーファイル名テンプレートには{layer}プレースホルダが必要です"
        )
    return v


type LayerFilenameTemplate = Annotated[
    str, AfterValidator(validate_layer_filename_template)
]
"""レイヤーファイル名テンプレート（.md拡張子と{layer}プレースホルダ必須）"""

type TypeSpecName = str
"""YAML型仕様の型名"""

type TypeSpecType = str
"""YAML型仕様の基本型（str, int, float, bool, list, dict, union）"""

type Description = str
"""説明文"""

type Code = str
"""ソースコード文字列"""

type FileSuffix = str
"""ファイル拡張子（例: .py, .txt）"""

type FileOpenMode = str
"""ファイルオープンモード（w, r, a, b等）"""

type GenerateMarkdownFlag = bool
"""Markdownドキュメント生成フラグ"""

type ExtractDepsFlag = bool
"""依存関係抽出フラグ"""

type CleanOutputDirFlag = bool
"""出力ディレクトリクリーンアップフラグ"""

type Timestamp = str
"""タイムスタンプ（ISO 8601形式）"""

type Version = str
"""バージョン文字列"""

type ToolName = str
"""ツール名（mypy, ruff等）"""

type Severity = str
"""エラーや警告の重要度"""

type Message = str
"""エラーメッセージや通知メッセージ"""

type CheckCount = int
"""チェック回数や統計カウント"""

type NodeCount = int
"""ノード数"""

type EdgeCount = int
"""エッジ数"""

type Density = float
"""グラフの密度"""

type VisualizeFlag = bool
"""可視化フラグ"""

type EnableMypyFlag = bool
"""mypy統合の有効化フラグ"""

type Timeout = int
"""タイムアウト時間（秒）"""

type ClassName = str
"""クラス名"""

type FunctionName = str
"""関数名"""

type StdOut = str
"""標準出力"""

type StdErr = str
"""標準エラー出力"""

type ReturnCode = int
"""終了コード"""

type RequiredFlag = bool
"""必須フラグ（型仕様で必須かどうか）"""

type AdditionalPropertiesFlag = bool
"""追加プロパティ許可フラグ"""

type GlobPattern = str
"""Globパターン（例: **/*.py, **/tests/**）"""

type LayerName = str
"""レイヤー名（primitives, domain, api, activity等）"""

type MethodName = str
"""メソッド名（get_primitive, get_domain等）"""

type MypyFlag = str
"""mypyコマンドラインフラグ（--strict, --no-implicit-optional等）"""

type CyclePath = list[str]
"""循環依存のパス（ノードIDのリスト）"""


# =============================================================================
# Level 2: Annotated + AfterValidator（制約付き、NewType代替）
# =============================================================================


def validate_directory_path(v: str) -> str:
    """
    ディレクトリパスのバリデーション

    - 空文字列チェック
    - 相対パス正規化（末尾スラッシュ除去、./正規化）
    - 禁止文字チェック（null byte等）

    Note:
        存在チェックは行わない（設定時点では未作成の場合があるため）
        実際の使用時に get_absolute_paths() で絶対パス化と存在確認を行う
    """
    if not v:
        raise ValueError("ディレクトリパスは空にできません")

    # null byteチェック（セキュリティ）
    if "\0" in v:
        raise ValueError("ディレクトリパスにnull byteを含むことはできません")

    # 相対パスの正規化（末尾スラッシュ除去、冗長な./ 除去）
    normalized = v.rstrip("/")
    if normalized.startswith("./"):
        normalized = normalized[2:]

    # 空になった場合は "." にフォールバック
    if not normalized:
        normalized = "."

    return normalized


type DirectoryPath = Annotated[
    str, AfterValidator(validate_directory_path), Field(min_length=1)
]
"""
ディレクトリパス（相対パス）

- 空文字列不可
- 末尾スラッシュは自動削除
- 禁止文字（null byte等）をチェック
- 存在チェックは get_absolute_paths() で実施
"""


def validate_max_depth(v: int) -> int:
    """最大深度のバリデーション"""
    if v < 1 or v > 100:
        raise ValueError("深さは1〜100の範囲")
    return v


type MaxDepth = Annotated[int, AfterValidator(validate_max_depth), Field(ge=1, le=100)]
"""再帰解析の最大深度（1〜100）"""


def validate_weight(v: float) -> float:
    """重みのバリデーション"""
    if v < 0.0 or v > 1.0:
        raise ValueError("重みは0.0〜1.0の範囲")
    return v


type Weight = Annotated[float, AfterValidator(validate_weight), Field(ge=0.0, le=1.0)]
"""エッジの重み（0.0〜1.0）"""

type ConfidenceScore = Weight
"""信頼度スコア（0.0〜1.0）- Weightと同じ制約"""


def validate_line_number(v: int) -> int:
    """行番号のバリデーション"""
    if v < 1:
        raise ValueError("行番号は1以上")
    return v


type LineNumber = Annotated[int, AfterValidator(validate_line_number), Field(ge=1)]
"""ソースコード行番号（1以上）"""


# =============================================================================
# Level 3: BaseModel（複雑なドメイン型・ビジネスロジック）
# =============================================================================


class NodeAttributes(BaseModel):
    """
    GraphNodeの属性を表す構造化型

    primitive型の dict[str, str | int | float | bool] を
    構造化されたドメイン型に置き換えます。
    """

    model_config = ConfigDict(extra="forbid")

    custom_data: dict[str, str | int | float | bool] = Field(
        default_factory=dict, description="カスタム属性データ"
    )

    def get_string_value(self, key: str) -> str | None:
        """文字列値を取得"""
        value = self.custom_data.get(key)
        return str(value) if value is not None else None

    def get_int_value(self, key: str) -> int | None:
        """整数値を取得"""
        value = self.custom_data.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        return None

    def get_float_value(self, key: str) -> float | None:
        """浮動小数点値を取得"""
        value = self.custom_data.get(key)
        if isinstance(value, int | float) and not isinstance(value, bool):
            return float(value)
        return None

    def get_bool_value(self, key: str) -> bool | None:
        """真偽値を取得"""
        value = self.custom_data.get(key)
        if isinstance(value, bool):
            return value
        return None

    def has_key(self, key: str) -> bool:
        """キーが存在するか確認"""
        return key in self.custom_data

    def keys(self) -> list[str]:
        """全てのキーを取得"""
        return list(self.custom_data.keys())

    def __contains__(self, key: str) -> bool:
        """dict互換: in演算子のサポート"""
        return key in self.custom_data

    def __getitem__(self, key: str) -> str | int | float | bool:
        """dict互換: []演算子のサポート"""
        return self.custom_data[key]

    def __eq__(self, other: object) -> bool:
        """等価性チェック（dict比較にも対応）"""
        if isinstance(other, dict):
            return self.custom_data == other
        if isinstance(other, NodeAttributes):
            return self.custom_data == other.custom_data
        return False

    def __hash__(self) -> int:
        """ハッシュ値を返す"""
        return hash(tuple(sorted(self.custom_data.items())))


class GraphMetadata(BaseModel):
    """
    グラフのメタデータを表す構造化型

    primitive型の dict[str, object] を構造化されたドメイン型に置き換えます。
    """

    model_config = ConfigDict(extra="forbid")

    version: Version = Field(default="1.0", description="グラフのバージョン")
    created_at: Timestamp | None = Field(
        default=None, description="作成日時（ISO 8601形式）"
    )
    cycles: list[list[NodeId]] = Field(
        default_factory=list, description="検出された循環依存のリスト"
    )
    statistics: dict[str, int] = Field(
        default_factory=dict, description="統計情報（ノード数、エッジ数など）"
    )
    custom_fields: dict[str, object] = Field(
        default_factory=dict, description="カスタムフィールド"
    )

    def has_cycles(self) -> bool:
        """循環依存が存在するか確認"""
        return len(self.cycles) > 0

    def get_cycle_count(self) -> int:
        """循環依存の数を取得"""
        return len(self.cycles)

    def get_statistic(self, key: str) -> int | None:
        """統計情報を取得"""
        return self.statistics.get(key)

    def set_statistic(self, key: str, value: int) -> None:
        """統計情報を設定"""
        self.statistics[key] = value

    def get(self, key: str, default: object | None = None) -> object | None:
        """カスタムフィールドから値を取得（dict互換）"""
        return self.custom_fields.get(key, default)

    def __contains__(self, key: str) -> bool:
        """dict互換: in演算子のサポート"""
        return key in self.custom_fields

    def __getitem__(self, key: str) -> object:
        """dict互換: []演算子のサポート"""
        return self.custom_fields[key]

    def __eq__(self, other: object) -> bool:
        """等価性チェック（dict比較にも対応）"""
        if isinstance(other, dict):
            # dictとの比較時は、カスタムフィールドとして扱う
            # ただし、versionキーがある場合は特別に処理
            if "version" in other and len(other) == 1:
                return self.version == other["version"] and not self.custom_fields
            return self.custom_fields == other
        if isinstance(other, GraphMetadata):
            return (
                self.version == other.version
                and self.created_at == other.created_at
                and self.cycles == other.cycles
                and self.statistics == other.statistics
                and self.custom_fields == other.custom_fields
            )
        return False
