"""
品質チェック機能のテスト

QualityCheckerクラスの機能をテストします。
"""

from collections.abc import Generator

import pytest

from src.core.analyzer.quality_checker import QualityChecker
from src.core.analyzer.type_level_analyzer import TypeLevelAnalyzer
from src.core.schemas.pylay_config import PylayConfig


class TestQualityChecker:
    """QualityCheckerクラスのテスト"""

    @pytest.fixture  # type: ignore[misc]
    def config(self) -> Generator[PylayConfig, None, None]:
        """テスト用の設定オブジェクト"""
        yield PylayConfig(
            target_dirs=["src"],
            quality_thresholds=None,
        )

    @pytest.fixture  # type: ignore[misc]
    def type_analyzer(
        self, config: PylayConfig
    ) -> Generator[TypeLevelAnalyzer, None, None]:
        """テスト用のTypeLevelAnalyzerインスタンス"""
        yield TypeLevelAnalyzer()

    @pytest.fixture  # type: ignore[misc]
    def quality_checker(
        self, config: PylayConfig
    ) -> Generator[QualityChecker, None, None]:
        """テスト用のQualityCheckerインスタンス"""
        yield QualityChecker(config)

    def test_init(self, quality_checker: QualityChecker) -> None:
        """初期化テスト"""
        assert quality_checker.config is not None
        assert quality_checker.thresholds is not None
        assert quality_checker.code_locator is not None

    def test_check_quality_basic(
        self, quality_checker: QualityChecker, type_analyzer: TypeLevelAnalyzer
    ) -> None:
        """基本的な品質チェックテスト"""
        from pathlib import Path

        # まず型分析レポートを作成
        analysis_report = type_analyzer.analyze_directory(Path("src"))

        # 品質チェックを実行
        result = quality_checker.check_quality(analysis_report)

        # 結果の検証
        assert result is not None
        assert hasattr(result, "issues")
        assert hasattr(result, "statistics")
        assert hasattr(result, "has_errors")
        assert hasattr(result, "overall_score")
        assert hasattr(result, "total_issues")

    def test_severity_calculation(self, quality_checker: QualityChecker) -> None:
        """深刻度判定ロジックのテスト"""
        from src.core.analyzer.quality_models import QualityIssue
        from src.core.analyzer.type_level_models import (
            DocumentationStatistics,
            TypeStatistics,
        )

        # テスト用のダミー統計情報
        test_stats = TypeStatistics(
            total_count=100,
            level1_count=20,
            level2_count=50,
            level3_count=30,
            other_count=0,
            level1_ratio=0.2,
            level2_ratio=0.5,
            level3_ratio=0.3,
            other_ratio=0.0,
            by_directory={},
            by_category={},
            documentation=DocumentationStatistics(
                total_types=100,
                documented_types=80,
                undocumented_types=20,
                implementation_rate=0.8,
                minimal_docstrings=20,
                detailed_docstrings=60,
                detail_rate=0.6,
                avg_docstring_lines=5.0,
                quality_score=0.7,
                by_level={},
                by_level_avg_lines={},
                by_format={},
            ),
            primitive_usage_count=10,
            deprecated_typing_count=5,
            primitive_usage_ratio=0.1,
            deprecated_typing_ratio=0.05,
        )

        # テストケース1: custom_error_condition (base_score=1.0) → error
        issue1 = QualityIssue(
            issue_type="custom_error_condition",
            message="カスタムエラー条件",
            suggestion="修正してください",
            improvement_plan="基準を満たすよう修正してください",
        )
        severity1 = quality_checker._calculate_severity(issue1, test_stats)
        assert severity1 == "error", (
            f"custom_error_condition (score=1.0): " f"期待=error, 実際={severity1}"
        )

        # テストケース2: primitive_usage (base_score=0.7) → warning
        issue2 = QualityIssue(
            issue_type="primitive_usage",
            message="primitive型使用",
            suggestion="ドメイン型を使用してください",
            improvement_plan="ドメイン型を定義して置き換えてください",
        )
        severity2 = quality_checker._calculate_severity(issue2, test_stats)
        assert severity2 == "warning", (
            f"primitive_usage (score=0.7): " f"期待=warning, 実際={severity2}"
        )

        # テストケース3: primitive_usage_excluded (base_score=0.85) → advice
        issue3 = QualityIssue(
            issue_type="primitive_usage_excluded",
            message="primitive型使用（除外パターン）",
            suggestion="現状維持",
            improvement_plan="現状維持（変更不要）",
        )
        severity3 = quality_checker._calculate_severity(issue3, test_stats)
        assert severity3 == "advice", (
            f"primitive_usage_excluded (score=0.85): " f"期待=advice, 実際={severity3}"
        )

        # テストケース4: level1_ratio_high (base_score=0.3) → error
        issue4 = QualityIssue(
            issue_type="level1_ratio_high",
            message="Level 1比率が高い",
            suggestion="Level 2に昇格してください",
            improvement_plan="制約が必要な型をLevel 2に昇格してください",
        )
        severity4 = quality_checker._calculate_severity(issue4, test_stats)
        assert severity4 == "error", (
            f"level1_ratio_high (score=0.3): " f"期待=error, 実際={severity4}"
        )
