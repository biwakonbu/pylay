"""
品質レポート機能のテスト

QualityReporterクラスのコンソール出力機能をテストします。
"""

from collections.abc import Generator
from io import StringIO

import pytest
from rich.console import Console

from src.core.analyzer.quality_models import (
    CodeLocation,
    QualityCheckResult,
    QualityIssue,
)
from src.core.analyzer.quality_reporter import QualityReporter
from src.core.analyzer.type_level_models import (
    DocumentationStatistics,
    TypeAnalysisReport,
    TypeStatistics,
)
from src.core.schemas.pylay_config import LevelThresholds, SeverityLevel


class TestQualityReporter:
    """QualityReporterクラスのテスト"""

    @pytest.fixture  # type: ignore[misc]
    def reporter(self) -> Generator[QualityReporter, None, None]:
        """テスト用のQualityReporterインスタンス"""
        yield QualityReporter(target_dirs=["src"])

    @pytest.fixture  # type: ignore[misc]
    def sample_check_result(
        self,
    ) -> Generator[QualityCheckResult, None, None]:
        """テスト用の品質チェック結果"""
        from pathlib import Path

        issue = QualityIssue(
            issue_type="primitive_usage",
            severity="warning",
            message="primitive型 str が直接使用されています",
            suggestion="ドメイン型を定義して使用してください",
            improvement_plan="ドメイン型を定義",
            location=CodeLocation(
                file=Path("src/test.py"),
                line=42,
                column=0,
                code="user_id: str = get_user_id()",
            ),
            primitive_type="str",
            priority_score=5,
            impact_score=3,
            difficulty_score=2,
        )

        result = QualityCheckResult(
            total_issues=1,
            error_count=0,
            warning_count=1,
            advice_count=0,
            has_errors=False,
            overall_score=0.9,
            issues=[issue],
            statistics=TypeStatistics(
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
            ),
            thresholds=LevelThresholds(),
            severity_levels=[
                SeverityLevel(name="error", color="red", threshold=0.0),
                SeverityLevel(name="warning", color="yellow", threshold=0.6),
                SeverityLevel(name="advice", color="blue", threshold=0.8),
            ],
        )

        yield result

    @pytest.fixture  # type: ignore[misc]
    def sample_report(self) -> Generator[TypeAnalysisReport, None, None]:
        """テスト用の型定義分析レポート"""
        report = TypeAnalysisReport(
            statistics=TypeStatistics(
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
            ),
            type_definitions=[],
            recommendations=[],
            upgrade_recommendations=[],
            docstring_recommendations=[],
            threshold_ratios={},
            deviation_from_threshold={},
        )

        yield report

    def test_init(self, reporter: QualityReporter) -> None:
        """初期化テスト"""
        assert reporter.console is not None
        assert reporter.target_dirs is not None
        assert len(reporter.target_dirs) > 0

    def test_generate_console_report_basic(
        self,
        reporter: QualityReporter,
        sample_check_result: QualityCheckResult,
        sample_report: TypeAnalysisReport,
    ) -> None:
        """基本的なコンソールレポート生成テスト"""
        # コンソール出力をキャプチャ
        string_io = StringIO()
        reporter.console = Console(file=string_io, force_terminal=True)

        # レポートを生成
        reporter.generate_console_report(sample_check_result, sample_report)

        # 出力を検証
        output = string_io.getvalue()
        assert "Type Definition Quality Report" in output
        assert "Summary" in output
        assert "Overall Score" in output

    def test_generate_console_report_with_details(
        self,
        reporter: QualityReporter,
        sample_check_result: QualityCheckResult,
        sample_report: TypeAnalysisReport,
    ) -> None:
        """詳細情報付きコンソールレポート生成テスト"""
        string_io = StringIO()
        reporter.console = Console(file=string_io, force_terminal=True)

        # 詳細情報付きでレポートを生成
        reporter.generate_console_report(sample_check_result, sample_report, show_details=True)

        output = string_io.getvalue()
        assert "Type Definition Quality Report" in output
        # 詳細情報が含まれていること
        assert len(output) > 100

    def test_generate_console_report_no_issues(
        self,
        reporter: QualityReporter,
        sample_report: TypeAnalysisReport,
    ) -> None:
        """問題がない場合のコンソールレポート生成テスト"""
        from src.core.schemas.pylay_config import LevelThresholds, SeverityLevel

        # 問題なしの結果を作成
        no_issue_result = QualityCheckResult(
            total_issues=0,
            error_count=0,
            warning_count=0,
            advice_count=0,
            has_errors=False,
            overall_score=1.0,
            issues=[],
            statistics=sample_report.statistics,
            thresholds=LevelThresholds(),
            severity_levels=[
                SeverityLevel(name="error", color="red", threshold=0.0),
                SeverityLevel(name="warning", color="yellow", threshold=0.6),
                SeverityLevel(name="advice", color="blue", threshold=0.8),
            ],
        )

        string_io = StringIO()
        reporter.console = Console(file=string_io, force_terminal=True)

        reporter.generate_console_report(no_issue_result, sample_report)

        output = string_io.getvalue()
        assert "品質問題は検出されませんでした" in output or "Overall Score" in output

    def test_generate_console_report_error_handling(
        self,
        reporter: QualityReporter,
        sample_report: TypeAnalysisReport,
    ) -> None:
        """エラーありの場合のコンソールレポート生成テスト"""
        from pathlib import Path

        from src.core.schemas.pylay_config import LevelThresholds, SeverityLevel

        # エラーありの結果を作成
        error_issue = QualityIssue(
            issue_type="level1_ratio_high",
            severity="error",
            message="Level 1比率が高すぎます",
            suggestion="Level 2に昇格してください",
            improvement_plan="Level 2に昇格",
            location=CodeLocation(
                file=Path("src/test.py"),
                line=10,
                column=0,
                code="type UserId = str",
            ),
            priority_score=1,
            impact_score=5,
            difficulty_score=3,
        )

        error_result = QualityCheckResult(
            total_issues=1,
            error_count=1,
            warning_count=0,
            advice_count=0,
            has_errors=True,
            overall_score=0.5,
            issues=[error_issue],
            statistics=sample_report.statistics,
            thresholds=LevelThresholds(),
            severity_levels=[
                SeverityLevel(name="error", color="red", threshold=0.0),
                SeverityLevel(name="warning", color="yellow", threshold=0.6),
                SeverityLevel(name="advice", color="blue", threshold=0.8),
            ],
        )

        string_io = StringIO()
        reporter.console = Console(file=string_io, force_terminal=True)

        reporter.generate_console_report(error_result, sample_report)

        output = string_io.getvalue()
        assert "Type Definition Quality Report" in output
        assert "ERROR" in output or "Error" in output or "Errors" in output
