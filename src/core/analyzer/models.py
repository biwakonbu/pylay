"""
型解析モジュールのドメインモデル

このモジュールでは、型解析機能のビジネスロジックを含むドメインモデルを定義します。
主に以下のカテゴリのモデルを定義します：

1. 型解析処理のビジネスモデル
2. ドキュメント解析のビジネスモデル
3. 統計計算のビジネスモデル
4. 品質評価のビジネスモデル
"""

import ast
import logging
import time
from pathlib import Path
from typing import Any, Literal, TypeGuard

from pydantic import BaseModel, ConfigDict, Field

from src.core.schemas.graph import GraphEdge, GraphNode
from src.core.schemas.pylay_config import PylayConfig
from src.core.schemas.types import (
    ClassName,
    Code,
    ConfidenceScore,
    EnableMypyFlag,
    FileOpenMode,
    FilePath,
    FileSuffix,
    FunctionName,
    InferLevel,
    LineNumber,
    MaxDepth,
    ModuleName,
    MypyFlag,
    ReturnCode,
    StdErr,
    StdOut,
    Timeout,
    TypeName,
    VariableName,
    VisualizeFlag,
    create_max_depth,
)

from .types import (
    AnalysisConfig,
    DocumentationStatistics,
    FileAnalysisResult,
    FormatStyle,
    ProjectAnalysisResult,
    QualityMetrics,
    TypeDefinition,
    TypeLevel,
    TypeLevelInfo,
    TypeUpgradeSuggestion,
)

logger = logging.getLogger(__name__)


def is_type_level(value: str) -> TypeGuard[TypeLevel]:
    """文字列がTypeLevelリテラル型であることを確認する型ガード関数"""
    return value in ("level1", "level2", "level3", "other")


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

    variable_name: VariableName
    inferred_type: TypeName
    confidence: ConfidenceScore
    source_file: FilePath | None = None
    line_number: LineNumber | None = None

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

    # GraphNode/GraphEdgeがPydanticモデル外のため、arbitrary_types_allowed=Trueが必要
    # これにより型安全性が低下するが、外部ライブラリ依存のグラフ構造を扱うため許容
    model_config = ConfigDict(frozen=False, extra="forbid", arbitrary_types_allowed=True)

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
    module_name: ModuleName
    current_class: ClassName | None = None
    current_function: FunctionName | None = None

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
    max_depth: MaxDepth = Field(default=MaxDepth(10))
    enable_mypy: EnableMypyFlag = True
    mypy_flags: list[MypyFlag] = Field(default_factory=lambda: ["--inferstats", "--timing-stats"])
    timeout: Timeout = Field(default=60, ge=1, le=600)

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

        # infer_levelのバリデーション
        infer_level = config.infer_level
        if not is_valid_infer_level(infer_level):
            logger.warning(
                f"無効なinfer_level '{infer_level}' が指定されました。"
                f"デフォルト値 'normal' にフォールバックします。"
                f"有効な値: 'loose', 'normal', 'strict'"
            )
            infer_level = "normal"

        # 型ガードによって infer_level は Literal["loose", "normal", "strict"] 型
        return cls(
            infer_level=infer_level,
            max_depth=create_max_depth(max_depth),
            enable_mypy=infer_level != "loose",
        )


def is_valid_infer_level(
    value: str,
) -> TypeGuard[Literal["loose", "normal", "strict"]]:
    """infer_levelが有効な値かチェックする型ガード"""
    return value in ("loose", "normal", "strict")


class MypyResult(BaseModel):
    """
    mypy実行結果

    Attributes:
        stdout: 標準出力
        stderr: 標準エラー
        return_code: 終了コード
        inferred_types: 推論された型情報
        statistics: mypy統計情報（オプション）
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    stdout: StdOut
    stderr: StdErr
    return_code: ReturnCode
    inferred_types: dict[str, InferResult] = Field(default_factory=dict)
    statistics: dict[str, dict[str, int]] | None = None

    def is_success(self) -> bool:
        """実行成功か判定"""
        return self.return_code == 0

    def has_inferred_types(self) -> bool:
        """推論結果があるか判定"""
        return len(self.inferred_types) > 0


class TempFileConfig(BaseModel):
    """一時ファイル設定のPydanticモデル

    Attributes:
        code: 一時ファイルに書き込むコード内容
        suffix: ファイルの拡張子（デフォルト: ".py"）
        mode: ファイルオープンモード（デフォルト: "w"）
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: Code = Field(..., description="一時ファイルに書き込むコード内容", min_length=1)
    suffix: FileSuffix = Field(default=".py", description="ファイルの拡張子")
    mode: FileOpenMode = Field(default="w", description="ファイルオープンモード")


class AnalyzerConfig(BaseModel):
    """Analyzer設定の型（PylayConfig拡張）

    Analyzer固有の設定を管理するPylayConfigの拡張クラスです。
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    infer_level: InferLevel
    max_depth: MaxDepth
    visualize: VisualizeFlag


class TypeAnalyzerService(BaseModel):
    """
    型解析のサービスクラス

    このクラスは、型解析処理のビジネスロジックを実装します。
    """

    def analyze_file(self, file_path: str | Path, config: AnalysisConfig | None = None) -> FileAnalysisResult:
        """
        単一ファイルを解析します。

        Args:
            file_path: 解析対象のファイルパス
            config: 解析設定（Noneの場合、デフォルト設定を使用）

        Returns:
            ファイル解析結果
        """
        start_time = time.time()
        config = config or AnalysisConfig()
        file_path_obj = Path(file_path)

        try:
            if not file_path_obj.exists():
                raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

            # ファイルサイズチェック
            file_size = file_path_obj.stat().st_size
            if file_size > config.max_file_size:
                raise ValueError(
                    f"ファイルサイズが制限を超えています: size={file_size} bytes > max={config.max_file_size} bytes"
                )

            # ファイル内容の読み込みと解析
            with open(file_path_obj, encoding="utf-8") as f:
                source_code = f.read()

            tree = ast.parse(source_code)

            # 型定義の抽出
            type_definitions = self._extract_type_definitions_from_ast(tree, file_path_obj)

            # 解析結果の構築
            analysis_time = (time.time() - start_time) * 1000

            return FileAnalysisResult(
                file_path=str(file_path),
                type_definitions=type_definitions,
                total_types=len(type_definitions),
                documented_types=sum(1 for td in type_definitions if td.has_docstring),
                analysis_time_ms=analysis_time,
                has_errors=False,
            )

        except Exception as e:
            analysis_time = (time.time() - start_time) * 1000
            return FileAnalysisResult(
                file_path=str(file_path),
                type_definitions=[],
                total_types=0,
                documented_types=0,
                analysis_time_ms=analysis_time,
                has_errors=True,
                error_messages=[str(e)],
            )

    def _extract_type_definitions_from_ast(self, tree: ast.AST, file_path: Path) -> list[TypeDefinition]:
        """ASTから型定義を抽出する内部メソッド"""
        type_definitions = []

        for node in ast.walk(tree):
            # isinstance with tuple is safer for compatibility
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                # クラスまたは関数の定義を処理
                type_def = self._create_type_definition_from_node(node, file_path)
                if type_def:
                    type_definitions.append(type_def)

        return type_definitions

    def _create_type_definition_from_node(self, node: ast.AST, file_path: Path) -> TypeDefinition | None:
        """ASTノードから型定義を作成する内部メソッド"""
        try:
            # 型情報の取得
            if isinstance(node, ast.ClassDef):
                type_name = node.name
                category = "class"
                definition = self._get_class_definition(node)
            elif isinstance(node, ast.FunctionDef):
                type_name = node.name
                category = "function"
                definition = self._get_function_definition(node)
            else:
                return None

            # docstringの取得
            docstring = ast.get_docstring(node)
            has_docstring = docstring is not None
            docstring_lines = len(docstring.split("\n")) if docstring else 0

            # 型レベルの判定（簡易版）
            type_level = self._determine_type_level(node, category)

            # 型レベルを適切に変換
            if is_type_level(type_level):
                level_value = type_level
            else:
                level_value = "other"  # デフォルト値

            return TypeDefinition(
                name=type_name,
                level=level_value,
                file_path=str(file_path),
                line_number=node.lineno,
                definition=definition,
                category=category,
                docstring=docstring,
                has_docstring=has_docstring,
                docstring_lines=docstring_lines,
                target_level=None,
                keep_as_is=False,
            )

        except Exception:
            return None

    def _get_class_definition(self, node: ast.ClassDef) -> str:
        """クラス定義の文字列を取得する内部メソッド"""
        bases = [base.id if isinstance(base, ast.Name) else ast.unparse(base) for base in node.bases]
        base_str = f"({', '.join(bases)})" if bases else ""
        return f"class {node.name}{base_str}:"

    def _get_function_definition(self, node: ast.FunctionDef) -> str:
        """関数定義の文字列を取得する内部メソッド"""
        args = [arg.arg for arg in node.args.args]
        args_str = ", ".join(args)
        return f"def {node.name}({args_str}):"

    def _determine_type_level(self, node: ast.AST, category: str) -> TypeLevel:
        """型レベルを判定する内部メソッド"""
        # 簡易的な判定ロジック
        if category == "class":
            return "level3"  # クラスはLevel 3
        else:
            return "level2"  # 関数はLevel 2


class DocstringAnalyzerService(BaseModel):
    """
    docstring解析のサービスクラス

    このクラスは、docstring解析処理のビジネスロジックを実装します。
    """

    def analyze_docstring(self, docstring: str, type_name: TypeName) -> dict[str, Any]:
        """
        docstringを解析します。

        Args:
            docstring: 解析対象のdocstring
            type_name: 型名

        Returns:
            解析結果の辞書
        """
        if not docstring:
            return {
                "has_summary": False,
                "has_description": False,
                "has_attributes": False,
                "has_args": False,
                "has_returns": False,
                "has_examples": False,
                "format_style": "unknown",
                "line_count": 0,
                "detail_score": 0.0,
            }

        lines = docstring.strip().split("\n")
        line_count = len(lines)

        # 基本的な解析（簡易版）
        has_summary = len(lines) > 0 and lines[0].strip() != ""
        has_description = line_count > 1
        has_attributes = "Attributes:" in docstring or "属性:" in docstring
        has_args = "Args:" in docstring or "引数:" in docstring
        has_returns = "Returns:" in docstring or "戻り値:" in docstring
        has_examples = "Examples:" in docstring or "例:" in docstring

        # フォーマットスタイルの判定（簡易版）
        format_style = "unknown"
        if "Args:" in docstring and "Returns:" in docstring:
            format_style = "google"
        elif "Parameters" in docstring and "Return" in docstring:
            format_style = "numpy"

        # 詳細度スコアの計算
        detail_score = (
            0.3 * (1 if has_summary else 0)
            + 0.2 * (1 if has_description else 0)
            + 0.2 * (1 if has_attributes else 0)
            + 0.15 * (1 if has_args else 0)
            + 0.15 * (1 if has_returns else 0)
            + 0.1 * (1 if has_examples else 0)
        )

        return {
            "has_summary": has_summary,
            "has_description": has_description,
            "has_attributes": has_attributes,
            "has_args": has_args,
            "has_returns": has_returns,
            "has_examples": has_examples,
            "format_style": format_style,
            "line_count": line_count,
            "detail_score": detail_score,
        }

    def calculate_documentation_quality(self, type_def: TypeDefinition) -> float:
        """
        ドキュメント品質スコアを計算します。

        Args:
            type_def: 型定義

        Returns:
            品質スコア（0.0-1.0）
        """
        if not type_def.has_docstring:
            return 0.0

        base_score = 0.5  # 基本スコア（docstringがある場合）

        # docstringの長さによるボーナス
        if type_def.docstring_lines >= 5:
            base_score += 0.3
        elif type_def.docstring_lines >= 2:
            base_score += 0.15

        # 型レベルによる調整
        if type_def.level == "level3":
            base_score += 0.2  # Level 3はより詳細なドキュメントが期待される

        return min(base_score, 1.0)

    def generate_documentation_statistics(self, type_definitions: list[TypeDefinition]) -> DocumentationStatistics:
        """
        ドキュメント統計情報を生成します。

        Args:
            type_definitions: 型定義のリスト

        Returns:
            ドキュメント統計情報
        """
        if not type_definitions:
            return DocumentationStatistics(
                total_types=0,
                documented_types=0,
                undocumented_types=0,
                implementation_rate=0.0,
                minimal_docstrings=0,
                detailed_docstrings=0,
                detail_rate=0.0,
                avg_docstring_lines=0.0,
                quality_score=0.0,
                by_level={},
                by_level_avg_lines={},
                by_format={},
            )

        total_types = len(type_definitions)
        documented_types = sum(1 for td in type_definitions if td.has_docstring)
        undocumented_types = total_types - documented_types
        implementation_rate = documented_types / total_types

        # docstringの詳細度分類
        minimal_docstrings = sum(1 for td in type_definitions if td.has_docstring and td.docstring_lines <= 2)
        detailed_docstrings = sum(1 for td in type_definitions if td.has_docstring and td.docstring_lines > 2)

        # レベル別統計の計算
        by_level: dict[TypeLevel, dict[str, int]] = {}
        by_format: dict[FormatStyle, int] = {}
        total_docstring_lines = 0

        for td in type_definitions:
            if td.has_docstring:
                total_docstring_lines += td.docstring_lines

                # レベル別統計
                if td.level not in by_level:
                    by_level[td.level] = {"total": 0, "documented": 0, "lines": 0}
                by_level[td.level]["total"] += 1
                by_level[td.level]["documented"] += 1
                by_level[td.level]["lines"] += td.docstring_lines

                # フォーマット別統計（簡易版）
                format_key: FormatStyle = "google"  # デフォルト値
                if format_key not in by_format:
                    by_format[format_key] = 0
                by_format[format_key] += 1

        # レベル別平均行数の計算（NonNegativeIntとfloatを分離）
        by_level_avg_lines: dict[TypeLevel, float] = {}
        for level in by_level:  # level is TypeLevel
            stats = by_level[level]
            avg_lines = stats["lines"] / stats["documented"] if stats["documented"] > 0 else 0.0
            by_level_avg_lines[level] = avg_lines
            # by_levelからはavg_linesを削除し、カウント値のみ保持
            del stats["lines"]  # 中間値を削除

        avg_docstring_lines = total_docstring_lines / documented_types if documented_types > 0 else 0.0
        detail_rate = detailed_docstrings / documented_types if documented_types > 0 else 0.0
        quality_score = implementation_rate * detail_rate

        return DocumentationStatistics(
            total_types=total_types,
            documented_types=documented_types,
            undocumented_types=undocumented_types,
            implementation_rate=implementation_rate,
            minimal_docstrings=minimal_docstrings,
            detailed_docstrings=detailed_docstrings,
            detail_rate=detail_rate,
            avg_docstring_lines=avg_docstring_lines,
            quality_score=quality_score,
            by_level=by_level,
            by_level_avg_lines=by_level_avg_lines,
            by_format=by_format,
        )


class TypeClassifierService(BaseModel):
    """
    型分類のサービスクラス

    このクラスは、型分類処理のビジネスロジックを実装します。
    """

    def classify_type(self, type_def: TypeDefinition) -> str:
        """
        型を分類します。

        Args:
            type_def: 型定義

        Returns:
            分類結果（type_alias/annotated/basemodel/class/dataclass等）
        """
        # 現在のcategoryを返す（簡易版）
        # 実際の実装ではより詳細な分類ロジックが必要
        return type_def.category

    def determine_type_level(self, type_def: TypeDefinition) -> str:
        """
        型レベルを判定します。

        Args:
            type_def: 型定義

        Returns:
            型レベル（level1/level2/level3/other）
        """
        # 現在のlevelを返す（簡易版）
        # 実際の実装ではより詳細な判定ロジックが必要
        return type_def.level

    def suggest_type_improvements(self, type_def: TypeDefinition) -> list[TypeUpgradeSuggestion]:
        """
        型の改善提案を生成します。

        Args:
            type_def: 型定義

        Returns:
            改善提案のリスト
        """
        suggestions = []

        # ドキュメントがない場合の提案
        if not type_def.has_docstring:
            suggestions.append(
                TypeUpgradeSuggestion(
                    type_name=type_def.name,
                    current_level=type_def.level,
                    suggested_level=type_def.level,
                    reason="ドキュメントがありません。適切なdocstringを追加してください。",
                    priority="high",
                    effort_estimate="small",
                )
            )

        # 型レベルによる提案
        if type_def.level == "level1" and type_def.category == "class":
            suggestions.append(
                TypeUpgradeSuggestion(
                    type_name=type_def.name,
                    current_level=type_def.level,
                    suggested_level="level3",
                    reason="クラス定義にはより詳細な型情報とバリデーションを追加することを検討してください。",
                    priority="medium",
                    effort_estimate="medium",
                )
            )

        return suggestions


class StatisticsCalculatorService(BaseModel):
    """
    統計計算のサービスクラス

    このクラスは、統計計算処理のビジネスロジックを実装します。
    """

    def calculate_level_statistics(self, type_definitions: list[TypeDefinition]) -> dict[TypeLevel, TypeLevelInfo]:
        """
        レベル別の統計情報を計算します。

        Args:
            type_definitions: 型定義のリスト

        Returns:
            レベル別の統計情報
        """
        level_stats: dict[str, dict[str, Any]] = {}

        for td in type_definitions:
            level = td.level
            if level not in level_stats:
                level_stats[level] = {
                    "count": 0,
                    "documented_count": 0,
                    "avg_docstring_lines": 0.0,
                    "upgrade_candidates": 0,
                    "keep_as_is_count": 0,
                }

            level_stats[level]["count"] += 1
            if td.has_docstring:
                level_stats[level]["documented_count"] += 1
                # 平均行数の計算（簡易版）
                level_stats[level]["avg_docstring_lines"] = (
                    level_stats[level]["avg_docstring_lines"] * (level_stats[level]["documented_count"] - 1)
                    + td.docstring_lines
                ) / level_stats[level]["documented_count"]

            # アップグレード候補の判定（簡易版）
            if td.level == "level1" and td.category in ["class", "function"]:
                level_stats[level]["upgrade_candidates"] += 1

            if td.keep_as_is:
                level_stats[level]["keep_as_is_count"] += 1

        # TypeLevelInfoオブジェクトの作成
        result: dict[TypeLevel, TypeLevelInfo] = {}
        for level_str, stats in level_stats.items():
            # 型レベル文字列をTypeLevelリテラルに変換
            # 有効なレベル値であることを確認
            if not is_type_level(level_str):
                continue  # 無効なレベルはスキップ

            # 型ガードで検証済みなので、level_strはTypeLevel型
            result[level_str] = TypeLevelInfo(
                level=level_str,
                count=stats["count"],
                documented_count=stats["documented_count"],
                avg_docstring_lines=stats["avg_docstring_lines"],
                upgrade_candidates=stats["upgrade_candidates"],
                keep_as_is_count=stats["keep_as_is_count"],
            )

        return result

    def calculate_quality_metrics(self, analysis_result: ProjectAnalysisResult) -> QualityMetrics:
        """
        品質指標を計算します。

        Args:
            analysis_result: プロジェクト解析結果

        Returns:
            品質指標
        """
        stats = analysis_result.documentation_stats

        # 総合スコアの計算（簡易版）
        overall_score = stats.quality_score

        # 型カバー率
        type_coverage = stats.implementation_rate

        # ドキュメントカバー率（既に計算済み）
        documentation_coverage = stats.implementation_rate

        # 型レベルバランススコア（簡易版）
        level_count = len(analysis_result.level_stats)
        if level_count > 0:
            # 各レベルの分布を考慮したバランススコア
            type_level_balance = 0.7  # 簡易的な固定値
        else:
            type_level_balance = 0.0

        # 保守性スコア（簡易版）
        maintainability_score = overall_score * 0.8 + type_coverage * 0.2

        # 複雑度スコア（簡易版）
        avg_lines = stats.avg_docstring_lines
        if avg_lines > 10:
            complexity_score = 0.8  # 詳細なドキュメントは複雑度が高い
        elif avg_lines > 5:
            complexity_score = 0.6
        else:
            complexity_score = 0.4

        return QualityMetrics(
            overall_score=overall_score,
            type_coverage=type_coverage,
            documentation_coverage=documentation_coverage,
            type_level_balance=type_level_balance,
            maintainability_score=maintainability_score,
            complexity_score=complexity_score,
        )

    def generate_summary_report(self, analysis_result: ProjectAnalysisResult) -> str:
        """
        要約レポートを生成します。

        Args:
            analysis_result: プロジェクト解析結果

        Returns:
            要約レポート文字列
        """
        stats = analysis_result.documentation_stats
        quality = self.calculate_quality_metrics(analysis_result)

        lines = [
            "# 型解析レポート",
            "",
            "## 概要",
            f"- 解析ファイル数: {analysis_result.analyzed_files}",
            f"- 失敗ファイル数: {analysis_result.failed_files}",
            f"- 総型定義数: {stats.total_types}",
            f"- ドキュメント付き型定義数: {stats.documented_types}",
            f"- ドキュメントカバー率: {stats.implementation_rate:.1%}",
            "",
            "## 品質指標",
            f"- 総合スコア: {quality.overall_score:.1%}",
            f"- 型カバー率: {quality.type_coverage:.1%}",
            f"- ドキュメントカバー率: {quality.documentation_coverage:.1%}",
            f"- 保守性スコア: {quality.maintainability_score:.1%}",
            "",
            "## 型レベル分布",
        ]

        for level, level_info in analysis_result.level_stats.items():
            doc_rate = (level_info.documented_count / level_info.count) if level_info.count else 0.0
            lines.append(f"- {level}: {level_info.count}個（ドキュメント率: {doc_rate:.1%}）")

        return "\n".join(lines)


class TypeReporterService(BaseModel):
    """
    レポート生成のサービスクラス

    このクラスは、レポート生成処理のビジネスロジックを実装します。
    """

    def generate_markdown_report(self, analysis_result: ProjectAnalysisResult) -> str:
        """
        マークダウンレポートを生成します。

        Args:
            analysis_result: プロジェクト解析結果

        Returns:
            マークダウン形式のレポート文字列
        """
        stats_calculator = StatisticsCalculatorService()
        return stats_calculator.generate_summary_report(analysis_result)

    def generate_json_report(self, analysis_result: ProjectAnalysisResult) -> str:
        """
        JSONレポートを生成します。

        Args:
            analysis_result: プロジェクト解析結果

        Returns:
            JSON形式のレポート文字列
        """
        import json

        # Pydanticモデルを辞書に変換してJSON化
        data = analysis_result.model_dump()
        return json.dumps(data, indent=2, ensure_ascii=False)

    def export_report(
        self,
        report_content: str,
        output_path: str | Path,
        format_type: str = "markdown",
    ) -> None:
        """
        レポートをファイルに出力します。

        Args:
            report_content: レポート内容
            output_path: 出力パス
            format_type: フォーマットタイプ（markdown/json）
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report_content, encoding="utf-8")


class ProjectAnalyzerService(BaseModel):
    """
    プロジェクト解析のサービスクラス

    このクラスは、プロジェクト全体の解析処理を統制します。
    """

    type_analyzer: TypeAnalyzerService = Field(default_factory=TypeAnalyzerService)
    docstring_analyzer: DocstringAnalyzerService = Field(default_factory=DocstringAnalyzerService)
    type_classifier: TypeClassifierService = Field(default_factory=TypeClassifierService)
    statistics_calculator: StatisticsCalculatorService = Field(default_factory=StatisticsCalculatorService)
    reporter: TypeReporterService = Field(default_factory=TypeReporterService)

    def analyze_project(self, project_path: str | Path, config: AnalysisConfig | None = None) -> ProjectAnalysisResult:
        """
        プロジェクト全体を解析します。

        Args:
            project_path: プロジェクトのルートパス
            config: 解析設定（Noneの場合、デフォルト設定を使用）

        Returns:
            プロジェクト解析結果
        """
        start_time = time.time()
        config = config or AnalysisConfig()
        project_path_obj = Path(project_path)

        if not project_path_obj.exists():
            raise FileNotFoundError(f"プロジェクトパスが見つかりません: {project_path}")

        # 解析対象ファイルの収集
        python_files = self._collect_python_files(project_path_obj, config)

        # 各ファイルの解析
        all_type_definitions = []
        analyzed_files = 0
        failed_files = 0
        file_results = []

        for file_path in python_files:
            try:
                result = self.type_analyzer.analyze_file(file_path, config)
                file_results.append(result)
                all_type_definitions.extend(result.type_definitions)
                analyzed_files += 1
            except Exception as e:
                logger.warning(f"ファイル解析に失敗: {file_path}, エラー: {e}")
                failed_files += 1

        # 統計情報の計算
        documentation_stats = self.docstring_analyzer.generate_documentation_statistics(all_type_definitions)
        level_stats = self.statistics_calculator.calculate_level_statistics(all_type_definitions)

        total_time = (time.time() - start_time) * 1000

        return ProjectAnalysisResult(
            project_path=str(project_path),
            total_files=len(python_files),
            analyzed_files=analyzed_files,
            failed_files=failed_files,
            all_type_definitions=all_type_definitions,
            documentation_stats=documentation_stats,
            level_stats=level_stats,
            total_analysis_time_ms=total_time,
            analysis_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

    def _collect_python_files(self, project_path: Path, config: AnalysisConfig) -> list[Path]:
        """プロジェクト内のPythonファイルを収集する内部メソッド"""
        python_files = []

        for pattern in config.include_patterns:
            for file_path in project_path.rglob(pattern):
                # 除外パターンチェック（globパターン）
                if any(file_path.match(exclude) for exclude in config.exclude_patterns):
                    continue

                # ファイルサイズチェック
                if file_path.stat().st_size > config.max_file_size:
                    continue

                python_files.append(file_path)

        # 重複除去と制限
        unique_files = list(set(python_files))
        if config.max_files:
            unique_files = unique_files[: config.max_files]

        return unique_files
