"""
品質チェックレポート生成機能

コンソール形式で品質チェックレポートを生成します。
"""

from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from src.core.analyzer.quality_models import QualityCheckResult, QualityIssue

if TYPE_CHECKING:
    from src.core.analyzer.type_level_models import TypeAnalysisReport

# 深刻度の型付き定数（Literal型との互換性を確保）
SEVERITIES: Final[tuple[Literal["error", "warning", "advice"], ...]] = (
    "error",
    "warning",
    "advice",
)


class QualityReporter:
    """品質チェックレポートを生成するクラス"""

    def __init__(self, target_dirs: list[str] | None = None):
        """初期化

        Args:
            target_dirs: 解析対象ディレクトリ（詳細レポート生成時に使用）
        """
        self.console = Console()
        self.target_dirs = [Path(d) for d in (target_dirs or ["."])]

    def generate_console_report(
        self,
        check_result: QualityCheckResult,
        _report: "TypeAnalysisReport",
        show_details: bool = False,
    ) -> None:
        """コンソール用レポートを生成して直接表示

        Args:
            check_result: 品質チェック結果
            _report: 型定義分析レポート（現在未使用、将来の拡張用）
            show_details: 詳細情報を表示するか
        """
        # ヘッダー
        self.console.rule("[bold cyan]Type Definition Quality Report[/bold cyan]")
        self.console.print()

        # 全体サマリー
        self._show_summary_panel(check_result)

        # 統計情報テーブル
        self._show_statistics_table(check_result)

        # 問題リスト
        if check_result.issues:
            self._show_issues_table(check_result, show_details)
        else:
            self.console.print("[green]No quality issues detected[/green]")

        # 推奨事項（問題がある場合のみ）
        if check_result.issues:
            self._show_recommendations(check_result)

    def _show_summary_panel(self, check_result: QualityCheckResult) -> None:
        """サマリーパネルを表示"""
        score_color = (
            "red"
            if check_result.overall_score < 0.6
            else "yellow"
            if check_result.overall_score < 0.8
            else "green"
        )
        score_text = (  # noqa: E501
            f"[bold {score_color}]{check_result.overall_score:.2f}/1.0"
            f"[/bold {score_color}]"
        )

        summary_content = (
            f"[bold cyan]Overall Score:[/bold cyan] {score_text}\n"
            f"[bold cyan]Total Issues:[/bold cyan] {check_result.total_issues}\n"
            f"[bold red]Errors:[/bold red] {check_result.error_count}\n"
            f"[bold yellow]Warnings:[/bold yellow] {check_result.warning_count}\n"
            f"[bold blue]Advice:[/bold blue] {check_result.advice_count}"
        )

        summary_panel = Panel(
            summary_content,
            title="[bold]Summary[/bold]",
            border_style=score_color,
        )
        self.console.print(summary_panel)
        self.console.print()

    def _show_statistics_table(self, check_result: QualityCheckResult) -> None:
        """統計情報テーブルを表示"""
        table = Table(title="Statistics", show_header=True, header_style="bold magenta")
        table.add_column("Item", style="cyan", width=30)
        table.add_column("Value", style="white", justify="right")
        table.add_column("Status", style="green")

        # 型レベル統計
        level1_color = (
            "red"
            if check_result.statistics.level1_ratio > check_result.thresholds.level1_max
            else "green"
        )
        l1_status = (  # noqa: E501
            "Exceeded"
            if check_result.statistics.level1_ratio > check_result.thresholds.level1_max
            else "OK"
        )
        table.add_row(
            "Level 1 Ratio",
            f"{check_result.statistics.level1_ratio * 100:.1f}%",
            f"[bold {level1_color}]{l1_status}[/bold {level1_color}]",
        )

        level2_color = (
            "red"
            if check_result.statistics.level2_ratio < check_result.thresholds.level2_min
            else "green"
        )
        l2_status = (  # noqa: E501
            "Low"
            if check_result.statistics.level2_ratio < check_result.thresholds.level2_min
            else "OK"
        )
        table.add_row(
            "Level 2 Ratio",
            f"{check_result.statistics.level2_ratio * 100:.1f}%",
            f"[bold {level2_color}]{l2_status}[/bold {level2_color}]",
        )

        level3_color = (
            "red"
            if check_result.statistics.level3_ratio < check_result.thresholds.level3_min
            else "green"
        )
        l3_status = (  # noqa: E501
            "Low"
            if check_result.statistics.level3_ratio < check_result.thresholds.level3_min
            else "OK"
        )
        table.add_row(
            "Level 3 Ratio",
            f"{check_result.statistics.level3_ratio * 100:.1f}%",
            f"[bold {level3_color}]{l3_status}[/bold {level3_color}]",
        )

        # ドキュメント統計
        doc_rate = check_result.statistics.documentation.implementation_rate
        doc_color = "yellow" if doc_rate < 0.8 else "green"
        doc_status = "Needs Improvement" if doc_rate < 0.8 else "Good"
        table.add_row(
            "Documentation Rate",
            f"{doc_rate * 100:.1f}%",
            f"[bold {doc_color}]{doc_status}[/bold {doc_color}]",
        )

        # その他の統計
        prim_ratio = check_result.statistics.primitive_usage_ratio
        primitive_color = "red" if prim_ratio > 0.10 else "green"
        prim_status = "High" if prim_ratio > 0.10 else "OK"
        table.add_row(
            "Primitive Usage Ratio",
            f"{prim_ratio * 100:.1f}%",
            f"[bold {primitive_color}]{prim_status}[/bold {primitive_color}]",
        )

        self.console.print(table)
        self.console.print()

    def _show_issues_table(
        self, check_result: QualityCheckResult, show_details: bool
    ) -> None:
        """問題リストテーブルを表示"""
        # 深刻度別にテーブルを作成
        for severity in SEVERITIES:
            severity_issues = check_result.get_issues_by_severity(severity)
            if not severity_issues:
                continue

            # 深刻度別の色設定
            color = {"error": "red", "warning": "yellow", "advice": "blue"}[severity]
            severity_label = {
                "error": "ERROR",
                "warning": "WARNING",
                "advice": "ADVICE",
            }[severity]

            rule_text = (  # noqa: E501
                f"[bold {color}]{severity_label} ({len(severity_issues)} issues)"
                f"[/bold {color}]"
            )
            self.console.rule(rule_text, style=color)
            self.console.print()

            # primitive_usage関連の問題をグルーピング表示
            primitive_issues = [
                i
                for i in severity_issues
                if i.issue_type in ("primitive_usage", "primitive_usage_excluded")
            ]
            other_issues = [
                i
                for i in severity_issues
                if i.issue_type not in ("primitive_usage", "primitive_usage_excluded")
            ]

            # primitive型問題をグルーピング表示
            if primitive_issues:
                self._show_grouped_primitive_issues(
                    primitive_issues, show_details, color
                )

            # その他の問題は個別表示
            for issue in other_issues:
                self._show_issue_detail(issue, show_details, color)

            self.console.print()

    def _show_grouped_primitive_issues(
        self, issues: list[QualityIssue], show_details: bool, color: str
    ) -> None:
        """primitive型問題をグルーピング表示"""
        from collections import defaultdict

        # 推奨型ごとにグルーピング
        grouped: dict[str, list[QualityIssue]] = defaultdict(list)
        for issue in issues:
            key = issue.recommended_type or "excluded"
            grouped[key].append(issue)

        # Pydantic型推奨グループ
        pydantic_groups = {
            k: v for k, v in grouped.items() if k not in ("custom", "excluded")
        }
        if pydantic_groups:
            self.console.print(
                f"[bold {color}]Pydantic型で置き換え可能 "
                f"({sum(len(v) for v in pydantic_groups.values())}件)[/bold {color}]"
            )
            for rec_type, type_issues in sorted(pydantic_groups.items()):
                self.console.print(f"  {rec_type}推奨: {len(type_issues)}箇所")
                if show_details:
                    for issue in type_issues[:3]:  # 最大3件表示
                        loc = issue.location
                        if loc:
                            self.console.print(
                                f"    [dim]Location:[/dim] {loc.file}:{loc.line}"
                            )
                            # コードコンテキストを表示
                            if loc.code:
                                self._print_code_context(issue)
                                self.console.print()
                    if len(type_issues) > 3:
                        self.console.print(f"    ... 他{len(type_issues) - 3}件")
            self.console.print()

        # カスタム型定義が必要なグループ
        if "custom" in grouped:
            custom_issues = grouped["custom"]
            self.console.print(
                f"[bold {color}]プロジェクト型定義の検討が必要 "
                f"({len(custom_issues)}件)[/bold {color}]"
            )
            if show_details:
                for issue in custom_issues[:5]:  # 最大5件表示
                    loc = issue.location
                    if loc:
                        self.console.print(
                            f"  [dim]Location:[/dim] {loc.file}:{loc.line}"
                        )
                        # コードコンテキストを表示
                        if loc.code:
                            self._print_code_context(issue)
                            self.console.print()
                if len(custom_issues) > 5:
                    self.console.print(f"  ... 他{len(custom_issues) - 5}件")
            self.console.print()

        # 除外グループ（汎用変数名）
        if "excluded" in grouped:
            excluded_issues = grouped["excluded"]
            self.console.print(
                f"[bold {color}]汎用変数名（型定義不要） "
                f"({len(excluded_issues)}件)[/bold {color}]"
            )
            if show_details:
                # primitive型ごとにカウント
                type_counts: dict[str, int] = defaultdict(int)
                for issue in excluded_issues:
                    if issue.primitive_type:
                        type_counts[issue.primitive_type] += 1
                for prim_type, count in sorted(type_counts.items()):
                    self.console.print(f"  {prim_type}: {count}箇所")
            self.console.print()

    def _show_issue_detail(
        self, issue: QualityIssue, show_details: bool, color: str
    ) -> None:
        """個別の問題を詳細表示"""
        # 問題の種類とメッセージ
        self.console.print(
            f"[bold {color}]Issue Type:[/bold {color}] {issue.issue_type}"
        )
        self.console.print(f"[bold]Message:[/bold] {issue.message}")
        self.console.print(f"[bold]Suggestion:[/bold] {issue.suggestion}")
        self.console.print()

        # 詳細表示が有効で、位置情報がある場合
        if show_details and issue.location:
            # 位置情報
            self.console.print(
                f"[dim]Location: {issue.location.file}:{issue.location.line}[/dim]"
            )
            self.console.print()

            # コードコンテキスト表示
            if issue.location.code:
                self._print_code_context(issue)
                self.console.print()

        # 改善プラン
        if issue.improvement_plan and show_details:
            self.console.print("[bold]Improvement Plan:[/bold]")
            self.console.print(issue.improvement_plan)
            self.console.print()

        self.console.rule(style="dim")

    def _print_code_context(self, issue: QualityIssue) -> None:
        """コードコンテキストをシンタックスハイライト付きで表示"""
        if not issue.location:
            return

        location = issue.location

        # 開始行番号を計算
        context_before_count = len(location.context_before)
        start_line = location.line - context_before_count

        # コード全体を構築
        code_lines = location.context_before + [location.code] + location.context_after
        code = "\n".join(code_lines)

        # Syntax highlight
        syntax = Syntax(
            code,
            "python",
            theme="monokai",
            line_numbers=True,
            start_line=start_line,
            highlight_lines={location.line},
        )

        self.console.print("  [bold]Code Context:[/bold]")
        self.console.print("  ", syntax)

    def _show_recommendations(self, check_result: QualityCheckResult) -> None:
        """推奨事項を表示"""
        self.console.print("[bold cyan]Recommendations[/bold cyan]")
        self.console.print()

        if check_result.error_count > 0:
            self.console.print(
                "1. [bold red]Fix error items with highest priority[/bold red]"
            )
            self.console.print("   - エラーは型定義の品質に深刻な影響を及ぼします")
            self.console.print(
                "   - CI/CDでエラーが発生した場合、ビルドが失敗する可能性があります"
            )
            self.console.print()

        if check_result.warning_count > 0:
            self.console.print(  # noqa: E501
                "2. [bold yellow]Strongly recommend fixing warning items[/bold yellow]"
            )
            self.console.print("   - 警告は品質低下の兆候です")
            self.console.print("   - 長期的に見て型安全性が損なわれる可能性があります")
            self.console.print()

        self.console.print(  # noqa: E501
            "3. [bold blue]Use advice items as references for quality improvement"
            "[/bold blue]"
        )
        self.console.print("   - アドバイスはベストプラクティスに基づく推奨事項です")
        self.console.print("   - 段階的に適用することを検討してください")
        self.console.print()

        # 設定ファイルでの閾値調整の提案
        if check_result.error_count > 0 or check_result.warning_count > 0:
            self.console.print(  # noqa: E501
                "4. [dim]プロジェクトの状況に応じてpyproject.tomlの閾値を"
                "調整することを検討してください[/dim]"
            )
            self.console.print()
