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
    extract_variable_name,
    suggest_pydantic_type,
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
        from src.core.analyzer.improvement_templates import _is_excluded_variable_name

        issues: list[QualityIssue] = []

        # CodeLocatorで詳細情報を取得
        primitive_details = self.code_locator.find_primitive_usages()

        for detail in primitive_details:
            # 変数名を抽出して除外パターンチェック
            var_name = extract_variable_name(detail.location.code)
            is_excluded = _is_excluded_variable_name(var_name)

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

            # 除外パターンの場合はアドバイスとして扱う
            if is_excluded:
                issue_type = "primitive_usage_excluded"
                prim_msg = (
                    f"primitive型 {detail.primitive_type} "
                    "が使用されています（汎用変数名）"
                )
                suggestion = "現状維持を推奨（汎用的な変数名のため型定義不要）"
                recommended_type = None
            else:
                issue_type = "primitive_usage"
                prim_msg = f"primitive型 {detail.primitive_type} が直接使用されています"
                suggestion = "ドメイン型を定義して使用してください"
                # 推奨型を取得
                pydantic_type = suggest_pydantic_type(var_name, detail.primitive_type)
                recommended_type = pydantic_type["type"] if pydantic_type else "custom"

            issues.append(
                QualityIssue(
                    issue_type=issue_type,
                    message=prim_msg,
                    location=location,
                    suggestion=suggestion,
                    improvement_plan=self._generate_primitive_replacement_plan(detail),
                    recommended_type=recommended_type,
                    primitive_type=detail.primitive_type,
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
            "primitive_usage": 0.7,  # 警告レベル（0.6以上）
            "primitive_usage_excluded": 0.85,  # アドバイスレベル（0.8以上）
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
        from src.core.analyzer.improvement_templates import _is_excluded_variable_name

        # 変数名を抽出
        var_name = extract_variable_name(detail.location.code)

        # 除外パターンチェック（汎用的な変数名は型定義不要）
        if _is_excluded_variable_name(var_name):
            return f"""primitive型 {detail.primitive_type} の直接使用は問題ありません。

変数名 '{var_name}' は汎用的な変数名のため、ドメイン型定義は不要です。
このような一般的な変数名にはprimitive型をそのまま使用することが推奨されます。

理由:
  - フレームワーク変数やユーティリティパラメータなど、特定のドメイン概念を表さない
  - 型定義によるオーバーエンジニアリングを避ける
  - 型の意図は変数名とコンテキストから十分に明確

推奨アクション: 現状維持（変更不要）
"""

        # Pydantic提供の型を優先的に推奨
        pydantic_type = suggest_pydantic_type(var_name, detail.primitive_type)

        if pydantic_type:
            # Pydantic型が見つかった場合
            fixed_code = detail.location.code.replace(
                f": {detail.primitive_type}", f": {pydantic_type['type']}"
            ).strip()

            plan = f"""primitive型 {detail.primitive_type} をPydantic型に置き換える手順:

推奨: Pydantic提供の型を使用（最もシンプル）

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
            # 機械的に判定できない場合: プロジェクトの型定義を活用するよう促す
            plan = f"""primitive型 {detail.primitive_type} の使用が検出されました。

変数名 '{var_name}' から適切な型を自動推奨できませんでした。
プロジェクトで定義された型を活用することを検討してください。

推奨アクション:
  1. プロジェクトの既存型定義を確認
     - src/core/schemas/types.py に適切な型が定義されているか確認
     - 同様の用途の変数で使われている型を参照

  2. 新規型定義が必要な場合
     - この変数が表すドメイン概念を明確化
     - Level 2（Annotated + バリデーション）での定義を推奨
     - docs/typing-rule.md の型定義ルールに従う

  3. primitive型のままで良い場合
     - 汎用的な値で特定のドメイン概念を表さない場合
     - 一時変数やユーティリティパラメータの場合

参考:
  - 型定義ルール: docs/typing-rule.md
  - 既存の型定義: src/core/schemas/types.py
  - 位置: {detail.location.file}:{detail.location.line}

注記: 将来的には、より精度の高い型推奨機能を提供予定です。
"""
        return plan
