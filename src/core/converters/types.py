"""
型変換モジュールの型定義

このモジュールでは、型変換機能に関連する型定義を提供します。
主に以下のカテゴリの型を定義します：

1. 型変換処理関連の型
2. YAML出力関連の型
3. モジュール解析関連の型
4. 依存関係抽出関連の型
"""

from pathlib import Path
from typing import Annotated, Any, NewType

from pydantic import AfterValidator, BaseModel, Field


def _validate_path_exists(v: str | Path | None) -> str | Path | None:
    """パスが存在することを検証するバリデーター"""
    if v is None:
        return v
    path = Path(v)
    if not path.exists():
        raise ValueError(f"パスが存在しません: {v}")
    return v


def _validate_positive_int(v: int) -> int:
    """正の整数であることを検証するバリデーター"""
    if v <= 0:
        raise ValueError(f"正の整数である必要がありますが、{v}が指定されました")
    return v


def _validate_depth_limit(v: int) -> int:
    """深さ制限が適切な範囲内であることを検証するバリデーター"""
    if v <= 0 or v > 1000:
        raise ValueError(
            f"深さ制限は1〜1000の範囲である必要がありますが、{v}が指定されました"
        )
    return v


# Level 1: 単純な型エイリアス（制約なし）
type ModulePath = str | Path
type TypeName = str
type YamlString = str
type CodeString = str
type OutputPath = str | Path | None

# Level 2: NewType + Annotated（制約付き、型レベル区別）
# NOTE: ModulePath は str | Path なので、NewTypeでは扱えない（Union型のため）
type ValidatedModulePath = Annotated[ModulePath, AfterValidator(_validate_path_exists)]

MaxDepth = NewType(
    "MaxDepth",
    Annotated[int, Field(gt=0, le=1000), AfterValidator(_validate_depth_limit)],
)

PositiveInt = NewType(
    "PositiveInt", Annotated[int, Field(gt=0), AfterValidator(_validate_positive_int)]
)


class TypeConversionConfig(BaseModel):
    """
    型変換処理の設定を管理するコンフィギュレーションクラス

    このクラスは、型変換処理の全体的な設定を管理します。
    """

    max_depth: MaxDepth = Field(default=10, description="再帰処理の最大深さ制限")  # type: ignore[assignment]
    preserve_quotes: bool = Field(
        default=True, description="YAML出力で引用符を保持するか"
    )
    as_root: bool = Field(default=True, description="ルートレベルで出力するか")

    class Config:
        """Pydantic設定"""

        frozen = True  # イミュータブルに設定


class YamlOutputConfig(BaseModel):
    """
    YAML出力の設定を管理するコンフィギュレーションクラス

    このクラスは、YAML出力のフォーマット設定を管理します。
    """

    indent_mapping: PositiveInt = Field(  # type: ignore[assignment]
        default=2, description="マッピングのインデント幅"
    )
    indent_sequence: PositiveInt = Field(  # type: ignore[assignment]
        default=4, description="シーケンスのインデント幅"
    )
    indent_offset: PositiveInt = Field(  # type: ignore[assignment]
        default=2, description="ベースインデントのオフセット"
    )
    width: PositiveInt | None = Field(
        default=None, description="出力幅の制限（Noneで無制限）"
    )

    class Config:
        """Pydantic設定"""

        frozen = True


class ModuleExtractionConfig(BaseModel):
    """
    モジュールからの型抽出設定を管理するコンフィギュレーションクラス

    このクラスは、Pythonモジュールから型定義を抽出する際の設定を管理します。
    """

    extract_functions: bool = Field(
        default=False, description="関数定義も抽出対象に含めるか"
    )
    extract_variables: bool = Field(
        default=True, description="変数定義も抽出対象に含めるか"
    )
    extract_classes: bool = Field(
        default=True, description="クラス定義も抽出対象に含めるか"
    )
    max_file_size: PositiveInt = Field(  # type: ignore[assignment]
        default=10 * 1024 * 1024, description="処理可能な最大ファイルサイズ（バイト）"
    )

    class Config:
        """Pydantic設定"""

        frozen = True


class DependencyGraphConfig(BaseModel):
    """
    依存関係グラフ構築の設定を管理するコンフィギュレーションクラス

    このクラスは、依存関係グラフの構築・処理に関する設定を管理します。
    """

    include_builtin_types: bool = Field(
        default=False, description="組み込み型も含めて処理するか"
    )
    max_nodes: PositiveInt | None = Field(
        default=None, description="最大ノード数制限（Noneで無制限）"
    )
    max_edges: PositiveInt | None = Field(
        default=None, description="最大エッジ数制限（Noneで無制限）"
    )
    detect_cycles: bool = Field(default=True, description="循環参照を検出・報告するか")

    class Config:
        """Pydantic設定"""

        frozen = True


class VisualizationConfig(BaseModel):
    """
    依存関係グラフの可視化設定を管理するコンフィギュレーションクラス

    このクラスは、依存関係グラフの視覚化に関する設定を管理します。
    """

    output_path: OutputPath = Field(
        default="deps.png", description="出力画像ファイルのパス"
    )
    width: PositiveInt = Field(default=8, description="画像の幅（インチ）")  # type: ignore[assignment]
    height: PositiveInt = Field(default=6, description="画像の高さ（インチ）")  # type: ignore[assignment]
    node_colors: dict[str, str] | None = Field(
        default_factory=lambda: {
            "function": "lightblue",
            "class": "lightgreen",
            "type": "lightyellow",
            "unknown": "lightgray",
        },
        description="ノードタイプ別の色設定",
    )
    edge_colors: dict[str, str] | None = Field(
        default_factory=lambda: {
            "argument": "blue",
            "returns": "green",
            "inherits_from": "red",
            "generic": "orange",
            "unknown": "black",
        },
        description="エッジタイプ別の色設定",
    )

    class Config:
        """Pydantic設定"""

        frozen = True


class ConversionResult(BaseModel):
    """
    型変換処理の結果を表すクラス

    このクラスは、型変換処理の結果とメタデータを保持します。
    """

    success: bool = Field(description="処理が成功したかどうか")
    input_type: TypeName | None = Field(default=None, description="入力された型名")
    output_path: OutputPath = Field(default=None, description="出力ファイルのパス")
    yaml_content: YamlString | None = Field(
        default=None, description="生成されたYAML内容"
    )
    error_message: str | None = Field(default=None, description="エラーメッセージ")
    processing_time_ms: float | None = Field(
        default=None, description="処理時間（ミリ秒）"
    )
    dependencies_count: PositiveInt | None = Field(
        default=None, description="検出された依存関係の数"
    )


class ExtractionResult(BaseModel):
    """
    モジュールからの型抽出結果を表すクラス

    このクラスは、モジュールから型を抽出する処理の結果を保持します。
    """

    success: bool = Field(description="処理が成功したかどうか")
    module_path: ValidatedModulePath = Field(description="処理対象のモジュールパス")
    extracted_types: dict[TypeName, dict[str, Any]] = Field(
        default_factory=dict, description="抽出された型定義"
    )
    error_message: str | None = Field(default=None, description="エラーメッセージ")
    processing_time_ms: float | None = Field(
        default=None, description="処理時間（ミリ秒）"
    )


class DependencyResult(BaseModel):
    """
    依存関係抽出処理の結果を表すクラス

    このクラスは、依存関係抽出処理の結果とグラフ情報を保持します。
    """

    success: bool = Field(description="処理が成功したかどうか")
    input_path: ValidatedModulePath = Field(description="処理対象のパス")
    graph_nodes: PositiveInt = Field(description="グラフのノード数")
    graph_edges: PositiveInt = Field(description="グラフのエッジ数")
    has_cycles: bool = Field(description="循環参照が存在するか")
    error_message: str | None = Field(default=None, description="エラーメッセージ")
    processing_time_ms: float | None = Field(
        default=None, description="処理時間（ミリ秒）"
    )
