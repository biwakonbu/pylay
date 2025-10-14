"""
型定義分析レポート生成

コンソール、Markdown、JSON形式でレポートを生成します。
Richライブラリを使用して、美しいCLI出力を実現します。
"""

from __future__ import annotations

import json
from pathlib import Path

from rich.box import SIMPLE
from rich.console import Console
from rich.table import Table
from rich.text import Text

from src.core.analyzer.code_locator import (
    CodeLocator,
    DeprecatedTypingDetail,
    Level1TypeDetail,
    PrimitiveUsageDetail,
    UnusedTypeDetail,
)
from src.core.analyzer.quality_models import QualityCheckResult
from src.core.analyzer.type_level_models import (
    DocstringRecommendation,
    DocumentationStatistics,
    TypeAnalysisReport,
    TypeStatistics,
    UpgradeRecommendation,
)


class TypeReporter:
    """型定義分析レポートを生成するクラス（Richベース）"""

    def __init__(
        self,
        threshold_ratios: dict[str, float] | None = None,
        target_dirs: list[str] | None = None,
    ):
        """初期化

        Args:
            threshold_ratios: 警告閾値（デフォルト: 推奨閾値）
                - level1_max: Level 1の上限
                - level2_min: Level 2の下限
                - level3_min: Level 3の下限
                - implementation_rate: ドキュメント実装率の下限
                - detail_rate: ドキュメント詳細度の下限
                - quality_score: ドキュメント総合品質スコアの下限
            target_dirs: 解析対象ディレクトリ（詳細レポート生成時に使用）

        Note:
            上記以外のキーが含まれている場合は無視されます。
            これは前方互換性を保つための仕様です。
        """
        base_type_thresholds = {
            "level1_max": 0.20,  # Level 1は20%以下が望ましい
            "level2_min": 0.40,  # Level 2は40%以上が望ましい
            "level3_min": 0.15,  # Level 3は15%以上が望ましい
        }
        base_doc_thresholds = {
            "implementation_rate": 0.8,  # 実装率は80%以上が望ましい
            "detail_rate": 0.5,  # 詳細度は50%以上が望ましい
            "quality_score": 0.6,  # 総合品質スコアは60%以上が望ましい
        }
        provided = threshold_ratios or {}
        self.threshold_ratios = base_type_thresholds | {
            key: provided[key] for key in base_type_thresholds if key in provided
        }
        self.doc_thresholds = base_doc_thresholds | {
            key: provided[key] for key in base_doc_thresholds if key in provided
        }
        self.console = Console()
        self.target_dirs = [Path(d) for d in (target_dirs or ["."])]
        self.code_locator = CodeLocator(self.target_dirs)

    def generate_console_report(self, report: TypeAnalysisReport, show_stats: bool = True) -> None:
        """コンソール用レポートを生成して直接表示

        Args:
            report: 型定義分析レポート

        Note:
            Pydanticモデルで必須フィールドが保証されているが、
            防御的プログラミングとして空データのチェックを実施
        """
        # ヘッダー
        self.console.rule("[bold cyan]型定義レベル分析レポート[/bold cyan]")
        self.console.print()

        # 統計情報（オプションで表示制御）
        if show_stats and report.statistics:
            self.console.print(self._create_statistics_table(report.statistics))
            self.console.print()

            # 警告閾値との比較
            self.console.rule("[bold yellow]警告閾値との比較[/bold yellow]")
            self.console.print()
            self._print_deviation_comparison(report)
            self.console.print()

            # ドキュメント品質スコア
            if report.statistics.documentation:
                self.console.rule("[bold green]ドキュメント品質スコア[/bold green]")
                self.console.print()
                self.console.print(self._create_documentation_quality_table(report.statistics.documentation))
                self.console.print()

            # コード品質統計
            self.console.rule("[bold magenta]コード品質統計[/bold magenta]")
            self.console.print()
            self.console.print(self._create_code_quality_table(report.statistics))
            self.console.print()

        # 推奨事項（空リストの場合はスキップ）
        if report.recommendations:
            self.console.rule("[bold red]推奨事項[/bold red]")
            self.console.print()
            self.console.print(self._create_recommendations_table(report.recommendations))
            self.console.print()

    def generate_upgrade_recommendations_report(self, recommendations: list[UpgradeRecommendation]) -> str:
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

    def generate_docstring_recommendations_report(self, recommendations: list[DocstringRecommendation]) -> str:
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

    def generate_console_report_with_quality_check(
        self,
        quality_check_result: QualityCheckResult,
        report: TypeAnalysisReport,
        show_details: bool = False,
    ) -> None:
        """品質チェック結果を含むコンソールレポートを生成

        Args:
            quality_check_result: 品質チェック結果
            report: 型定義分析レポート
            show_details: 詳細情報を表示するか
        """
        # QualityReporterに委譲して品質チェック結果を表示
        from src.core.analyzer.quality_reporter import QualityReporter

        reporter = QualityReporter(target_dirs=[str(path) for path in self.target_dirs])
        reporter.generate_console_report(quality_check_result, report, show_details)

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
        lines.append(self._format_documentation_quality_markdown(report.statistics.documentation))

        # コード品質統計
        lines.append("\n## ⚠️  コード品質統計\n")
        lines.append(self._format_code_quality_statistics_markdown(report.statistics))

        # 推奨事項
        if report.recommendations:
            lines.append("\n## 💡 推奨事項\n")
            for rec in report.recommendations:
                lines.append(f"- {rec}")

        # 型レベルアップ推奨
        if report.upgrade_recommendations:
            lines.append("\n## 🔼 型レベルアップ推奨\n")
            lines.append(self._format_upgrade_recommendations_markdown(report.upgrade_recommendations))

        # docstring改善推奨
        if report.docstring_recommendations:
            lines.append("\n## 📝 ドキュメント改善推奨\n")
            lines.append(self._format_docstring_recommendations_markdown(report.docstring_recommendations))

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
    # Richベースのフォーマットヘルパー
    # ========================================

    def _create_statistics_table(self, statistics: TypeStatistics) -> Table:
        """統計情報をRich Tableで作成"""
        table = Table(
            title="Type Definition Level Statistics",
            show_header=True,
            width=80,
            header_style="",
            box=SIMPLE,
        )

        table.add_column("Level", style="cyan", no_wrap=True, width=30)
        table.add_column("Count", justify="right", style="green", width=10)
        table.add_column("Ratio", justify="right", width=10)
        table.add_column("Status", justify="center", width=10)

        # Level 1
        level1_limit = self.threshold_ratios["level1_max"]
        level1_status = "✓" if statistics.level1_ratio <= level1_limit else "✗"
        level1_style = "green" if statistics.level1_ratio <= level1_limit else "red"
        table.add_row(
            "Level 1: type エイリアス",
            str(statistics.level1_count),
            f"{statistics.level1_ratio * 100:.1f}%",
            Text(level1_status, style=level1_style),
        )

        # Level 2
        level2_limit = self.threshold_ratios["level2_min"]
        level2_status = "✓" if statistics.level2_ratio >= level2_limit else "✗"
        level2_style = "green" if statistics.level2_ratio >= level2_limit else "red"
        table.add_row(
            "Level 2: Annotated",
            str(statistics.level2_count),
            f"{statistics.level2_ratio * 100:.1f}%",
            Text(level2_status, style=level2_style),
        )

        # Level 3
        level3_limit = self.threshold_ratios["level3_min"]
        level3_status = "✓" if statistics.level3_ratio >= level3_limit else "✗"
        level3_style = "green" if statistics.level3_ratio >= level3_limit else "red"
        table.add_row(
            "Level 3: BaseModel",
            str(statistics.level3_count),
            f"{statistics.level3_ratio * 100:.1f}%",
            Text(level3_status, style=level3_style),
        )

        # その他
        table.add_row(
            "その他: class/dataclass",
            str(statistics.other_count),
            f"{statistics.other_ratio * 100:.1f}%",
            "-",
            style="dim",
        )

        # 合計
        table.add_section()
        table.add_row(
            "合計",
            str(statistics.total_count),
            "100.0%",
            "",
        )

        return table

    def _print_deviation_comparison(self, report: TypeAnalysisReport) -> None:
        """警告閾値との比較を表示"""
        stats = report.statistics

        table = Table(show_header=True, width=80, header_style="", box=SIMPLE)

        table.add_column("Level", style="cyan", no_wrap=True, width=15)
        table.add_column("Current", justify="right", width=10)
        table.add_column("Threshold", justify="right", width=15)
        table.add_column("Deviation", justify="right", width=15)
        table.add_column("Status", justify="center", width=10)

        # Level 1
        l1_max_dev = report.deviation_from_threshold.get("level1_max", 0.0)
        l1_status = "✓" if l1_max_dev <= 0 else "✗"
        l1_style = "green" if l1_max_dev <= 0 else "red"
        table.add_row(
            "Level 1",
            f"{stats.level1_ratio * 100:.1f}%",
            f"上限 {self.threshold_ratios['level1_max'] * 100:.0f}%",
            f"{l1_max_dev * 100:+.1f}%",
            Text(l1_status, style=l1_style),
        )

        # Level 2
        l2_min_dev = report.deviation_from_threshold.get("level2_min", 0.0)
        l2_status = "✓" if l2_min_dev >= 0 else "✗"
        l2_style = "green" if l2_min_dev >= 0 else "red"
        table.add_row(
            "Level 2",
            f"{stats.level2_ratio * 100:.1f}%",
            f"下限 {self.threshold_ratios['level2_min'] * 100:.0f}%",
            f"{l2_min_dev * 100:+.1f}%",
            Text(l2_status, style=l2_style),
        )

        # Level 3
        l3_min_dev = report.deviation_from_threshold.get("level3_min", 0.0)
        l3_status = "✓" if l3_min_dev >= 0 else "✗"
        l3_style = "green" if l3_min_dev >= 0 else "red"
        table.add_row(
            "Level 3",
            f"{stats.level3_ratio * 100:.1f}%",
            f"下限 {self.threshold_ratios['level3_min'] * 100:.0f}%",
            f"{l3_min_dev * 100:+.1f}%",
            Text(l3_status, style=l3_style),
        )

        self.console.print(table)

    def _create_documentation_quality_table(self, doc_stats: DocumentationStatistics) -> Table:
        """ドキュメント品質をRich Tableで作成"""
        table = Table(show_header=True, width=80, header_style="", box=SIMPLE)

        table.add_column("Metric", style="cyan", no_wrap=True, width=30)
        table.add_column("Value", justify="right", style="green", width=20)
        table.add_column("Status", justify="center", width=10)

        # 実装率
        impl_threshold = self.doc_thresholds["implementation_rate"]
        impl_status = "✓" if doc_stats.implementation_rate >= impl_threshold else "✗"
        impl_style = "green" if doc_stats.implementation_rate >= impl_threshold else "red"
        table.add_row(
            "実装率",
            f"{doc_stats.implementation_rate * 100:.1f}%",
            Text(impl_status, style=impl_style),
        )

        # 詳細度
        detail_threshold = self.doc_thresholds["detail_rate"]
        detail_status = "✓" if doc_stats.detail_rate >= detail_threshold else "✗"
        detail_style = "green" if doc_stats.detail_rate >= detail_threshold else "red"
        table.add_row(
            "詳細度",
            f"{doc_stats.detail_rate * 100:.1f}%",
            Text(detail_status, style=detail_style),
        )

        # 総合品質スコア
        quality_threshold = self.doc_thresholds["quality_score"]
        quality_status = "✓" if doc_stats.quality_score >= quality_threshold else "✗"
        quality_style = "green" if doc_stats.quality_score >= quality_threshold else "red"
        table.add_row(
            "総合品質スコア",
            f"{doc_stats.quality_score * 100:.1f}%",
            Text(quality_status, style=quality_style),
        )

        return table

    def _create_code_quality_table(self, statistics: TypeStatistics) -> Table:
        """コード品質統計をRich Tableで作成"""
        table = Table(show_header=True, width=80, header_style="", box=SIMPLE)

        table.add_column("Level", style="cyan", no_wrap=True, width=30)
        table.add_column("Count", justify="right", style="green", width=10)
        table.add_column("Ratio", justify="right", width=10)
        table.add_column("Status", justify="center", width=10)

        # Level 0: 非推奨typing使用
        dep_status = "✓" if statistics.deprecated_typing_ratio == 0.0 else "✗"
        dep_style = "green" if statistics.deprecated_typing_ratio == 0.0 else "red"
        table.add_row(
            "Level 0: 非推奨typing",
            str(statistics.deprecated_typing_count),
            f"{statistics.deprecated_typing_ratio * 100:.1f}%",
            Text(dep_status, style=dep_style),
        )

        # Level 1: type エイリアス
        level1_limit = self.threshold_ratios["level1_max"]
        level1_status = "✓" if statistics.level1_ratio <= level1_limit else "✗"
        level1_style = "green" if statistics.level1_ratio <= level1_limit else "red"
        table.add_row(
            "Level 1: type エイリアス",
            str(statistics.level1_count),
            f"{statistics.level1_ratio * 100:.1f}%",
            Text(level1_status, style=level1_style),
        )

        # Level 1の内訳: primitive型の直接使用
        table.add_row(
            "  └─ primitive型直接使用",
            str(statistics.primitive_usage_count),
            f"{statistics.primitive_usage_ratio * 100:.1f}%",
            "-",
            style="dim",
        )

        return table

    def _create_recommendations_table(self, recommendations: list[str]) -> Table:
        """推奨事項をRich Tableで作成"""
        table = Table(show_header=True, header_style="", box=SIMPLE, width=100)

        table.add_column("Priority", style="cyan", no_wrap=True, width=12)
        table.add_column("Recommendation", no_wrap=False, width=85)

        for rec in recommendations:
            # 優先度を判定（警告マークがあるかで判断）
            if "⚠️" in rec:
                priority = "HIGH"
                priority_style = "red"
                # ⚠️を削除
                rec = rec.replace("⚠️", "").strip()
            else:
                priority = "MEDIUM"
                priority_style = "yellow"

            # 長い文章を整形（句点で分割してインデント）
            formatted_rec = self._format_recommendation_text(rec)

            table.add_row(
                Text(priority, style=priority_style),
                formatted_rec,
            )

        return table

    def _format_recommendation_text(self, text: str) -> str:
        """推奨事項のテキストを見やすく整形

        長い文章を句点で分割し、インデントを付けて整形する

        Args:
            text: 整形対象のテキスト

        Returns:
            整形済みのテキスト（複数文の場合は改行とインデント付き）
        """
        # 「。」で文を分割（空文字列を除外）
        sentences = [s.strip() for s in text.split("。") if s.strip()]

        # 単一文または空の場合
        if not sentences:
            return text
        if len(sentences) == 1:
            return text if text.endswith("。") else text + "。"

        # 複数文の場合は整形
        result = []
        for i, sentence in enumerate(sentences):
            if i == 0:
                # 最初の文はそのまま
                result.append(sentence + "。")
            else:
                # 2文目以降は矢印でインデント
                arrow = "→ " if i == 1 else "  "
                result.append(arrow + sentence + "。")

        return "\n".join(result)

    # ========================================
    # 旧フォーマットヘルパー（後方互換性のため保持）
    # ========================================

    def _format_statistics_table(self, statistics: TypeStatistics) -> str:
        """統計情報をテーブル形式でフォーマット"""
        lines = []
        lines.append("┌─────────────────────────┬───────┬─────────┐")
        lines.append("│ レベル                  │ 件数  │ 比率    │")
        lines.append("├─────────────────────────┼───────┼─────────┤")
        lines.append(
            f"│ Level 1: type エイリアス │ {statistics.level1_count:5} │ {statistics.level1_ratio * 100:6.1f}% │"
        )
        lines.append(
            f"│ Level 2: Annotated      │ {statistics.level2_count:5} │ {statistics.level2_ratio * 100:6.1f}% │"
        )
        lines.append(
            f"│ Level 3: BaseModel      │ {statistics.level3_count:5} │ {statistics.level3_ratio * 100:6.1f}% │"
        )
        lines.append(f"│ その他: class/dataclass │ {statistics.other_count:5} │ {statistics.other_ratio * 100:6.1f}% │")
        lines.append("├─────────────────────────┼───────┼─────────┤")
        lines.append(f"│ 合計                    │ {statistics.total_count:5} │ 100.0%  │")
        lines.append("└─────────────────────────┴───────┴─────────┘")
        return "\n".join(lines)

    def _format_code_quality_statistics(self, statistics: TypeStatistics) -> str:
        """コード品質統計をフォーマット"""
        lines = []
        lines.append("┌─────────────────────────────────┬───────┬─────────┬──────┐")
        lines.append("│ レベル                          │ 件数  │ 比率    │ 状態 │")
        lines.append("├─────────────────────────────────┼───────┼─────────┼──────┤")

        # Level 0: 非推奨typing使用（0%必須）
        dep_status = "✅" if statistics.deprecated_typing_ratio == 0.0 else "⚠️"
        lines.append(
            f"│ Level 0: 非推奨typing           │ {statistics.deprecated_typing_count:5} │ {statistics.deprecated_typing_ratio * 100:6.1f}% │ {dep_status}  │"
        )

        # Level 1: type エイリアス（20%以下推奨、primitive型含む）
        level1_limit = self.threshold_ratios["level1_max"]
        level1_status = "✅" if statistics.level1_ratio <= level1_limit else "⚠️"
        lines.append(
            f"│ Level 1: type エイリアス        │ {statistics.level1_count:5} │ {statistics.level1_ratio * 100:6.1f}% │ {level1_status}  │"
        )

        # Level 1の内訳: primitive型の直接使用
        lines.append(
            f"│   └─ primitive型直接使用        │ {statistics.primitive_usage_count:5} │ {statistics.primitive_usage_ratio * 100:6.1f}% │      │"
        )

        lines.append("└─────────────────────────────────┴───────┴─────────┴──────┘")
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

    def _format_documentation_quality(self, doc_stats: DocumentationStatistics) -> str:
        """ドキュメント品質をフォーマット"""
        lines = []
        lines.append("┌─────────────────────────┬───────┬─────────┐")
        lines.append("│ 指標                    │ 値    │ 評価    │")
        lines.append("├─────────────────────────┼───────┼─────────┤")

        # 実装率
        impl_threshold = self.doc_thresholds["implementation_rate"]
        impl_status = "✅" if doc_stats.implementation_rate >= impl_threshold else "⚠️"
        lines.append(f"│ 実装率                  │ {doc_stats.implementation_rate * 100:5.1f}% │   {impl_status}    │")

        # 詳細度
        detail_threshold = self.doc_thresholds["detail_rate"]
        detail_status = "✅" if doc_stats.detail_rate >= detail_threshold else "⚠️"
        lines.append(f"│ 詳細度                  │ {doc_stats.detail_rate * 100:5.1f}% │   {detail_status}    │")

        # 総合品質スコア
        quality_threshold = self.doc_thresholds["quality_score"]
        quality_status = (
            "✅"
            if doc_stats.quality_score >= quality_threshold
            else "⚠️"
            if doc_stats.quality_score >= quality_threshold * 0.5
            else "❌"
        )
        lines.append(f"│ 総合品質スコア          │ {doc_stats.quality_score * 100:5.1f}% │   {quality_status}    │")

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
            lines.append(f"{emoji} [{rec.priority.upper()}] {rec.type_name} (確信度: {rec.confidence:.2f})")
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

        lines.append(f"{emoji} [{rec.priority.upper()}] {rec.type_name} ({rec.file_path}:{rec.line_number})")
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

    def _format_statistics_markdown(self, statistics: TypeStatistics) -> str:
        """統計情報をMarkdown形式でフォーマット"""
        lines = []
        lines.append("| レベル | 件数 | 比率 |")
        lines.append("|--------|------|------|")
        lines.append(f"| Level 1: type エイリアス | {statistics.level1_count} | {statistics.level1_ratio * 100:.1f}% |")
        lines.append(f"| Level 2: Annotated | {statistics.level2_count} | {statistics.level2_ratio * 100:.1f}% |")
        lines.append(f"| Level 3: BaseModel | {statistics.level3_count} | {statistics.level3_ratio * 100:.1f}% |")
        lines.append(f"| その他 | {statistics.other_count} | {statistics.other_ratio * 100:.1f}% |")
        lines.append(f"| **合計** | **{statistics.total_count}** | **100.0%** |")
        return "\n".join(lines)

    def _format_documentation_quality_markdown(self, doc_stats: DocumentationStatistics) -> str:
        """ドキュメント品質をMarkdown形式でフォーマット"""
        lines = []
        lines.append("| 指標 | 値 |")
        lines.append("|------|------|")
        lines.append(f"| 実装率 | {doc_stats.implementation_rate * 100:.1f}% |")
        lines.append(f"| 詳細度 | {doc_stats.detail_rate * 100:.1f}% |")
        lines.append(f"| 総合品質スコア | {doc_stats.quality_score * 100:.1f}% |")
        return "\n".join(lines)

    def _format_code_quality_statistics_markdown(self, statistics: TypeStatistics) -> str:
        """コード品質統計をMarkdown形式でフォーマット"""
        lines = []
        lines.append("| レベル | 件数 | 比率 | 状態 |")
        lines.append("|--------|------|------|------|")

        # Level 0: 非推奨typing使用（0%必須）
        dep_status = "✅" if statistics.deprecated_typing_ratio == 0.0 else "⚠️"
        lines.append(
            f"| Level 0: 非推奨typing | {statistics.deprecated_typing_count} | "
            f"{statistics.deprecated_typing_ratio * 100:.1f}% | {dep_status} |"
        )

        # Level 1: type エイリアス（20%以下推奨、primitive型含む）
        level1_limit = self.threshold_ratios["level1_max"]
        level1_status = "✅" if statistics.level1_ratio <= level1_limit else "⚠️"
        lines.append(
            f"| Level 1: type エイリアス | {statistics.level1_count} | "
            f"{statistics.level1_ratio * 100:.1f}% | {level1_status} |"
        )

        # Level 1の内訳: primitive型の直接使用
        lines.append(
            f"| └─ primitive型直接使用 | {statistics.primitive_usage_count} | "
            f"{statistics.primitive_usage_ratio * 100:.1f}% | - |"
        )

        return "\n".join(lines)

    def _format_upgrade_recommendations_markdown(self, recommendations: list[UpgradeRecommendation]) -> str:
        """型レベルアップ推奨をMarkdown形式でフォーマット"""
        lines = []
        for rec in recommendations[:10]:  # 最初の10件のみ
            lines.append(f"### {rec.type_name} ({rec.priority.upper()}, 確信度: {rec.confidence:.2f})")
            lines.append(f"- 現在: `{rec.current_level}` → 推奨: `{rec.recommended_level}`")
            if rec.reasons:
                lines.append("- 理由:")
                for reason in rec.reasons:
                    lines.append(f"  - {reason}")
            lines.append("")
        return "\n".join(lines)

    def generate_detailed_report(
        self,
        report: TypeAnalysisReport,
        show_details: bool = False,
        show_stats: bool = True,
    ) -> None:
        """詳細レポートをコンソールに出力

        Args:
            report: 型分析レポート
            show_details: 詳細情報を表示するかどうか
        """
        if not show_details:
            # 通常のレポートのみ出力
            self.generate_console_report(report, show_stats)
            return

        # 基本レポート
        self.generate_console_report(report, show_stats)

        # 詳細情報の収集
        primitive_details = self.code_locator.find_primitive_usages()
        level1_details = self.code_locator.find_level1_types(list(report.type_definitions))
        unused_details = self.code_locator.find_unused_types(list(report.type_definitions))
        deprecated_details = self.code_locator.find_deprecated_typing()

        # 詳細レポートの出力
        if primitive_details:
            self.console.print()
            self.console.rule("[bold red]🔍 問題詳細: Primitive型の直接使用[/bold red]")
            self.console.print()
            self.console.print(self._create_primitive_usage_table(primitive_details))

        if level1_details:
            self.console.print()
            self.console.rule("[bold yellow]🔍 問題詳細: Level 1型の放置[/bold yellow]")
            self.console.print()
            self.console.print(self._create_level1_types_table(level1_details))

        if unused_details:
            self.console.print()
            self.console.rule("[bold magenta]🔍 問題詳細: 被参照0の型定義[/bold magenta]")
            self.console.print()
            self.console.print(self._create_unused_types_table(unused_details))

        if deprecated_details:
            self.console.print()
            self.console.rule("[bold cyan]🔍 問題詳細: 非推奨typing使用[/bold cyan]")
            self.console.print()
            self.console.print(self._create_deprecated_typing_table(deprecated_details))

    def _create_primitive_usage_table(self, details: list[PrimitiveUsageDetail]) -> Table:
        """Primitive型使用の詳細テーブルを生成"""
        table = Table(
            title="Direct Primitive Type Usage",
            show_header=True,
            width=120,
            header_style="",
            box=SIMPLE,
        )

        table.add_column("File", style="cyan", no_wrap=True, width=25)
        table.add_column("Line", justify="right", style="green", width=5)
        table.add_column("Kind", justify="center", width=12)
        table.add_column("Type", justify="center", width=8)
        table.add_column("Code", no_wrap=False, width=65)

        for detail in details[:50]:  # 最大50件まで表示
            # ファイル名を短く表示
            file_name = detail.location.file.name
            if len(file_name) > 24:
                file_name = "..." + file_name[-21:]

            # コードを整形
            code = detail.location.code.strip()
            if len(code) > 60:
                code = code[:57] + "..."

            table.add_row(
                file_name,
                str(detail.location.line),
                detail.kind.replace("function_", "").replace("return_", "戻り値").replace("class_", ""),
                detail.primitive_type,
                code,
                style="red" if detail.kind == "function_argument" else "yellow",
            )

        return table

    def _create_level1_types_table(self, details: list[Level1TypeDetail]) -> Table:
        """Level 1型の詳細テーブルを生成"""
        table = Table(
            title="Unused Level 1 Types",
            show_header=True,
            width=120,
            header_style="",
            box=SIMPLE,
        )

        table.add_column("Type Definition", style="cyan", no_wrap=True, width=25)
        table.add_column("File", style="blue", no_wrap=True, width=20)
        table.add_column("Line", justify="right", style="green", width=5)
        table.add_column("Usage Count", justify="right", width=8)
        table.add_column("Recommendation", no_wrap=False, width=60)

        for detail in details[:30]:  # 最大30件まで表示
            # 型名を短く表示
            type_name = detail.type_name
            if len(type_name) > 24:
                type_name = type_name[:21] + "..."

            # ファイル名を短く表示
            file_name = detail.location.file.name
            if len(file_name) > 19:
                file_name = "..." + file_name[-16:]

            # 推奨事項を短く表示
            recommendation = detail.recommendation
            if len(recommendation) > 55:
                recommendation = recommendation[:52] + "..."

            table.add_row(
                type_name,
                file_name,
                str(detail.location.line),
                str(detail.usage_count),
                recommendation,
                style="yellow",
            )

        return table

    def _create_unused_types_table(self, details: list[UnusedTypeDetail]) -> Table:
        """被参照0型の詳細テーブルを生成"""
        table = Table(
            title="Unused Type Definitions",
            show_header=True,
            width=120,
            header_style="",
            box=SIMPLE,
        )

        table.add_column("Type Definition", style="cyan", no_wrap=True, width=25)
        table.add_column("File", style="blue", no_wrap=True, width=20)
        table.add_column("Line", justify="right", style="green", width=5)
        table.add_column("Level", justify="center", width=8)
        table.add_column("Recommendation", no_wrap=False, width=60)

        for detail in details[:30]:  # 最大30件まで表示
            # 型名を短く表示
            type_name = detail.type_name
            if len(type_name) > 24:
                type_name = type_name[:21] + "..."

            # ファイル名を短く表示
            file_name = detail.location.file.name
            if len(file_name) > 19:
                file_name = "..." + file_name[-16:]

            # 推奨事項を短く表示
            recommendation = detail.recommendation
            if len(recommendation) > 55:
                recommendation = recommendation[:52] + "..."

            table.add_row(
                type_name,
                file_name,
                str(detail.location.line),
                detail.level,
                recommendation,
                style="magenta",
            )

        return table

    def _create_deprecated_typing_table(self, details: list[DeprecatedTypingDetail]) -> Table:
        """非推奨typing使用の詳細テーブルを生成"""
        table = Table(
            title="Deprecated typing Usage",
            show_header=True,
            width=120,
            header_style="",
            box=SIMPLE,
        )

        table.add_column("File", style="cyan", no_wrap=True, width=25)
        table.add_column("Line", justify="right", style="green", width=5)
        table.add_column("Deprecated Type", justify="center", width=15)
        table.add_column("Recommended Alternative", justify="center", width=15)
        table.add_column("Code", no_wrap=False, width=60)

        for detail in details[:30]:  # 最大30件まで表示
            # ファイル名を短く表示
            file_name = detail.location.file.name
            if len(file_name) > 24:
                file_name = "..." + file_name[-21:]

            # コードを整形
            code = detail.location.code.strip()
            if len(code) > 55:
                code = code[:52] + "..."

            # import情報をまとめて表示
            deprecated_types = [imp["deprecated"] for imp in detail.imports]
            recommended_types = [imp["recommended"] for imp in detail.imports]

            dep_str = ", ".join(deprecated_types)
            rec_str = ", ".join(recommended_types)

            table.add_row(
                file_name,
                str(detail.location.line),
                dep_str,
                rec_str,
                code,
                style="cyan",
            )

        return table

    def _format_docstring_recommendations_markdown(self, recommendations: list[DocstringRecommendation]) -> str:
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
