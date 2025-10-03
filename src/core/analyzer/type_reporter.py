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

    def __init__(self, target_ratios: dict[str, float] | None = None):
        """初期化

        Args:
            target_ratios: 目標比率（デフォルト: 標準的な比率）
        """
        self.target_ratios = target_ratios or {
            "level1": 0.55,  # 50-60%の中央値
            "level2": 0.30,  # 25-35%の中央値
            "level3": 0.175,  # 15-20%の中央値
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

        # 理想比率との比較
        lines.append("\n🎯 理想比率との比較:")
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
            f"│ Level 1: type エイリアス │ {statistics.level1_count:5} │ {statistics.level1_ratio*100:6.1f}% │"
        )
        lines.append(
            f"│ Level 2: Annotated      │ {statistics.level2_count:5} │ {statistics.level2_ratio*100:6.1f}% │"
        )
        lines.append(
            f"│ Level 3: BaseModel      │ {statistics.level3_count:5} │ {statistics.level3_ratio*100:6.1f}% │"
        )
        lines.append(
            f"│ その他: class/dataclass │ {statistics.other_count:5} │ {statistics.other_ratio*100:6.1f}% │"
        )
        lines.append("├─────────────────────────┼───────┼─────────┤")
        lines.append(
            f"│ 合計                    │ {statistics.total_count:5} │ 100.0%  │"
        )
        lines.append("└─────────────────────────┴───────┴─────────┘")
        return "\n".join(lines)

    def _format_deviation_comparison(self, report: TypeAnalysisReport) -> str:
        """目標比率との乖離を比較形式でフォーマット"""
        lines = []
        stats = report.statistics

        # Level 1の比較
        l1_dev = report.deviation_from_target.get("level1", 0.0)
        l1_status = "✅" if abs(l1_dev) < 0.1 else "⚠️"
        lines.append(
            f"  Level 1: {stats.level1_ratio*100:.1f}% "
            f"(目標: {self.target_ratios['level1']*100:.0f}%, "
            f"差分: {l1_dev*100:+.1f}%) {l1_status}"
        )

        # Level 2の比較
        l2_dev = report.deviation_from_target.get("level2", 0.0)
        l2_status = "✅" if abs(l2_dev) < 0.1 else "⚠️"
        lines.append(
            f"  Level 2: {stats.level2_ratio*100:.1f}% "
            f"(目標: {self.target_ratios['level2']*100:.0f}%, "
            f"差分: {l2_dev*100:+.1f}%) {l2_status}"
        )

        # Level 3の比較
        l3_dev = report.deviation_from_target.get("level3", 0.0)
        l3_status = "✅" if abs(l3_dev) < 0.05 else "⚠️"
        lines.append(
            f"  Level 3: {stats.level3_ratio*100:.1f}% "
            f"(目標: {self.target_ratios['level3']*100:.0f}%, "
            f"差分: {l3_dev*100:+.1f}%) {l3_status}"
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
            f"│ 実装率                  │ {doc_stats.implementation_rate*100:5.1f}% │   {impl_status}    │"
        )

        # 詳細度
        detail_status = "✅" if doc_stats.detail_rate >= 0.5 else "⚠️"
        lines.append(
            f"│ 詳細度                  │ {doc_stats.detail_rate*100:5.1f}% │   {detail_status}    │"
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
            f"│ 総合品質スコア          │ {doc_stats.quality_score*100:5.1f}% │   {quality_status}    │"
        )

        lines.append("└─────────────────────────┴───────┴─────────┘")
        return "\n".join(lines)

    def _format_upgrade_recommendation(self, rec: UpgradeRecommendation) -> str:
        """型レベルアップ推奨をフォーマット"""
        lines = []
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        emoji = priority_emoji.get(rec.priority, "⚪")

        lines.append(
            f"{emoji} [{rec.priority.upper()}] {rec.type_name} (確信度: {rec.confidence:.2f})"
        )
        lines.append(f"  現在: {rec.current_level} → 推奨: {rec.recommended_level}")

        if rec.reasons:
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
            f"| Level 1: type エイリアス | {statistics.level1_count} | {statistics.level1_ratio*100:.1f}% |"
        )
        lines.append(
            f"| Level 2: Annotated | {statistics.level2_count} | {statistics.level2_ratio*100:.1f}% |"
        )
        lines.append(
            f"| Level 3: BaseModel | {statistics.level3_count} | {statistics.level3_ratio*100:.1f}% |"
        )
        lines.append(
            f"| その他 | {statistics.other_count} | {statistics.other_ratio*100:.1f}% |"
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
        lines.append(f"| 実装率 | {doc_stats.implementation_rate*100:.1f}% |")
        lines.append(f"| 詳細度 | {doc_stats.detail_rate*100:.1f}% |")
        lines.append(f"| 総合品質スコア | {doc_stats.quality_score*100:.1f}% |")
        return "\n".join(lines)

    def _format_upgrade_recommendations_markdown(
        self, recommendations: list[UpgradeRecommendation]
    ) -> str:
        """型レベルアップ推奨をMarkdown形式でフォーマット"""
        lines = []
        for rec in recommendations[:10]:  # 最初の10件のみ
            lines.append(
                f"### {rec.type_name} ({rec.priority.upper()}, 確信度: {rec.confidence:.2f})"
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
