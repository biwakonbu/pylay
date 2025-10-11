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
        target_dirs = config.target_dirs or ["src"]
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
        issues.extend(self._check_primitive_usage_issues())

        # 非推奨typing使用の問題をチェック
        issues.extend(self._check_deprecated_typing_issues(report))

        # エラー条件をチェック
        issues.extend(self._check_error_conditions(report.statistics))

        # 深刻度レベルを計算して設定
        for issue in issues:
            issue.severity = self._calculate_severity(issue, report.statistics)

        # 優先度スコアを計算
        for issue in issues:
            issue.priority_score = self._calculate_priority_score(issue)
            issue.impact_score = self._calculate_impact_score(issue, report)
            issue.difficulty_score = self._estimate_difficulty(issue)

        # 優先度順にソート（優先度高→影響大→難易度低の順）
        issues = self._prioritize_issues(issues)

        # 全体統計を計算
        error_count = sum(1 for issue in issues if issue.severity == "error")
        warning_count = sum(1 for issue in issues if issue.severity == "warning")
        advice_count = sum(1 for issue in issues if issue.severity == "advice")

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

    def _check_type_level_issues(self, statistics: TypeStatistics) -> list[QualityIssue]:
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

    def _check_documentation_issues(self, statistics: TypeStatistics) -> list[QualityIssue]:
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

    def _check_primitive_usage_issues(self) -> list[QualityIssue]:
        """primitive型使用の問題をチェック（位置情報付き）"""
        from src.core.analyzer.improvement_templates import _is_excluded_variable_name

        issues: list[QualityIssue] = []

        # CodeLocatorで詳細情報を取得
        primitive_details = self.code_locator.find_primitive_usages()

        for detail in primitive_details:
            # 変数名を抽出して除外パターンチェック
            var_name = extract_variable_name(detail.location.code) or "value"
            is_excluded = _is_excluded_variable_name(var_name)

            # 位置情報を含むQualityIssueを作成
            location = CodeLocation(
                file=detail.location.file,
                line=detail.location.line,
                column=getattr(detail.location, "column", 0),
                context_before=detail.location.context_before if hasattr(detail.location, "context_before") else [],
                code=detail.location.code,
                context_after=detail.location.context_after if hasattr(detail.location, "context_after") else [],
            )

            # 除外パターンの場合はアドバイスとして扱う
            if is_excluded:
                issue_type = "primitive_usage_excluded"
                prim_msg = f"primitive型 {detail.primitive_type} が使用されています（汎用変数名）"
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

    def _check_deprecated_typing_issues(self, report: TypeAnalysisReport) -> list[QualityIssue]:
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
                    improvement_plan="typing.Union → X | Y, typing.List → list[X] に置き換えてください",
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

        Note:
            セキュリティのためサンドボックス環境で評価します。
            TODO: 将来的にはASTベースのセーフ評価器に置き換える
                 （BoolOp/Compare/UnaryOp/Name/Constantのみ許可）
        """
        try:
            # 評価に使用する変数を明示的に辞書で定義
            env = {
                "level1_ratio": statistics.level1_ratio,
                "level2_ratio": statistics.level2_ratio,
                "level3_ratio": statistics.level3_ratio,
                "primitive_usage_ratio": statistics.primitive_usage_ratio,
                "deprecated_typing_ratio": statistics.deprecated_typing_ratio,
                "documentation": statistics.documentation,
                "documentation_rate": statistics.documentation.implementation_rate,
                "detail_rate": statistics.documentation.detail_rate,
                "implementation_rate": statistics.documentation.implementation_rate,
            }

            # サンドボックス環境で条件式を評価
            # __builtins__を空にすることで危険な組み込み関数へのアクセスを防ぐ
            compiled = compile(condition, "<quality_condition>", "eval")
            result = eval(compiled, {"__builtins__": {}}, env)
            return bool(result)

        except Exception:
            # 評価エラーの場合はFalseを返す
            return False

    def _calculate_severity(
        self, issue: QualityIssue, statistics: TypeStatistics
    ) -> Literal["advice", "warning", "error"]:
        """問題の深刻度レベルを計算

        設定ファイルのしきい値（デフォルト: error:0.0, warning:0.6, advice:0.8）は
        「base_scoreがこの値以上なら該当レベル」を意味します。

        スコアの意味:
            - 低いスコア（0.0〜0.6未満）: 深刻（error）
            - 中程度のスコア（0.6〜0.8未満）: 警告（warning）
            - 高いスコア（0.8以上）: アドバイス（advice）

        修正後のロジック: 降順走査（advice → warning → error）し、
        base_score >= threshold を満たす最初のレベルを返します。

        例:
            - base_score=0.0 → error(0.0) にマッチ → error
            - base_score=0.7 → warning(0.6) にマッチ → warning
            - base_score=0.85 → advice(0.8) にマッチ → advice
        """
        # ベーススコアを計算（問題の種類によって重み付け）
        base_score = self._calculate_base_score(issue.issue_type, statistics)

        # 降順（しきい値が高い順: advice → warning → error）で走査
        for level in sorted(self.severity_levels, key=lambda x: x.threshold, reverse=True):
            name = level.name
            if name in ("advice", "warning", "error"):
                if base_score >= level.threshold:
                    return name  # type: ignore[return-value]

        # デフォルトはアドバイス（すべてのしきい値を満たさない場合）
        return "advice"

    def _calculate_base_score(self, issue_type: str, statistics: TypeStatistics) -> float:
        """問題のベーススコアを計算（0.0〜1.0）

        スコアの意味:
            - 低いスコア（0.0〜0.6未満）: 深刻（error）
            - 中程度のスコア（0.6〜0.8未満）: 警告（warning）
            - 高いスコア（0.8以上）: アドバイス（advice）
        """
        base_scores = {
            "level1_ratio_high": 0.3,  # error
            "level2_ratio_low": 0.4,  # error
            "level3_ratio_low": 0.5,  # error
            "documentation_low": 0.6,  # warning（境界値）
            "documentation_detail_low": 0.7,  # warning
            "primitive_usage": 0.7,  # warning
            "primitive_usage_excluded": 0.85,  # advice
            "primitive_usage_high": 0.8,  # advice（境界値）
            "deprecated_typing_usage": 0.9,  # advice
            "custom_error_condition": 0.0,  # error（最も深刻）
        }

        base_score = base_scores.get(issue_type, 0.5)

        # 実際の比率に基づいてスコアを調整
        if "ratio" in issue_type:
            if "high" in issue_type:
                # 高い比率ほど高いスコア（悪い状態）
                if "level1" in issue_type:
                    ratio_diff = max(0, statistics.level1_ratio - self.thresholds.level1_max)
                    base_score += ratio_diff * 2.0
                elif "primitive" in issue_type:
                    ratio_diff = max(0, statistics.primitive_usage_ratio - 0.10)
                    base_score += ratio_diff * 3.0
            elif "low" in issue_type:
                # 低い比率ほど高いスコア（悪い状態）
                if "level2" in issue_type:
                    ratio_diff = max(0, self.thresholds.level2_min - statistics.level2_ratio)
                    base_score += ratio_diff * 2.0
                elif "level3" in issue_type:
                    ratio_diff = max(0, self.thresholds.level3_min - statistics.level3_ratio)
                    base_score += ratio_diff * 2.0

        return min(1.0, base_score)

    def _get_improvement_plan(self, guidance_level: str) -> str:
        """改善プランのガイダンスを取得"""
        for guidance in self.improvement_guidance:
            if guidance.level == guidance_level:
                return guidance.suggestion

        # デフォルトの改善プラン
        return "適切な型定義パターンを使用して改善してください"

    def _generate_primitive_replacement_plan(self, detail: "PrimitiveUsageDetail") -> str:
        """primitive型置き換えの詳細プランを生成

        Args:
            detail: PrimitiveUsageDetail

        Returns:
            フォーマット済みの改善プラン
        """
        from src.core.analyzer.improvement_templates import (
            _is_excluded_variable_name,
            generate_detailed_improvement_plan,
        )

        # 変数名を抽出
        var_name = extract_variable_name(detail.location.code) or "value"

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

  {pydantic_type["import"]}

  説明: {pydantic_type["description"]}
  例: {pydantic_type["example"]}

Step 2: 使用箇所を修正

  File: {detail.location.file}:{detail.location.line}

  # Before
  {detail.location.code.strip()}

  # After
  {pydantic_type["import"]}
  {fixed_code}

利点:
  - 自動バリデーション（Pydanticが提供）
  - 追加のコード不要
  - 標準的な型定義パターン
  - ドキュメント自動生成対応

参考: https://docs.pydantic.dev/latest/api/types/
"""
        else:
            # カスタム型の場合: 詳細な改善プランを生成
            plan = generate_detailed_improvement_plan(
                var_name=var_name,
                primitive_type=detail.primitive_type,
                file_path=str(detail.location.file),
                line_number=detail.location.line,
                code_line=detail.location.code,
            )

        return plan

    def _calculate_priority_score(self, issue: QualityIssue) -> int:
        """問題の優先度スコアを計算（低いほど優先度高）

        Args:
            issue: 品質問題

        Returns:
            優先度スコア（0=最高優先度、10=最低優先度）
        """
        # 深刻度による基本スコア
        severity_score = {"error": 0, "warning": 3, "advice": 6}[issue.severity]

        # 問題タイプによる調整
        type_penalty = 0
        if issue.issue_type in ("primitive_usage", "level2_ratio_low"):
            # 型安全性に直結する問題は優先度高
            type_penalty = -1
        elif issue.issue_type in ("documentation_low", "documentation_detail_low"):
            # ドキュメント問題は優先度低
            type_penalty = 2

        return severity_score + type_penalty

    def _calculate_impact_score(self, issue: QualityIssue, report: TypeAnalysisReport) -> int:
        """問題の影響度を計算（高いほど影響大）

        Args:
            issue: 品質問題
            report: 型定義分析レポート

        Returns:
            影響度スコア（1=影響小、10=影響大）
        """
        # primitive型使用の場合、使用箇所の数で影響度を判定
        if issue.issue_type == "primitive_usage" and issue.primitive_type:
            # primitive使用率から推測
            usage_ratio = report.statistics.primitive_usage_ratio
            if usage_ratio > 0.2:  # 20%以上
                return 10
            elif usage_ratio > 0.1:  # 10%以上
                return 7
            elif usage_ratio > 0.05:  # 5%以上
                return 5
            else:
                return 3

        # Level比率の問題は全体に影響
        if "ratio" in issue.issue_type:
            return 8

        # その他の問題
        return 5

    def _estimate_difficulty(self, issue: QualityIssue) -> int:
        """修正難易度を推定（低いほど簡単）

        Args:
            issue: 品質問題

        Returns:
            難易度スコア（1=簡単、10=難しい）
        """
        # primitive型使用で推奨型がある場合は簡単
        if issue.issue_type == "primitive_usage" and issue.recommended_type:
            # Pydantic型推奨がある場合は非常に簡単
            if issue.recommended_type != "custom":
                return 2
            # カスタム型が必要な場合は少し難しい
            return 5

        # Level比率の問題は複数箇所の修正が必要で難しい
        if "ratio" in issue.issue_type:
            return 8

        # ドキュメント問題は比較的簡単
        if "documentation" in issue.issue_type:
            return 3

        # その他の問題
        return 5

    def _prioritize_issues(self, issues: list[QualityIssue]) -> list[QualityIssue]:
        """問題に優先度を付けてソート

        Args:
            issues: 問題リスト

        Returns:
            ソート済み問題リスト（優先度高→影響大→難易度低の順）
        """

        def sort_key(issue: QualityIssue) -> tuple[int, int, int]:
            return (
                issue.priority_score,  # 優先度（低いほど優先）
                -issue.impact_score,  # 影響度（高いほど優先）
                issue.difficulty_score,  # 難易度（低いほど優先）
            )

        return sorted(issues, key=sort_key)

    def generate_fix_checklist(self, issue: QualityIssue) -> str:
        """修正完了チェックリストを生成

        Args:
            issue: 品質問題

        Returns:
            チェックリスト（マークダウン形式）
        """
        checklist_items = []

        if issue.issue_type == "primitive_usage" and issue.location:
            # primitive型使用の場合
            var_name = extract_variable_name(issue.location.code) or "value"
            type_name = (
                issue.recommended_type
                if issue.recommended_type and issue.recommended_type != "custom"
                else f"{var_name.capitalize()}Type"
            )

            checklist_items = [
                f"[ ] 1. src/core/schemas/types.py に {type_name} を定義",
                f"[ ] 2. {issue.location.file}:{issue.location.line} のコードを修正",
                "[ ] 3. インポート文を追加",
                "[ ] 4. バリデーション関数を実装（必要な場合）",
                "[ ] 5. テストを実行して型エラーがないことを確認",
            ]
        elif "level1_ratio" in issue.issue_type or "level2_ratio" in issue.issue_type:
            # Level比率の問題の場合
            checklist_items = [
                "[ ] 1. Level 1型を特定（制約が必要か検討）",
                "[ ] 2. バリデーション関数を定義",
                "[ ] 3. Level 2（Annotated）に昇格",
                "[ ] 4. 全ての使用箇所を確認",
                "[ ] 5. テストを実行して動作確認",
            ]
        elif "documentation" in issue.issue_type:
            # ドキュメント問題の場合
            checklist_items = [
                "[ ] 1. 未ドキュメント型をリストアップ",
                "[ ] 2. 各型にdocstringを追加",
                "[ ] 3. 型の目的と使用例を記述",
                "[ ] 4. ドキュメントカバレッジを再確認",
            ]
        else:
            # その他の問題の場合
            checklist_items = [
                "[ ] 1. 問題箇所を特定",
                "[ ] 2. 改善プランに従って修正",
                "[ ] 3. テストを実行",
                "[ ] 4. 品質チェックを再実行",
            ]

        return "\n".join(checklist_items)
