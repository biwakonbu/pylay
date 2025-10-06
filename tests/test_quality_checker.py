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
        yield TypeLevelAnalyzer(config)

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
        # まず型分析レポートを作成
        analysis_report = type_analyzer.analyze_types()

        # 品質チェックを実行
        result = quality_checker.check_quality(analysis_report)

        # 結果の検証
        assert result is not None
        assert hasattr(result, "issues")
        assert hasattr(result, "statistics")
        assert hasattr(result, "has_errors")
        assert hasattr(result, "overall_score")
        assert hasattr(result, "total_issues")

    def test_get_quality_report(
        self, quality_checker: QualityChecker, type_analyzer: TypeLevelAnalyzer
    ) -> None:
        """品質レポート取得テスト"""
        # 型分析レポートを作成
        analysis_report = type_analyzer.analyze_types()

        # 品質レポートを取得
        report = quality_checker.get_quality_report(analysis_report)

        assert report is not None
        assert hasattr(report, "statistics")
        assert hasattr(report, "issues")
        assert hasattr(report, "overall_score")
