"""
品質チェック機能のテスト

QualityCheckerクラスの機能をテストします。
"""

import pytest

from src.core.analyzer.quality_checker import QualityChecker
from src.core.analyzer.type_level_analyzer import TypeLevelAnalyzer
from src.core.schemas.pylay_config import PylayConfig, QualityCheckConfig


@pytest.fixture
def config() -> PylayConfig:
    """テスト用の設定オブジェクト"""
    return PylayConfig(target_dirs=["src"])


@pytest.fixture
def type_analyzer() -> TypeLevelAnalyzer:
    """テスト用のTypeLevelAnalyzerインスタンス"""
    return TypeLevelAnalyzer()


@pytest.fixture
def quality_checker(config: PylayConfig) -> QualityChecker:
    """テスト用のQualityCheckerインスタンス"""
    return QualityChecker(config)


class TestQualityChecker:
    """QualityCheckerクラスのテスト"""

    def test_init(self, quality_checker: QualityChecker) -> None:
        """初期化テスト"""
        assert quality_checker.config is not None
        assert quality_checker.thresholds is not None
        assert quality_checker.code_locator is not None

    def test_check_quality_basic(self, quality_checker: QualityChecker, type_analyzer: TypeLevelAnalyzer) -> None:
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
        assert severity1 == "error", f"custom_error_condition (score=1.0): 期待=error, 実際={severity1}"

        # テストケース2: primitive_usage (base_score=0.7) → warning
        issue2 = QualityIssue(
            issue_type="primitive_usage",
            message="primitive型使用",
            suggestion="ドメイン型を使用してください",
            improvement_plan="ドメイン型を定義して置き換えてください",
        )
        severity2 = quality_checker._calculate_severity(issue2, test_stats)
        assert severity2 == "warning", f"primitive_usage (score=0.7): 期待=warning, 実際={severity2}"

        # テストケース3: primitive_usage_excluded (base_score=0.85) → advice
        issue3 = QualityIssue(
            issue_type="primitive_usage_excluded",
            message="primitive型使用（除外パターン）",
            suggestion="現状維持",
            improvement_plan="現状維持（変更不要）",
        )
        severity3 = quality_checker._calculate_severity(issue3, test_stats)
        assert severity3 == "advice", f"primitive_usage_excluded (score=0.85): 期待=advice, 実際={severity3}"

        # テストケース4: level1_ratio_high (base_score=0.3) → error
        issue4 = QualityIssue(
            issue_type="level1_ratio_high",
            message="Level 1比率が高い",
            suggestion="Level 2に昇格してください",
            improvement_plan="制約が必要な型をLevel 2に昇格してください",
        )
        severity4 = quality_checker._calculate_severity(issue4, test_stats)
        assert severity4 == "error", f"level1_ratio_high (score=0.3): 期待=error, 実際={severity4}"

    def test_priority_calculation(self, quality_checker: QualityChecker) -> None:
        """優先度計算のテスト"""
        from src.core.analyzer.quality_models import QualityIssue

        # テストケース1: error + primitive_usage → 優先度高
        issue1 = QualityIssue(
            issue_type="primitive_usage",
            severity="error",
            message="primitive型使用",
            suggestion="ドメイン型を使用",
            improvement_plan="ドメイン型を定義",
        )
        priority1 = quality_checker._calculate_priority_score(issue1)
        assert priority1 == -1  # 0 (error) + (-1) (type_penalty)

        # テストケース2: warning + documentation → 優先度低
        issue2 = QualityIssue(
            issue_type="documentation_low",
            severity="warning",
            message="ドキュメント不足",
            suggestion="docstringを追加",
            improvement_plan="各型にdocstringを追加",
        )
        priority2 = quality_checker._calculate_priority_score(issue2)
        assert priority2 == 5  # 3 (warning) + 2 (doc penalty)

        # 優先度順にソート確認（スコアを設定してから）
        issue1.priority_score = priority1
        issue1.impact_score = 5
        issue1.difficulty_score = 2
        issue2.priority_score = priority2
        issue2.impact_score = 3
        issue2.difficulty_score = 3

        issues = [issue2, issue1]  # 逆順
        sorted_issues = quality_checker._prioritize_issues(issues)
        assert sorted_issues[0].issue_type == "primitive_usage"  # 優先度高が先

    def test_impact_calculation(self, quality_checker: QualityChecker, type_analyzer: TypeLevelAnalyzer) -> None:
        """影響度計算のテスト"""
        from pathlib import Path

        from src.core.analyzer.quality_models import QualityIssue

        # 実際のレポートを取得
        high_report = type_analyzer.analyze_directory(Path("src"))

        # primitive型使用の問題
        issue = QualityIssue(
            issue_type="primitive_usage",
            severity="warning",
            message="primitive型使用",
            suggestion="ドメイン型を使用",
            improvement_plan="ドメイン型を定義",
            primitive_type="str",
        )

        # 影響度を計算（実際の使用率に基づく）
        impact = quality_checker._calculate_impact_score(issue, high_report)
        assert impact > 0  # 何らかの影響度が計算される
        assert isinstance(impact, int)

    def test_difficulty_estimation(self, quality_checker: QualityChecker) -> None:
        """修正難易度推定のテスト"""
        from src.core.analyzer.quality_models import QualityIssue

        # Pydantic型推奨あり → 簡単
        easy_issue = QualityIssue(
            issue_type="primitive_usage",
            severity="advice",
            message="primitive型使用",
            suggestion="EmailStrを使用",
            improvement_plan="EmailStrに置き換え",
            recommended_type="EmailStr",
        )
        difficulty1 = quality_checker._estimate_difficulty(easy_issue)
        assert difficulty1 == 2  # 非常に簡単

        # カスタム型必要 → 中程度
        medium_issue = QualityIssue(
            issue_type="primitive_usage",
            severity="advice",
            message="primitive型使用",
            suggestion="カスタム型を定義",
            improvement_plan="カスタム型を定義",
            recommended_type="custom",
        )
        difficulty2 = quality_checker._estimate_difficulty(medium_issue)
        assert difficulty2 == 5  # 中程度

        # Level比率問題 → 難しい
        hard_issue = QualityIssue(
            issue_type="level2_ratio_low",
            severity="error",
            message="Level 2比率が低い",
            suggestion="Level 2に昇格",
            improvement_plan="複数の型をLevel 2に昇格",
        )
        difficulty3 = quality_checker._estimate_difficulty(hard_issue)
        assert difficulty3 == 8  # 難しい

    def test_generate_fix_checklist(self, quality_checker: QualityChecker) -> None:
        """修正チェックリスト生成のテスト"""
        from pathlib import Path

        from src.core.analyzer.quality_models import CodeLocation, QualityIssue

        # primitive型使用の問題
        location = CodeLocation(
            file=Path("src/test.py"),
            line=42,
            column=0,
            code="user_id: str = get_user_id()",
        )
        issue = QualityIssue(
            issue_type="primitive_usage",
            severity="warning",
            message="primitive型使用",
            suggestion="ドメイン型を使用",
            improvement_plan="ドメイン型を定義",
            location=location,
            recommended_type="UserId",
        )

        checklist = quality_checker.generate_fix_checklist(issue)
        assert "[ ]" in checklist
        assert "src/core/schemas/types.py" in checklist
        assert "UserId" in checklist
        assert "src/test.py:42" in checklist

        # Level比率問題
        level_issue = QualityIssue(
            issue_type="level1_ratio_high",
            severity="error",
            message="Level 1比率が高い",
            suggestion="Level 2に昇格",
            improvement_plan="Level 2に昇格",
        )
        level_checklist = quality_checker.generate_fix_checklist(level_issue)
        assert "[ ]" in level_checklist
        assert "Level 1型を特定" in level_checklist
        assert "Level 2" in level_checklist

    def test_empty_project(self, quality_checker: QualityChecker) -> None:
        """空のプロジェクトに対する品質チェックテスト"""
        from src.core.analyzer.type_level_models import (
            DocumentationStatistics,
            TypeAnalysisReport,
            TypeStatistics,
        )

        # 空のレポートを作成
        empty_report = TypeAnalysisReport(
            statistics=TypeStatistics(
                total_count=0,
                level1_count=0,
                level2_count=0,
                level3_count=0,
                other_count=0,
                level1_ratio=0.0,
                level2_ratio=0.0,
                level3_ratio=0.0,
                other_ratio=0.0,
                by_directory={},
                by_category={},
                documentation=DocumentationStatistics(
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
                ),
                primitive_usage_count=0,
                deprecated_typing_count=0,
                primitive_usage_ratio=0.0,
                deprecated_typing_ratio=0.0,
            ),
            type_definitions=[],
            recommendations=[],
            upgrade_recommendations=[],
            docstring_recommendations=[],
            threshold_ratios={},
            deviation_from_threshold={},
        )

        # 品質チェックを実行
        result = quality_checker.check_quality(empty_report)

        # 空のプロジェクトでもエラーなく完了すること
        assert result is not None
        # CodeLocatorがsrcディレクトリをスキャンするため、問題が検出される可能性がある
        assert isinstance(result.total_issues, int)
        assert result.overall_score >= 0.0

    def test_no_type_definitions(self, quality_checker: QualityChecker, type_analyzer: TypeLevelAnalyzer) -> None:
        """型定義が全くないプロジェクトの処理テスト"""
        from pathlib import Path
        from tempfile import TemporaryDirectory

        # 一時ディレクトリに型定義のないPythonファイルを作成
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text(
                """# 型定義なしのファイル
def foo():
    return 42

x = foo()
""",
            )

            # 解析を実行
            report = type_analyzer.analyze_directory(Path(tmpdir))

            # 品質チェックを実行
            result = quality_checker.check_quality(report)

            # エラーなく完了すること
            assert result is not None
            assert isinstance(result.total_issues, int)

    def test_invalid_threshold_config(self) -> None:
        """不正な閾値設定の処理テスト"""
        from src.core.schemas.pylay_config import LevelThresholds

        # 不正な閾値（合計が1.0を超える）を設定
        invalid_config = PylayConfig(
            target_dirs=["src"],
            quality_check=QualityCheckConfig(
                level_thresholds=LevelThresholds(
                    level1_max=0.5,
                    level2_min=0.6,  # level1_max + level2_min > 1.0
                    level3_min=0.3,
                ),
            ),
        )

        # QualityCheckerが初期化できること（デフォルト値で補正される可能性）
        checker = QualityChecker(invalid_config)
        assert checker is not None
        assert checker.thresholds is not None
