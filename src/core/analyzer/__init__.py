"""
型解析モジュールのパッケージ初期化。

このモジュールは、型解析機能を提供します。
主な機能：
- Pythonコードからの型定義抽出
- 型レベルの解析と分類
- ドキュメント品質の評価
- 型定義の改善提案
"""

# 型定義のエクスポート
# 既存の実装クラスのエクスポート（一部のみ）
from .base import FullAnalyzer
from .docstring_analyzer import DocstringAnalyzer

# モデルのエクスポート
from .models import (
    DocstringAnalyzerService,
    ProjectAnalyzerService,
    StatisticsCalculatorService,
    TypeAnalyzerService,
    TypeClassifierService,
    TypeReporterService,
)

# プロトコルのエクスポート
from .protocols import (
    DocstringAnalyzerProtocol,
    StatisticsCalculatorProtocol,
    TypeAnalyzerProtocol,
    TypeClassifierProtocol,
    TypeReporterProtocol,
)
from .type_classifier import TypeClassifier
from .type_level_analyzer import TypeLevelAnalyzer
from .type_reporter import TypeReporter
from .type_statistics import TypeStatisticsCalculator
from .types import (
    AnalysisConfig,
    CategoryName,
    DocstringDetail,
    DocumentationStatistics,
    FileAnalysisResult,
    # 型エイリアス
    FilePath,
    FormatStyle,
    Percentage,
    ProjectAnalysisResult,
    QualityMetrics,
    TargetLevel,
    TypeDefinition,
    TypeLevel,
    TypeLevelInfo,
    TypeName,
    TypeUpgradeSuggestion,
    ValidatedFilePath,
)

__all__ = [
    # 型定義
    "TypeDefinition",
    "DocstringDetail",
    "DocumentationStatistics",
    "TypeLevelInfo",
    "FileAnalysisResult",
    "ProjectAnalysisResult",
    "AnalysisConfig",
    "QualityMetrics",
    "TypeUpgradeSuggestion",
    # 型エイリアス
    "FilePath",
    "TypeName",
    "CategoryName",
    "FormatStyle",
    "TypeLevel",
    "TargetLevel",
    "ValidatedFilePath",
    "PositiveInt",
    "Percentage",
    # プロトコル
    "TypeAnalyzerProtocol",
    "DocstringAnalyzerProtocol",
    "TypeClassifierProtocol",
    "StatisticsCalculatorProtocol",
    "TypeReporterProtocol",
    # モデル
    "TypeAnalyzerService",
    "DocstringAnalyzerService",
    "TypeClassifierService",
    "StatisticsCalculatorService",
    "TypeReporterService",
    "ProjectAnalyzerService",
    # 実装クラス
    "FullAnalyzer",
    "TypeLevelAnalyzer",
    "DocstringAnalyzer",
    "TypeClassifier",
    "TypeReporter",
    "TypeStatisticsCalculator",
]
