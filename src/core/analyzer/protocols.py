"""
型解析モジュールのプロトコル定義

このモジュールでは、型解析機能で使用するProtocolインターフェースを定義します。
主に以下のカテゴリのプロトコルを定義します：

1. 型解析関連のプロトコル
2. ドキュメント解析関連のプロトコル
3. 統計情報関連のプロトコル
4. 品質評価関連のプロトコル
"""

from abc import abstractmethod
from pathlib import Path
from typing import Any, Protocol

from .types import (
    AnalysisConfig,
    DocumentationStatistics,
    FileAnalysisResult,
    ProjectAnalysisResult,
    QualityMetrics,
    TypeDefinition,
    TypeLevelInfo,
    TypeName,
    TypeUpgradeSuggestion,
)


class TypeAnalyzerProtocol(Protocol):
    """
    型解析機能の基本プロトコル

    このプロトコルは、型解析機能の基本的なインターフェースを定義します。
    """

    @abstractmethod
    def analyze_file(self, file_path: str | Path, config: AnalysisConfig | None = None) -> FileAnalysisResult:
        """
        単一ファイルを解析します。

        Args:
            file_path: 解析対象のファイルパス
            config: 解析設定（Noneの場合、デフォルト設定を使用）

        Returns:
            ファイル解析結果
        """
        ...

    @abstractmethod
    def analyze_project(self, project_path: str | Path, config: AnalysisConfig | None = None) -> ProjectAnalysisResult:
        """
        プロジェクト全体を解析します。

        Args:
            project_path: プロジェクトのルートパス
            config: 解析設定（Noneの場合、デフォルト設定を使用）

        Returns:
            プロジェクト解析結果
        """
        ...

    @abstractmethod
    def extract_type_definitions(self, code: str) -> list[TypeDefinition]:
        """
        コードから型定義を抽出します。

        Args:
            code: 解析対象のPythonコード

        Returns:
            抽出された型定義のリスト
        """
        ...


class DocstringAnalyzerProtocol(Protocol):
    """
    docstring解析機能のプロトコル

    このプロトコルは、docstring解析機能のインターフェースを定義します。
    """

    @abstractmethod
    def analyze_docstring(self, docstring: str, type_name: TypeName) -> dict[str, Any]:
        """
        docstringを解析します。

        Args:
            docstring: 解析対象のdocstring
            type_name: 型名

        Returns:
            解析結果の辞書
        """
        ...

    @abstractmethod
    def calculate_documentation_quality(self, type_def: TypeDefinition) -> float:
        """
        ドキュメント品質スコアを計算します。

        Args:
            type_def: 型定義

        Returns:
            品質スコア（0.0-1.0）
        """
        ...

    @abstractmethod
    def generate_documentation_statistics(self, type_definitions: list[TypeDefinition]) -> DocumentationStatistics:
        """
        ドキュメント統計情報を生成します。

        Args:
            type_definitions: 型定義のリスト

        Returns:
            ドキュメント統計情報
        """
        ...


class TypeClassifierProtocol(Protocol):
    """
    型分類機能のプロトコル

    このプロトコルは、型分類機能のインターフェースを定義します。
    """

    @abstractmethod
    def classify_type(self, type_def: TypeDefinition) -> str:
        """
        型を分類します。

        Args:
            type_def: 型定義

        Returns:
            分類結果（type_alias/annotated/basemodel/class/dataclass等）
        """
        ...

    @abstractmethod
    def determine_type_level(self, type_def: TypeDefinition) -> str:
        """
        型レベルを判定します。

        Args:
            type_def: 型定義

        Returns:
            型レベル（level1/level2/level3/other）
        """
        ...

    @abstractmethod
    def suggest_type_improvements(self, type_def: TypeDefinition) -> list[TypeUpgradeSuggestion]:
        """
        型の改善提案を生成します。

        Args:
            type_def: 型定義

        Returns:
            改善提案のリスト
        """
        ...


class StatisticsCalculatorProtocol(Protocol):
    """
    統計計算機能のプロトコル

    このプロトコルは、統計計算機能のインターフェースを定義します。
    """

    @abstractmethod
    def calculate_level_statistics(self, type_definitions: list[TypeDefinition]) -> dict[str, TypeLevelInfo]:
        """
        レベル別の統計情報を計算します。

        Args:
            type_definitions: 型定義のリスト

        Returns:
            レベル別の統計情報
        """
        ...

    @abstractmethod
    def calculate_quality_metrics(self, analysis_result: ProjectAnalysisResult) -> QualityMetrics:
        """
        品質指標を計算します。

        Args:
            analysis_result: プロジェクト解析結果

        Returns:
            品質指標
        """
        ...

    @abstractmethod
    def generate_summary_report(self, analysis_result: ProjectAnalysisResult) -> str:
        """
        要約レポートを生成します。

        Args:
            analysis_result: プロジェクト解析結果

        Returns:
            要約レポート文字列
        """
        ...


class TypeReporterProtocol(Protocol):
    """
    レポート生成機能のプロトコル

    このプロトコルは、レポート生成機能のインターフェースを定義します。
    """

    @abstractmethod
    def generate_markdown_report(self, analysis_result: ProjectAnalysisResult) -> str:
        """
        マークダウンレポートを生成します。

        Args:
            analysis_result: プロジェクト解析結果

        Returns:
            マークダウン形式のレポート文字列
        """
        ...

    @abstractmethod
    def generate_json_report(self, analysis_result: ProjectAnalysisResult) -> str:
        """
        JSONレポートを生成します。

        Args:
            analysis_result: プロジェクト解析結果

        Returns:
            JSON形式のレポート文字列
        """
        ...

    @abstractmethod
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
        ...
