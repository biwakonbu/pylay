"""
型定義レベル分析のメインアナライザ

すべての分析機能を統合し、型定義レベルとドキュメント品質の分析を実行します。
"""

from pathlib import Path

from src.core.analyzer.docstring_analyzer import DocstringAnalyzer
from src.core.analyzer.type_classifier import TypeClassifier
from src.core.analyzer.type_level_models import (
    DocstringRecommendation,
    TypeAnalysisReport,
    TypeDefinition,
    TypeStatistics,
    UpgradeRecommendation,
)
from src.core.analyzer.type_reporter import TypeReporter
from src.core.analyzer.type_statistics import TypeStatisticsCalculator
from src.core.analyzer.type_upgrade_analyzer import TypeUpgradeAnalyzer


class TypeLevelAnalyzer:
    """型定義レベル分析のメインアナライザ"""

    def __init__(self, target_ratios: dict[str, float] | None = None):
        """初期化

        Args:
            target_ratios: 目標比率（デフォルト: 標準的な比率）
        """
        self.classifier = TypeClassifier()
        self.statistics_calculator = TypeStatisticsCalculator()
        self.docstring_analyzer = DocstringAnalyzer()
        self.upgrade_analyzer = TypeUpgradeAnalyzer()
        self.reporter = TypeReporter(target_ratios)

        self.target_ratios = target_ratios or {
            "level1": 0.55,
            "level2": 0.30,
            "level3": 0.175,
        }

    def analyze_directory(
        self, directory: Path, include_upgrade_recommendations: bool = True
    ) -> TypeAnalysisReport:
        """ディレクトリ内の型定義を分析

        Args:
            directory: 解析対象のディレクトリ
            include_upgrade_recommendations: 型レベルアップ推奨を含めるか

        Returns:
            TypeAnalysisReport
        """
        # すべての.pyファイルを収集
        py_files = list(directory.rglob("*.py"))

        # 型定義を収集
        all_type_definitions: list[TypeDefinition] = []
        for py_file in py_files:
            type_defs = self.classifier.classify_file(py_file)
            all_type_definitions.extend(type_defs)

        # 統計情報を計算
        statistics = self.statistics_calculator.calculate(all_type_definitions)

        # ドキュメント推奨を生成
        docstring_recommendations = self._generate_docstring_recommendations(
            all_type_definitions
        )

        # 型レベルアップ推奨を生成
        upgrade_recommendations: list[UpgradeRecommendation] = []
        if include_upgrade_recommendations:
            upgrade_recommendations = self._generate_upgrade_recommendations(
                all_type_definitions
            )

        # 一般的な推奨事項を生成
        recommendations = self._generate_general_recommendations(statistics)

        # 目標との乖離を計算
        deviation_from_target = self._calculate_deviation(statistics)

        return TypeAnalysisReport(
            statistics=statistics,
            type_definitions=all_type_definitions,
            recommendations=recommendations,
            upgrade_recommendations=upgrade_recommendations,
            docstring_recommendations=docstring_recommendations,
            target_ratios=self.target_ratios,
            deviation_from_target=deviation_from_target,
        )

    def analyze_file(self, file_path: Path) -> TypeAnalysisReport:
        """単一ファイルの型定義を分析

        Args:
            file_path: 解析対象のファイルパス

        Returns:
            TypeAnalysisReport
        """
        # 型定義を収集
        type_definitions = self.classifier.classify_file(file_path)

        # 統計情報を計算
        statistics = self.statistics_calculator.calculate(type_definitions)

        # ドキュメント推奨を生成
        docstring_recommendations = self._generate_docstring_recommendations(
            type_definitions
        )

        # 型レベルアップ推奨を生成
        upgrade_recommendations = self._generate_upgrade_recommendations(
            type_definitions
        )

        # 一般的な推奨事項を生成
        recommendations = self._generate_general_recommendations(statistics)

        # 目標との乖離を計算
        deviation_from_target = self._calculate_deviation(statistics)

        return TypeAnalysisReport(
            statistics=statistics,
            type_definitions=type_definitions,
            recommendations=recommendations,
            upgrade_recommendations=upgrade_recommendations,
            docstring_recommendations=docstring_recommendations,
            target_ratios=self.target_ratios,
            deviation_from_target=deviation_from_target,
        )

    def _generate_docstring_recommendations(
        self, type_definitions: list[TypeDefinition]
    ) -> list[DocstringRecommendation]:
        """docstring改善推奨を生成

        Args:
            type_definitions: 型定義リスト

        Returns:
            DocstringRecommendationのリスト
        """
        recommendations: list[DocstringRecommendation] = []

        for type_def in type_definitions:
            # docstringを解析
            detail = self.docstring_analyzer.analyze_docstring(type_def.docstring)

            # 推奨事項を生成
            rec = self.docstring_analyzer.recommend_docstring_improvements(
                type_def, detail
            )

            # "none"以外の推奨事項を追加
            if rec.recommended_action != "none":
                recommendations.append(rec)

        # 優先度順にソート
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda r: priority_order.get(r.priority, 3))

        return recommendations

    def _generate_upgrade_recommendations(
        self, type_definitions: list[TypeDefinition]
    ) -> list[UpgradeRecommendation]:
        """型レベルアップ推奨を生成

        Args:
            type_definitions: 型定義リスト

        Returns:
            UpgradeRecommendationのリスト
        """
        recommendations: list[UpgradeRecommendation] = []

        for type_def in type_definitions:
            # 使用回数は未実装なので0
            rec = self.upgrade_analyzer.analyze(type_def, usage_count=0)

            if rec:
                recommendations.append(rec)

        # 優先度と確信度順にソート
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(
            key=lambda r: (priority_order.get(r.priority, 3), -r.confidence)
        )

        return recommendations

    def _generate_general_recommendations(
        self, statistics: "TypeStatistics"
    ) -> list[str]:
        """一般的な推奨事項を生成

        Args:
            statistics: 統計情報

        Returns:
            推奨事項のリスト
        """
        recommendations = []

        # Level 2の比率が低い場合
        if statistics.level2_ratio < 0.25:
            recommendations.append(
                f"Level 2（Annotated）の比率が{statistics.level2_ratio * 100:.1f}%と低いです。"
                f"目標の25-35%に近づけるため、バリデーションが必要な型をLevel 2に変換してください。"
            )

        # Level 1の比率が高い場合
        if statistics.level1_ratio > 0.60:
            recommendations.append(
                f"Level 1（type エイリアス）の比率が{statistics.level1_ratio * 100:.1f}%と高いです。"
                f"制約が必要な型はLevel 2に、不要な型は削除を検討してください。"
            )

        # ドキュメント実装率が低い場合
        if statistics.documentation.implementation_rate < 0.70:
            recommendations.append(
                f"ドキュメント実装率が{statistics.documentation.implementation_rate * 100:.1f}%と低いです。"
                f"目標の80%以上に近づけるため、docstringを追加してください。"
            )

        # ドキュメント詳細度が低い場合
        if statistics.documentation.detail_rate < 0.50:
            recommendations.append(
                f"ドキュメント詳細度が{statistics.documentation.detail_rate * 100:.1f}%と低いです。"
                f"Attributes、Examples等のセクションを追加してドキュメントを充実させてください。"
            )

        return recommendations

    def _calculate_deviation(self, statistics: "TypeStatistics") -> dict[str, float]:
        """目標比率との乖離を計算

        Args:
            statistics: 統計情報

        Returns:
            乖離の辞書
        """
        return {
            "level1": statistics.level1_ratio - self.target_ratios["level1"],
            "level2": statistics.level2_ratio - self.target_ratios["level2"],
            "level3": statistics.level3_ratio - self.target_ratios["level3"],
        }
