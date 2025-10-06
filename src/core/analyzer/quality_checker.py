"""
品質チェック機能

型定義の品質をチェックし、アドバイス・警告・エラーレベルで結果を報告します。
"""

from pathlib import Path
from typing import TYPE_CHECKING, Literal

from src.core.analyzer.code_locator import CodeLocator

if TYPE_CHECKING:
    from src.core.analyzer.code_locator import PrimitiveUsageDetail
from src.core.analyzer.improvement_templates import (
    VALIDATION_PATTERNS,
    extract_variable_name,
    format_validation_checklist,
    suggest_pydantic_type,
    suggest_type_name,
    suggest_validation_patterns,
)
from src.core.analyzer.quality_models import (
    CodeLocation,
    QualityCheckResult,
    QualityIssue,
)
from src.core.analyzer.type_level_models import TypeAnalysisReport, TypeStatistics
from src.core.schemas.pylay_config import (
    LevelThresholds,
    PylayConfig,
)


class QualityChecker:
    """型定義の品質をチェックするクラス"""

    def __init__(self, config: PylayConfig):
        """初期化

        Args:
            config: pylay設定オブジェクト
        """
        self.config = config

        # 品質チェック設定を取得（デフォルト値で初期化）
        self.thresholds = config.get_quality_thresholds() or LevelThresholds()
        self.error_conditions = config.get_error_conditions()
        self.severity_levels = config.get_severity_levels()
        self.improvement_guidance = config.get_improvement_guidance()

        # CodeLocatorを初期化（コード位置情報取得用）
        target_dirs = config.target_dirs if config.target_dirs else ["src"]
        self.code_locator = CodeLocator([Path(d) for d in target_dirs])

    def check_quality(self, report: TypeAnalysisReport) -> QualityCheckResult:
        """型定義の品質をチェック

        Args:
            report: 型定義分析レポート

        Returns:
            品質チェック結果
        """
        issues: list[QualityIssue] = []

        # 型レベル関連の問題をチェック
        issues.extend(self._check_type_level_issues(report.statistics))

        # ドキュメント関連の問題をチェック
        issues.extend(self._check_documentation_issues(report.statistics))

        # primitive型使用の問題をチェック
        issues.extend(self._check_primitive_usage_issues(report))

        # 非推奨typing使用の問題をチェック
        issues.extend(self._check_deprecated_typing_issues(report))

        # エラー条件をチェック
        issues.extend(self._check_error_conditions(report.statistics))

        # 深刻度レベルを計算して設定
        for issue in issues:
            issue.severity = self._calculate_severity(issue, report.statistics)

        # 全体統計を計算
        error_count = sum(1 for issue in issues if issue.severity == "エラー")
        warning_count = sum(1 for issue in issues if issue.severity == "警告")
        advice_count = sum(1 for issue in issues if issue.severity == "アドバイス")

        # 全体スコアを計算（エラーは大きく減点、警告は中程度、アドバイスは軽く減点）
        score_deduction = error_count * 0.3 + warning_count * 0.1 + advice_count * 0.05
        overall_score = max(0.0, 1.0 - score_deduction)

        return QualityCheckResult(
            total_issues=len(issues),
            error_count=error_count,
            warning_count=warning_count,
            advice_count=advice_count,
            has_errors=error_count > 0,
            overall_score=overall_score,
            issues=issues,
            statistics=report.statistics,
            thresholds=self.thresholds,
            severity_levels=self.severity_levels,
        )

    def _check_type_level_issues(
        self, statistics: TypeStatistics
    ) -> list[QualityIssue]:
        """型レベル関連の問題をチェック"""
        issues: list[QualityIssue] = []

        # Level 1の比率が高すぎる場合
        if statistics.level1_ratio > self.thresholds.level1_max:
            issues.append(
                QualityIssue(
                    issue_type="level1_ratio_high",
                    message=(
                        f"Level 1型エイリアスの比率が"
                        f"{statistics.level1_ratio * 100:.1f}%と高すぎます"
                        f"（上限: {self.thresholds.level1_max * 100:.0f}%）"
                    ),
                    suggestion="制約が必要な型はLevel 2（Annotated）に昇格してください",
                    improvement_plan=self._get_improvement_plan("level1_to_level2"),
                )
            )

        # Level 2の比率が低すぎる場合
        if statistics.level2_ratio < self.thresholds.level2_min:
            issues.append(
                QualityIssue(
                    issue_type="level2_ratio_low",
                    message=(
                        f"Level 2制約付き型の比率が"
                        f"{statistics.level2_ratio * 100:.1f}%と低すぎます"
                        f"（下限: {self.thresholds.level2_min * 100:.0f}%）"
                    ),
                    suggestion="バリデーションが必要な型をLevel 2に昇格してください",
                    improvement_plan=self._get_improvement_plan("level1_to_level2"),
                )
            )

        # Level 3の比率が低すぎる場合
        if statistics.level3_ratio < self.thresholds.level3_min:
            issues.append(
                QualityIssue(
                    issue_type="level3_ratio_low",
                    message=(
                        f"Level 3 BaseModelの比率が"
                        f"{statistics.level3_ratio * 100:.1f}%と低すぎます"
                        f"（下限: {self.thresholds.level3_min * 100:.0f}%）"
                    ),
                    suggestion="複雑なドメイン型をLevel 3に昇格してください",
                    improvement_plan=self._get_improvement_plan("level2_to_level3"),
                )
            )

        return issues

    def _check_documentation_issues(
        self, statistics: TypeStatistics
    ) -> list[QualityIssue]:
        """ドキュメント関連の問題をチェック"""
        issues: list[QualityIssue] = []

        # ドキュメント実装率が低い場合
        if statistics.documentation.implementation_rate < 0.70:
            doc_rate = statistics.documentation.implementation_rate
            issues.append(
                QualityIssue(
                    issue_type="documentation_low",
                    message=f"ドキュメント実装率が{doc_rate * 100:.1f}%と低いです",
                    suggestion="すべての型定義にdocstringを追加してください",
                    improvement_plan=self._get_improvement_plan("add_documentation"),
                )
            )

        # ドキュメント詳細度が低い場合
        if statistics.documentation.detail_rate < 0.50:
            detail_rate = statistics.documentation.detail_rate
            issues.append(
                QualityIssue(
                    issue_type="documentation_detail_low",
                    message=f"ドキュメント詳細度が{detail_rate * 100:.1f}%と低いです",
                    suggestion="詳細な説明と使用例を追加してください",
                    improvement_plan=self._get_improvement_plan("add_documentation"),
                )
            )

        return issues

    def _check_primitive_usage_issues(
        self, report: TypeAnalysisReport
    ) -> list[QualityIssue]:
        """primitive型使用の問題をチェック（位置情報付き）"""
        issues: list[QualityIssue] = []

        # CodeLocatorで詳細情報を取得
        primitive_details = self.code_locator.find_primitive_usages()

        for detail in primitive_details:
            # 位置情報を含むQualityIssueを作成
            location = CodeLocation(
                file=detail.location.file,
                line=detail.location.line,
                column=0,
                context_before=detail.location.context_before
                if hasattr(detail.location, "context_before")
                else [],
                code=detail.location.code,
                context_after=detail.location.context_after
                if hasattr(detail.location, "context_after")
                else [],
            )

            prim_msg = f"primitive型 {detail.primitive_type} が直接使用されています"
            issues.append(
                QualityIssue(
                    issue_type="primitive_usage",
                    message=prim_msg,
                    location=location,
                    suggestion="ドメイン型を定義して使用してください",
                    improvement_plan=self._generate_primitive_replacement_plan(detail),
                )
            )

        return issues

    def _check_deprecated_typing_issues(
        self, report: TypeAnalysisReport
    ) -> list[QualityIssue]:
        """非推奨typing使用の問題をチェック"""
        issues: list[QualityIssue] = []

        # 非推奨typingの使用を検出
        if report.statistics.deprecated_typing_ratio > 0.05:
            depr_ratio = report.statistics.deprecated_typing_ratio
            depr_msg = f"非推奨のtyping型が{depr_ratio * 100:.1f}%使用されています"
            issues.append(
                QualityIssue(
                    issue_type="deprecated_typing_usage",
                    message=depr_msg,
                    suggestion="Python 3.13標準構文（例: list[str]）を使用してください",
                    improvement_plan=(
                        "typing.Union → X | Y, typing.List → list[X] "
                        "に置き換えてください"
                    ),
                )
            )

        return issues

    def _check_error_conditions(self, statistics: TypeStatistics) -> list[QualityIssue]:
        """エラー条件をチェック"""
        issues: list[QualityIssue] = []

        for condition in self.error_conditions:
            if self._evaluate_condition(condition.condition, statistics):
                issues.append(
                    QualityIssue(
                        issue_type="custom_error_condition",
                        severity="エラー",  # カスタム条件はすべてエラー扱い
                        message=condition.message,
                        suggestion="設定された基準を満たすようにコードを修正してください",
                        improvement_plan="pyproject.tomlの基準設定を確認し、適切な閾値に調整してください",
                    )
                )

        return issues

    def _evaluate_condition(self, condition: str, statistics: TypeStatistics) -> bool:
        """条件式を評価

        Args:
            condition: 条件式（例: "level1_ratio > 0.20"）
            statistics: 統計情報

        Returns:
            条件が真の場合はTrue
        """
        try:
            # 統計情報の属性をローカル変数として設定（eval()で使用）
            level1_ratio = statistics.level1_ratio  # noqa: F841
            level2_ratio = statistics.level2_ratio  # noqa: F841
            level3_ratio = statistics.level3_ratio  # noqa: F841
            primitive_usage_ratio = statistics.primitive_usage_ratio  # noqa: F841
            deprecated_typing_ratio = (  # noqa: F841
                statistics.deprecated_typing_ratio
            )
            documentation_rate = (  # noqa: F841
                statistics.documentation.implementation_rate
            )
            detail_rate = statistics.documentation.detail_rate  # noqa: F841

            # 条件式を評価
            result = eval(condition)
            return bool(result)

        except Exception:
            # 評価エラーの場合はFalseを返す
            return False

    def _calculate_severity(
        self, issue: QualityIssue, statistics: TypeStatistics
    ) -> Literal["アドバイス", "警告", "エラー"]:
        """問題の深刻度レベルを計算"""
        # ベーススコアを計算（問題の種類によって重み付け）
        base_score = self._calculate_base_score(issue.issue_type, statistics)

        # 深刻度レベルを決定
        for level in sorted(
            self.severity_levels, key=lambda x: x.threshold, reverse=True
        ):
            name = level.name
            # 型チェックを満たすため、明示的に判定
            if name in ("アドバイス", "警告", "エラー"):
                if base_score >= level.threshold:
                    return name  # type: ignore[return-value]

        # デフォルトはアドバイス
        return "アドバイス"

    def _calculate_base_score(
        self, issue_type: str, statistics: TypeStatistics
    ) -> float:
        """問題のベーススコアを計算（0.0〜1.0）"""
        base_scores = {
            "level1_ratio_high": 0.3,
            "level2_ratio_low": 0.4,
            "level3_ratio_low": 0.5,
            "documentation_low": 0.6,
            "documentation_detail_low": 0.7,
            "primitive_usage_high": 0.8,
            "deprecated_typing_usage": 0.9,
            "custom_error_condition": 1.0,
        }

        base_score = base_scores.get(issue_type, 0.5)

        # 実際の比率に基づいてスコアを調整
        if "ratio" in issue_type:
            if "high" in issue_type:
                # 高い比率ほど高いスコア（悪い状態）
                if "level1" in issue_type:
                    ratio_diff = max(
                        0, statistics.level1_ratio - self.thresholds.level1_max
                    )
                    base_score += ratio_diff * 2.0
                elif "primitive" in issue_type:
                    ratio_diff = max(0, statistics.primitive_usage_ratio - 0.10)
                    base_score += ratio_diff * 3.0
            elif "low" in issue_type:
                # 低い比率ほど高いスコア（悪い状態）
                if "level2" in issue_type:
                    ratio_diff = max(
                        0, self.thresholds.level2_min - statistics.level2_ratio
                    )
                    base_score += ratio_diff * 2.0
                elif "level3" in issue_type:
                    ratio_diff = max(
                        0, self.thresholds.level3_min - statistics.level3_ratio
                    )
                    base_score += ratio_diff * 2.0

        return min(1.0, base_score)

    def _get_improvement_plan(self, guidance_level: str) -> str:
        """改善プランのガイダンスを取得"""
        for guidance in self.improvement_guidance:
            if guidance.level == guidance_level:
                return guidance.suggestion

        # デフォルトの改善プラン
        return "適切な型定義パターンを使用して改善してください"

    def _generate_primitive_replacement_plan(
        self, detail: "PrimitiveUsageDetail"
    ) -> str:
        """primitive型置き換えの詳細プランを生成

        Args:
            detail: PrimitiveUsageDetail

        Returns:
            フォーマット済みの改善プラン
        """
        # 変数名を抽出
        var_name = extract_variable_name(detail.location.code)

        # Pydantic提供の型を優先的に推奨
        pydantic_type = suggest_pydantic_type(var_name, detail.primitive_type)

        if pydantic_type:
            # Pydantic型が見つかった場合
            fixed_code = detail.location.code.replace(
                f": {detail.primitive_type}", f": {pydantic_type['type']}"
            ).strip()

            plan = f"""primitive型 {detail.primitive_type} をPydantic型に置き換える手順:

★ 推奨: Pydantic提供の型を使用（最もシンプル）

Step 1: Pydantic型をインポート

  {pydantic_type['import']}

  説明: {pydantic_type['description']}
  例: {pydantic_type['example']}

Step 2: 使用箇所を修正

  File: {detail.location.file}:{detail.location.line}

  # Before
  {detail.location.code.strip()}

  # After
  {pydantic_type['import']}
  {fixed_code}

利点:
  - 自動バリデーション（Pydanticが提供）
  - 追加のコード不要
  - 標準的な型定義パターン
  - ドキュメント自動生成対応

参考: https://docs.pydantic.dev/latest/api/types/
"""
        else:
            # カスタム型定義が必要な場合
            type_candidates = suggest_type_name(var_name, detail.primitive_type)
            validation_patterns = suggest_validation_patterns(
                var_name, detail.primitive_type
            )

            # バリデーション例を構築
            validation_examples = []
            for pattern_key in validation_patterns:
                if pattern_key in VALIDATION_PATTERNS:
                    pattern = VALIDATION_PATTERNS[pattern_key]
                    validation_examples.append(f"  # {pattern['description']}")
                    validation_examples.append(f"  {pattern['validator']}")

            validation_code = (
                "\n\n".join(validation_examples)
                if validation_examples
                else "  # TODO: 適切なバリデーションを実装"
            )

            type_candidates_formatted = "\n  ".join(
                f"- {name}" for name in type_candidates
            )
            fixed_code = detail.location.code.replace(
                f": {detail.primitive_type}", f": {type_candidates[0]}"
            ).strip()
            checklist = format_validation_checklist(detail.primitive_type)

            plan = f"""primitive型 {detail.primitive_type} をドメイン型に置き換える手順:

Step 1: src/core/schemas/types.py に型定義を作成

  型名の候補（コードから推測）:
  {type_candidates_formatted}

  # Level 1: 単純な型エイリアス
  type {type_candidates[0]} = {detail.primitive_type}

  # Level 2: 制約付き型（推奨）
  from typing import Annotated
  from pydantic import AfterValidator

{validation_code}

  type {type_candidates[0]} = Annotated[
      {detail.primitive_type}, AfterValidator(validate_{var_name})
  ]

Step 2: 使用箇所を修正

  File: {detail.location.file}:{detail.location.line}

  # インポート追加
  from src.core.schemas.types import {type_candidates[0]}

  # Before
  {detail.location.code.strip()}

  # After
  {fixed_code}

Step 3: バリデーションの検討

  この型に必要な制約を検討してください:
  {checklist}

Implementation Context:
  - Why: primitive型の直接使用は型の意図を不明確にします
  - Effect: 型名により「何の{detail.primitive_type}か」が明確になります
  - Impact: {type_candidates[0]}を使う全ての箇所で型安全性が向上します

Tools and References:
  - Pydantic AfterValidator - バリデーション実装
  - typing.Annotated - 型制約の追加
  - docs/typing-rule.md - 型定義ルール
  - src/core/schemas/types.py - 既存の型定義例

Related Files:
  - {detail.location.file}:{detail.location.line} - 修正対象
  - src/core/schemas/types.py - 型定義を追加
"""
        return plan
