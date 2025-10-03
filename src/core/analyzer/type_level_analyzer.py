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

    def __init__(self, threshold_ratios: dict[str, float] | None = None):
        """初期化

        Args:
            threshold_ratios: 警告閾値（デフォルト: 推奨閾値）
                - level1_max: Level 1の上限（これを超えたら警告）
                - level2_min: Level 2の下限（これを下回ったら警告）
                - level3_min: Level 3の下限（これを下回ったら警告）
        """
        self.classifier = TypeClassifier()
        self.statistics_calculator = TypeStatisticsCalculator()
        self.docstring_analyzer = DocstringAnalyzer()
        self.upgrade_analyzer = TypeUpgradeAnalyzer()
        self.reporter = TypeReporter(threshold_ratios)

        self.threshold_ratios = threshold_ratios or {
            "level1_max": 0.20,  # Level 1は20%以下が望ましい
            "level2_min": 0.40,  # Level 2は40%以上が望ましい
            "level3_min": 0.15,  # Level 3は15%以上が望ましい
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

        # 重複を除去（同じ型名の最初の定義のみを保持）
        unique_type_definitions = self._deduplicate_type_definitions(
            all_type_definitions
        )

        # 統計情報を計算（すべての定義を使用）
        statistics = self.statistics_calculator.calculate(all_type_definitions)

        # ドキュメント推奨を生成（重複除去後の定義を使用）
        docstring_recommendations = self._generate_docstring_recommendations(
            unique_type_definitions
        )

        # 型レベルアップ推奨を生成（すべての定義を使用して使用回数をカウント）
        upgrade_recommendations: list[UpgradeRecommendation] = []
        if include_upgrade_recommendations:
            upgrade_recommendations = self._generate_upgrade_recommendations(
                all_type_definitions
            )
            # 重複除去
            upgrade_recommendations = self._deduplicate_upgrade_recommendations(
                upgrade_recommendations
            )

        # 一般的な推奨事項を生成
        recommendations = self._generate_general_recommendations(statistics)

        # 警告閾値との乖離を計算
        deviation_from_threshold = self._calculate_deviation(statistics)

        return TypeAnalysisReport(
            statistics=statistics,
            type_definitions=unique_type_definitions,
            recommendations=recommendations,
            upgrade_recommendations=upgrade_recommendations,
            docstring_recommendations=docstring_recommendations,
            threshold_ratios=self.threshold_ratios,
            deviation_from_threshold=deviation_from_threshold,
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

        # 警告閾値との乖離を計算
        deviation_from_threshold = self._calculate_deviation(statistics)

        return TypeAnalysisReport(
            statistics=statistics,
            type_definitions=type_definitions,
            recommendations=recommendations,
            upgrade_recommendations=upgrade_recommendations,
            docstring_recommendations=docstring_recommendations,
            threshold_ratios=self.threshold_ratios,
            deviation_from_threshold=deviation_from_threshold,
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

        # 使用回数をカウント
        usage_counts = self._count_type_usage(type_definitions)

        for type_def in type_definitions:
            # 使用回数を取得
            usage_count = usage_counts.get(type_def.name, 0)
            rec = self.upgrade_analyzer.analyze(type_def, usage_count=usage_count)

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

        # Level 1の比率が高すぎる場合（上限を超えている）
        level1_max = self.threshold_ratios["level1_max"]
        if statistics.level1_ratio > level1_max:
            recommendations.append(
                f"⚠️ Level 1（type エイリアス）の比率が{statistics.level1_ratio * 100:.1f}%と高すぎます。"  # noqa: E501
                f"推奨上限の{level1_max * 100:.0f}%を超えています。"
                f"制約が必要な型はLevel 2に昇格させ、不要な型は削除を検討してください。"
            )

        # Level 2の比率が低すぎる場合（下限を下回っている）
        level2_min = self.threshold_ratios["level2_min"]
        if statistics.level2_ratio < level2_min:
            recommendations.append(
                f"⚠️ Level 2（Annotated）の比率が{statistics.level2_ratio * 100:.1f}%と低すぎます。"  # noqa: E501
                f"推奨下限の{level2_min * 100:.0f}%を下回っています。"
                f"バリデーションが必要な型をLevel 2に昇格させてください。"
            )

        # Level 3の比率が低すぎる場合（下限を下回っている）
        level3_min = self.threshold_ratios["level3_min"]
        if statistics.level3_ratio < level3_min:
            recommendations.append(
                f"⚠️ Level 3（BaseModel）の比率が{statistics.level3_ratio * 100:.1f}%と低すぎます。"  # noqa: E501
                f"推奨下限の{level3_min * 100:.0f}%を下回っています。"
                f"複雑なドメイン型をLevel 3に昇格させてください。"
            )

        # ドキュメント実装率が低い場合
        if statistics.documentation.implementation_rate < 0.70:
            recommendations.append(
                f"ドキュメント実装率が{statistics.documentation.implementation_rate * 100:.1f}%と低いです。"  # noqa: E501
                f"目標の80%以上に近づけるため、docstringを追加してください。"
            )

        # ドキュメント詳細度が低い場合
        if statistics.documentation.detail_rate < 0.50:
            recommendations.append(
                f"ドキュメント詳細度が{statistics.documentation.detail_rate * 100:.1f}%と低いです。"  # noqa: E501
                f"Attributes、Examples等のセクションを追加してドキュメントを充実させてください。"
            )

        return recommendations

    def _calculate_deviation(self, statistics: "TypeStatistics") -> dict[str, float]:
        """警告閾値との乖離を計算

        Args:
            statistics: 統計情報

        Returns:
            乖離の辞書（正の値 = 閾値を超えている、負の値 = 閾値を下回っている）
        """
        return {
            "level1_max": statistics.level1_ratio
            - self.threshold_ratios["level1_max"],  # 正 = 上限超過（警告）
            "level2_min": statistics.level2_ratio
            - self.threshold_ratios["level2_min"],  # 負 = 下限未満（警告）
            "level3_min": statistics.level3_ratio
            - self.threshold_ratios["level3_min"],  # 負 = 下限未満（警告）
        }

    def _count_type_usage(
        self, type_definitions: list[TypeDefinition]
    ) -> dict[str, int]:
        """型の使用回数をカウント

        現在の実装では、正確な参照解析を行わず、すべての型に最小使用回数（1）を割り当てます。
        これにより、型が「未使用」と誤判定されることを防ぎます。

        将来的には、AST解析やmypyの型情報を活用して、実際の参照箇所をカウントする
        実装に置き換えることが望ましいです。

        Args:
            type_definitions: 型定義リスト

        Returns:
            型名 -> 使用回数の辞書（すべての型に最小値1を設定）
        """
        # すべての型に最小使用回数（1）を設定
        # これにより、「未使用」と誤判定されることを防ぐ
        usage_counts = {td.name: 1 for td in type_definitions}

        return usage_counts

    def _deduplicate_type_definitions(
        self, type_definitions: list[TypeDefinition]
    ) -> list[TypeDefinition]:
        """型定義の重複を除去

        Args:
            type_definitions: 型定義リスト

        Returns:
            重複除去後の型定義リスト
        """
        seen_names: set[str] = set()
        unique_types: list[TypeDefinition] = []

        for td in type_definitions:
            if td.name not in seen_names:
                seen_names.add(td.name)
                unique_types.append(td)

        return unique_types

    def _deduplicate_upgrade_recommendations(
        self, recommendations: list[UpgradeRecommendation]
    ) -> list[UpgradeRecommendation]:
        """型レベルアップ推奨の重複を除去

        Args:
            recommendations: 推奨事項リスト

        Returns:
            重複除去後の推奨事項リスト
        """
        seen_names: set[str] = set()
        unique_recs: list[UpgradeRecommendation] = []

        for rec in recommendations:
            if rec.type_name not in seen_names:
                seen_names.add(rec.type_name)
                unique_recs.append(rec)

        return unique_recs
