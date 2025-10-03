"""
型定義分析レポート生成

コンソール、Markdown、JSON形式でレポートを生成します。
"""

import json

from src.core.analyzer.type_level_models import (
    DocstringRecommendation,
    DocumentationStatistics,
    TypeAnalysisReport,
    TypeStatistics,
    UpgradeRecommendation,
)


class TypeReporter:
    """型定義分析レポートを生成するクラス"""

    def __init__(self, threshold_ratios: dict[str, float] | None = None):
        """初期化

        Args:
            threshold_ratios: 警告閾値（デフォルト: 推奨閾値）
        """
        self.threshold_ratios = threshold_ratios or {
            "level1_max": 0.20,  # Level 1は20%以下が望ましい
            "level2_min": 0.40,  # Level 2は40%以上が望ましい
            "level3_min": 0.15,  # Level 3は15%以上が望ましい
        }

    def generate_console_report(self, report: TypeAnalysisReport) -> str:
        """コンソール用レポートを生成

        Args:
            report: 型定義分析レポート

        Returns:
            コンソール出力文字列
        """
        lines = []

        # ヘッダー
        lines.append("=== 型定義レベル分析レポート ===\n")

        # 統計情報
        lines.append("📊 統計情報:")
        lines.append(self._format_statistics_table(report.statistics))

        # 警告閾値との比較
        lines.append("\n🎯 警告閾値との比較:")
        lines.append(self._format_deviation_comparison(report))

        # ドキュメント品質スコア
        lines.append("\n📝 ドキュメント品質スコア:")
        lines.append(
            self._format_documentation_quality(report.statistics.documentation)
        )

        # 推奨事項
        if report.recommendations:
            lines.append("\n💡 推奨事項:")
            for rec in report.recommendations:
                lines.append(f"  - {rec}")

        return "\n".join(lines)

    def generate_upgrade_recommendations_report(
        self, recommendations: list[UpgradeRecommendation]
    ) -> str:
        """型レベルアップ推奨レポートを生成

        Args:
            recommendations: 型レベルアップ推奨リスト

        Returns:
            レポート文字列
        """
        if not recommendations:
            return "\n=== 型レベルアップ推奨レポート ===\n\n推奨事項はありません。"

        lines = []
        lines.append("\n=== 型レベルアップ推奨レポート ===\n")

        # 優先度別にグループ化
        high_priority = [r for r in recommendations if r.priority == "high"]
        medium_priority = [r for r in recommendations if r.priority == "medium"]
        low_priority = [r for r in recommendations if r.priority == "low"]

        if high_priority:
            lines.append("🔼 高優先度の推奨事項:\n")
            for rec in high_priority:
                lines.append(self._format_upgrade_recommendation(rec))

        if medium_priority:
            lines.append("\n🔼 中優先度の推奨事項:\n")
            for rec in medium_priority:
                lines.append(self._format_upgrade_recommendation(rec))

        if low_priority:
            lines.append("\n🔼 低優先度の推奨事項:\n")
            for rec in low_priority:
                lines.append(self._format_upgrade_recommendation(rec))

        return "\n".join(lines)

    def generate_docstring_recommendations_report(
        self, recommendations: list[DocstringRecommendation]
    ) -> str:
        """docstring改善推奨レポートを生成

        Args:
            recommendations: docstring改善推奨リスト

        Returns:
            レポート文字列
        """
        if not recommendations:
            return "\n=== ドキュメント改善推奨レポート ===\n\n推奨事項はありません。"

        lines = []
        lines.append("\n=== ドキュメント改善推奨レポート ===\n")

        # ステータス別にグループ化
        missing = [r for r in recommendations if r.current_status == "missing"]
        minimal = [r for r in recommendations if r.current_status == "minimal"]
        partial = [r for r in recommendations if r.current_status == "partial"]

        if missing:
            lines.append(f"📝 docstring未実装（{len(missing)}件）\n")
            for rec in missing[:5]:  # 最初の5件のみ表示
                lines.append(self._format_docstring_recommendation(rec))

        if minimal:
            lines.append(f"\n📄 docstring詳細度不足（{len(minimal)}件）\n")
            for rec in minimal[:5]:  # 最初の5件のみ表示
                lines.append(self._format_docstring_recommendation(rec))

        if partial:
            lines.append(f"\n🔄 docstring部分的（{len(partial)}件）\n")
            for rec in partial[:3]:  # 最初の3件のみ表示
                lines.append(self._format_docstring_recommendation(rec))

        return "\n".join(lines)

    def generate_markdown_report(self, report: TypeAnalysisReport) -> str:
        """Markdown形式のレポートを生成

        Args:
            report: 型定義分析レポート

        Returns:
            Markdown文字列
        """
        lines = []

        # ヘッダー
        lines.append("# 型定義レベル分析レポート\n")

        # 統計情報
        lines.append("## 📊 統計情報\n")
        lines.append(self._format_statistics_markdown(report.statistics))

        # ドキュメント品質
        lines.append("\n## 📝 ドキュメント品質\n")
        lines.append(
            self._format_documentation_quality_markdown(report.statistics.documentation)
        )

        # 推奨事項
        if report.recommendations:
            lines.append("\n## 💡 推奨事項\n")
            for rec in report.recommendations:
                lines.append(f"- {rec}")

        # 型レベルアップ推奨
        if report.upgrade_recommendations:
            lines.append("\n## 🔼 型レベルアップ推奨\n")
            lines.append(
                self._format_upgrade_recommendations_markdown(
                    report.upgrade_recommendations
                )
            )

        # docstring改善推奨
        if report.docstring_recommendations:
            lines.append("\n## 📝 ドキュメント改善推奨\n")
            lines.append(
                self._format_docstring_recommendations_markdown(
                    report.docstring_recommendations
                )
            )

        return "\n".join(lines)

    def generate_json_report(self, report: TypeAnalysisReport) -> str:
        """JSON形式のレポートを生成

        Args:
            report: 型定義分析レポート

        Returns:
            JSON文字列
        """
        return json.dumps(report.model_dump(), indent=2, ensure_ascii=False)

    # ========================================
    # フォーマットヘルパー
    # ========================================

    def _format_statistics_table(self, statistics: "TypeStatistics") -> str:
        """統計情報をテーブル形式でフォーマット"""
        lines = []
        lines.append("┌─────────────────────────┬───────┬─────────┐")
        lines.append("│ レベル                  │ 件数  │ 比率    │")
        lines.append("├─────────────────────────┼───────┼─────────┤")
        lines.append(
            f"│ Level 1: type エイリアス │ {statistics.level1_count:5} │ {statistics.level1_ratio * 100:6.1f}% │"  # noqa: E501
        )
        lines.append(
            f"│ Level 2: Annotated      │ {statistics.level2_count:5} │ {statistics.level2_ratio * 100:6.1f}% │"  # noqa: E501
        )
        lines.append(
            f"│ Level 3: BaseModel      │ {statistics.level3_count:5} │ {statistics.level3_ratio * 100:6.1f}% │"  # noqa: E501
        )
        lines.append(
            f"│ その他: class/dataclass │ {statistics.other_count:5} │ {statistics.other_ratio * 100:6.1f}% │"  # noqa: E501
        )
        lines.append("├─────────────────────────┼───────┼─────────┤")
        lines.append(
            f"│ 合計                    │ {statistics.total_count:5} │ 100.0%  │"
        )
        lines.append("└─────────────────────────┴───────┴─────────┘")
        return "\n".join(lines)

    def _format_deviation_comparison(self, report: TypeAnalysisReport) -> str:
        """警告閾値との乖離を比較形式でフォーマット"""
        lines = []
        stats = report.statistics

        # Level 1の比較（上限チェック）
        l1_max_dev = report.deviation_from_threshold.get("level1_max", 0.0)
        l1_status = "✅" if l1_max_dev <= 0 else "⚠️"  # 負 or 0 = OK、正 = 警告
        lines.append(
            f"  Level 1: {stats.level1_ratio * 100:.1f}% "
            f"(上限: {self.threshold_ratios['level1_max'] * 100:.0f}%, "
            f"差分: {l1_max_dev * 100:+.1f}%) {l1_status}"
        )

        # Level 2の比較（下限チェック）
        l2_min_dev = report.deviation_from_threshold.get("level2_min", 0.0)
        l2_status = "✅" if l2_min_dev >= 0 else "⚠️"  # 正 or 0 = OK、負 = 警告
        lines.append(
            f"  Level 2: {stats.level2_ratio * 100:.1f}% "
            f"(下限: {self.threshold_ratios['level2_min'] * 100:.0f}%, "
            f"差分: {l2_min_dev * 100:+.1f}%) {l2_status}"
        )

        # Level 3の比較（下限チェック）
        l3_min_dev = report.deviation_from_threshold.get("level3_min", 0.0)
        l3_status = "✅" if l3_min_dev >= 0 else "⚠️"  # 正 or 0 = OK、負 = 警告
        lines.append(
            f"  Level 3: {stats.level3_ratio * 100:.1f}% "
            f"(下限: {self.threshold_ratios['level3_min'] * 100:.0f}%, "
            f"差分: {l3_min_dev * 100:+.1f}%) {l3_status}"
        )

        return "\n".join(lines)

    def _format_documentation_quality(
        self, doc_stats: "DocumentationStatistics"
    ) -> str:
        """ドキュメント品質をフォーマット"""
        lines = []
        lines.append("┌─────────────────────────┬───────┬─────────┐")
        lines.append("│ 指標                    │ 値    │ 評価    │")
        lines.append("├─────────────────────────┼───────┼─────────┤")

        # 実装率
        impl_status = "✅" if doc_stats.implementation_rate >= 0.8 else "⚠️"
        lines.append(
            f"│ 実装率                  │ {doc_stats.implementation_rate * 100:5.1f}% │   {impl_status}    │"  # noqa: E501
        )

        # 詳細度
        detail_status = "✅" if doc_stats.detail_rate >= 0.5 else "⚠️"
        lines.append(
            f"│ 詳細度                  │ {doc_stats.detail_rate * 100:5.1f}% │   {detail_status}    │"  # noqa: E501
        )

        # 総合品質スコア
        quality_status = (
            "✅"
            if doc_stats.quality_score >= 0.4
            else "⚠️"
            if doc_stats.quality_score >= 0.2
            else "❌"
        )
        lines.append(
            f"│ 総合品質スコア          │ {doc_stats.quality_score * 100:5.1f}% │   {quality_status}    │"  # noqa: E501
        )

        lines.append("└─────────────────────────┴───────┴─────────┘")
        return "\n".join(lines)

    def _format_upgrade_recommendation(self, rec: UpgradeRecommendation) -> str:
        """型レベルアップ推奨をフォーマット"""
        lines = []
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        emoji = priority_emoji.get(rec.priority, "⚪")

        # 調査推奨の場合は異なる表示
        if rec.recommended_level == "investigate":
            lines.append(f"❓ [{rec.priority.upper()}] {rec.type_name} (被参照: 0)")
            lines.append("  推奨アクション: 調査")
        else:
            lines.append(
                f"{emoji} [{rec.priority.upper()}] {rec.type_name} (確信度: {rec.confidence:.2f})"  # noqa: E501
            )
            lines.append(f"  現在: {rec.current_level} → 推奨: {rec.recommended_level}")

        if rec.reasons:
            if rec.recommended_level == "investigate":
                for reason in rec.reasons:
                    lines.append(f"  {reason}")
            else:
                lines.append("  理由:")
                for reason in rec.reasons:
                    lines.append(f"    - {reason}")

        if rec.suggested_validator:
            lines.append("  推奨バリデータ:")
            for line in rec.suggested_validator.splitlines():
                lines.append(f"    {line}")

        lines.append("")  # 空行
        return "\n".join(lines)

    def _format_docstring_recommendation(self, rec: DocstringRecommendation) -> str:
        """docstring改善推奨をフォーマット"""
        lines = []
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        emoji = priority_emoji.get(rec.priority, "⚪")

        lines.append(
            f"{emoji} [{rec.priority.upper()}] {rec.type_name} "
            f"({rec.file_path}:{rec.line_number})"
        )
        lines.append(f"  現状: {rec.current_status}")
        lines.append(f"  推奨: {rec.recommended_action}")

        if rec.reasons:
            for reason in rec.reasons:
                lines.append(f"  - {reason}")

        if rec.detail_gaps:
            lines.append(f"  不足セクション: {', '.join(rec.detail_gaps)}")

        if rec.suggested_template:
            lines.append("  推奨テンプレート:")
            for line in rec.suggested_template.splitlines()[:5]:  # 最初の5行のみ
                lines.append(f"    {line}")

        lines.append("")  # 空行
        return "\n".join(lines)

    def _format_statistics_markdown(self, statistics: "TypeStatistics") -> str:
        """統計情報をMarkdown形式でフォーマット"""
        lines = []
        lines.append("| レベル | 件数 | 比率 |")
        lines.append("|--------|------|------|")
        lines.append(
            f"| Level 1: type エイリアス | {statistics.level1_count} | {statistics.level1_ratio * 100:.1f}% |"  # noqa: E501
        )
        lines.append(
            f"| Level 2: Annotated | {statistics.level2_count} | {statistics.level2_ratio * 100:.1f}% |"  # noqa: E501
        )
        lines.append(
            f"| Level 3: BaseModel | {statistics.level3_count} | {statistics.level3_ratio * 100:.1f}% |"  # noqa: E501
        )
        lines.append(
            f"| その他 | {statistics.other_count} | {statistics.other_ratio * 100:.1f}% |"  # noqa: E501
        )
        lines.append(f"| **合計** | **{statistics.total_count}** | **100.0%** |")
        return "\n".join(lines)

    def _format_documentation_quality_markdown(
        self, doc_stats: "DocumentationStatistics"
    ) -> str:
        """ドキュメント品質をMarkdown形式でフォーマット"""
        lines = []
        lines.append("| 指標 | 値 |")
        lines.append("|------|------|")
        lines.append(f"| 実装率 | {doc_stats.implementation_rate * 100:.1f}% |")
        lines.append(f"| 詳細度 | {doc_stats.detail_rate * 100:.1f}% |")
        lines.append(f"| 総合品質スコア | {doc_stats.quality_score * 100:.1f}% |")
        return "\n".join(lines)

    def _format_upgrade_recommendations_markdown(
        self, recommendations: list[UpgradeRecommendation]
    ) -> str:
        """型レベルアップ推奨をMarkdown形式でフォーマット"""
        lines = []
        for rec in recommendations[:10]:  # 最初の10件のみ
            lines.append(
                f"### {rec.type_name} ({rec.priority.upper()}, 確信度: {rec.confidence:.2f})"  # noqa: E501
            )
            lines.append(
                f"- 現在: `{rec.current_level}` → 推奨: `{rec.recommended_level}`"
            )
            if rec.reasons:
                lines.append("- 理由:")
                for reason in rec.reasons:
                    lines.append(f"  - {reason}")
            lines.append("")
        return "\n".join(lines)

    def _format_docstring_recommendations_markdown(
        self, recommendations: list[DocstringRecommendation]
    ) -> str:
        """docstring改善推奨をMarkdown形式でフォーマット"""
        lines = []
        for rec in recommendations[:10]:  # 最初の10件のみ
            lines.append(f"### {rec.type_name} ({rec.priority.upper()})")
            lines.append(f"- ファイル: `{rec.file_path}:{rec.line_number}`")
            lines.append(f"- 現状: {rec.current_status}")
            lines.append(f"- 推奨: {rec.recommended_action}")
            if rec.detail_gaps:
                lines.append(f"- 不足セクション: {', '.join(rec.detail_gaps)}")
            lines.append("")
        return "\n".join(lines)
