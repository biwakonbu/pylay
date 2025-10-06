"""
品質チェックレポート生成機能

コンソール、Markdown、JSON形式で品質チェックレポートを生成します。
"""

import json
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from src.core.analyzer.quality_models import QualityCheckResult, QualityIssue

if TYPE_CHECKING:
    from src.core.analyzer.type_level_models import TypeAnalysisReport


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
        report: "TypeAnalysisReport",
        show_details: bool = False,
    ) -> None:
        """コンソール用レポートを生成して直接表示

        Args:
            check_result: 品質チェック結果
            report: 型定義分析レポート
            show_details: 詳細情報を表示するか
        """
        # ヘッダー
        self.console.rule("[bold cyan]型定義品質チェックレポート[/bold cyan]")
        self.console.print()

        # 全体サマリー
        self._show_summary_panel(check_result)

        # 統計情報テーブル
        self._show_statistics_table(check_result)

        # 問題リスト
        if check_result.issues:
            self._show_issues_table(check_result, show_details)
        else:
            self.console.print("[green]✅ 品質問題は検出されませんでした[/green]")

        # 推奨事項（問題がある場合のみ）
        if check_result.issues:
            self._show_recommendations(check_result)

    def generate_markdown_report(self, check_result: QualityCheckResult) -> str:
        """Markdown形式のレポートを生成

        Args:
            check_result: 品質チェック結果

        Returns:
            Markdown形式のレポート文字列
        """
        lines = []

        # ヘッダー
        lines.append("# 型定義品質チェックレポート")
        lines.append("")
        lines.append(f"実行日時: {self._get_current_time()}")
        lines.append("")

        # サマリー
        lines.append("## サマリー")
        lines.append("")
        lines.append(f"- **全体スコア**: {check_result.overall_score:.2f}/1.0")
        lines.append(f"- **総問題数**: {check_result.total_issues}")
        lines.append(f"- **エラー数**: {check_result.error_count}")
        lines.append(f"- **警告数**: {check_result.warning_count}")
        lines.append(f"- **アドバイス数**: {check_result.advice_count}")
        lines.append("")

        # 統計情報
        lines.append("## 統計情報")
        lines.append("")
        lines.append("| 項目 | 値 |")
        lines.append("|------|-----|")
        lines.append(
            f"| Level 1比率 | {check_result.statistics.level1_ratio * 100:.1f}% |"
        )
        lines.append(
            f"| Level 2比率 | {check_result.statistics.level2_ratio * 100:.1f}% |"
        )
        lines.append(
            f"| Level 3比率 | {check_result.statistics.level3_ratio * 100:.1f}% |"
        )
        doc_rate = check_result.statistics.documentation.implementation_rate
        lines.append(f"| ドキュメント実装率 | {doc_rate * 100:.1f}% |")
        prim_ratio = check_result.statistics.primitive_usage_ratio
        lines.append(f"| primitive使用率 | {prim_ratio * 100:.1f}% |")
        lines.append("")

        # 問題リスト
        if check_result.issues:
            lines.append("## 検出された問題")
            lines.append("")

            # 深刻度別にグループ化して表示
            for severity in ["エラー", "警告", "アドバイス"]:
                severity_issues = check_result.get_issues_by_severity(severity)
                if severity_issues:
                    severity_emoji = {"エラー": "❌", "警告": "⚠️", "アドバイス": "💡"}[
                        severity
                    ]
                    lines.append(
                        f"### {severity_emoji} {severity} ({len(severity_issues)}件)"
                    )
                    lines.append("")

                    for issue in severity_issues:
                        lines.append(f"#### {issue.message}")
                        lines.append("")
                        lines.append(f"**種類**: {issue.issue_type}")
                        lines.append(f"**提案**: {issue.suggestion}")
                        lines.append("")
                        lines.append("**改善プラン**:")
                        lines.append(f"{issue.improvement_plan}")
                        lines.append("")

                        if issue.location:
                            lines.append("**詳細情報**:")
                            lines.append(f"- ファイル: {issue.location.file}")
                            lines.append(f"- 行: {issue.location.line}")
                            if issue.location.code:
                                lines.append("```python")
                                lines.append(issue.location.code)
                                lines.append("```")
                            lines.append("")

        # 推奨事項
        if check_result.issues:
            lines.append("## 全体的な推奨事項")
            lines.append("")
            lines.append("- エラー項目を最優先で修正してください")
            lines.append("- 警告項目も可能な限り修正することを推奨します")
            lines.append(
                "- アドバイス項目は品質向上のための参考情報として活用してください"
            )
            lines.append("")

        return "\n".join(lines)

    def generate_json_report(self, check_result: QualityCheckResult) -> str:
        """JSON形式のレポートを生成

        Args:
            check_result: 品質チェック結果

        Returns:
            JSON形式のレポート文字列
        """
        # Pydanticモデルを辞書に変換してJSONシリアル化
        report_dict = {
            "summary": {
                "overall_score": check_result.overall_score,
                "total_issues": check_result.total_issues,
                "error_count": check_result.error_count,
                "warning_count": check_result.warning_count,
                "advice_count": check_result.advice_count,
                "has_errors": check_result.has_errors,
            },
            "statistics": {
                "level1_ratio": check_result.statistics.level1_ratio,
                "level2_ratio": check_result.statistics.level2_ratio,
                "level3_ratio": check_result.statistics.level3_ratio,
                "documentation_rate": (
                    check_result.statistics.documentation.implementation_rate
                ),
                "primitive_usage_ratio": (
                    check_result.statistics.primitive_usage_ratio
                ),
                "deprecated_typing_ratio": (
                    check_result.statistics.deprecated_typing_ratio
                ),
            },
            "issues": [
                {
                    "type": issue.issue_type,
                    "severity": issue.severity,
                    "message": issue.message,
                    "suggestion": issue.suggestion,
                    "improvement_plan": issue.improvement_plan,
                    "location": {
                        "file": str(issue.location.file) if issue.location else None,
                        "line": issue.location.line if issue.location else None,
                        "column": issue.location.column if issue.location else None,
                        "code": issue.location.code if issue.location else None,
                    }
                    if issue.location
                    else None,
                }
                for issue in check_result.issues
            ],
            "thresholds": {
                "level1_max": check_result.thresholds.level1_max,
                "level2_min": check_result.thresholds.level2_min,
                "level3_min": check_result.thresholds.level3_min,
            },
        }

        return json.dumps(report_dict, indent=2, ensure_ascii=False)

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
            f"[bold cyan]全体スコア:[/bold cyan] {score_text}\n"
            f"[bold cyan]総問題数:[/bold cyan] {check_result.total_issues}\n"
            f"[bold red]エラー:[/bold red] {check_result.error_count}\n"
            f"[bold yellow]警告:[/bold yellow] {check_result.warning_count}\n"
            f"[bold blue]アドバイス:[/bold blue] {check_result.advice_count}"
        )

        summary_panel = Panel(
            summary_content,
            title="[bold]📊 サマリー[/bold]",
            border_style=score_color,
        )
        self.console.print(summary_panel)
        self.console.print()

    def _show_statistics_table(self, check_result: QualityCheckResult) -> None:
        """統計情報テーブルを表示"""
        table = Table(
            title="📈 統計情報", show_header=True, header_style="bold magenta"
        )
        table.add_column("項目", style="cyan", width=20)
        table.add_column("値", style="white", justify="right")
        table.add_column("状態", style="green")

        # 型レベル統計
        level1_color = (
            "red"
            if check_result.statistics.level1_ratio > check_result.thresholds.level1_max
            else "green"
        )
        l1_status = (  # noqa: E501
            "超過"
            if check_result.statistics.level1_ratio > check_result.thresholds.level1_max
            else "正常"
        )
        table.add_row(
            "Level 1比率",
            f"{check_result.statistics.level1_ratio * 100:.1f}%",
            f"[bold {level1_color}]{l1_status}[/bold {level1_color}]",
        )

        level2_color = (
            "red"
            if check_result.statistics.level2_ratio < check_result.thresholds.level2_min
            else "green"
        )
        l2_status = (  # noqa: E501
            "不足"
            if check_result.statistics.level2_ratio < check_result.thresholds.level2_min
            else "正常"
        )
        table.add_row(
            "Level 2比率",
            f"{check_result.statistics.level2_ratio * 100:.1f}%",
            f"[bold {level2_color}]{l2_status}[/bold {level2_color}]",
        )

        level3_color = (
            "red"
            if check_result.statistics.level3_ratio < check_result.thresholds.level3_min
            else "green"
        )
        l3_status = (  # noqa: E501
            "不足"
            if check_result.statistics.level3_ratio < check_result.thresholds.level3_min
            else "正常"
        )
        table.add_row(
            "Level 3比率",
            f"{check_result.statistics.level3_ratio * 100:.1f}%",
            f"[bold {level3_color}]{l3_status}[/bold {level3_color}]",
        )

        # ドキュメント統計
        doc_rate = check_result.statistics.documentation.implementation_rate
        doc_color = "yellow" if doc_rate < 0.8 else "green"
        doc_status = "要改善" if doc_rate < 0.8 else "良好"
        table.add_row(
            "ドキュメント実装率",
            f"{doc_rate * 100:.1f}%",
            f"[bold {doc_color}]{doc_status}[/bold {doc_color}]",
        )

        # その他の統計
        prim_ratio = check_result.statistics.primitive_usage_ratio
        primitive_color = "red" if prim_ratio > 0.10 else "green"
        prim_status = "過多" if prim_ratio > 0.10 else "正常"
        table.add_row(
            "primitive使用率",
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
        for severity in ["エラー", "警告", "アドバイス"]:
            severity_issues = check_result.get_issues_by_severity(severity)
            if not severity_issues:
                continue

            # 深刻度別の色設定
            color = {"エラー": "red", "警告": "yellow", "アドバイス": "blue"}[severity]
            severity_label = {
                "エラー": "ERROR",
                "警告": "WARNING",
                "アドバイス": "ADVICE",
            }[severity]

            rule_text = (  # noqa: E501
                f"[bold {color}]{severity_label} ({len(severity_issues)} issues)"
                f"[/bold {color}]"
            )
            self.console.rule(rule_text, style=color)
            self.console.print()

            for issue in severity_issues:
                self._show_issue_detail(issue, show_details, color)

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
        self.console.print("[bold cyan]💡 推奨事項[/bold cyan]")
        self.console.print()

        if check_result.error_count > 0:
            self.console.print(
                "1. [bold red]エラー項目を最優先で修正してください[/bold red]"
            )
            self.console.print("   - エラーは型定義の品質に深刻な影響を及ぼします")
            self.console.print(
                "   - CI/CDでエラーが発生した場合、ビルドが失敗する可能性があります"
            )
            self.console.print()

        if check_result.warning_count > 0:
            self.console.print(  # noqa: E501
                "2. [bold yellow]警告項目も可能な限り修正することを推奨します"
                "[/bold yellow]"
            )
            self.console.print("   - 警告は品質低下の兆候です")
            self.console.print("   - 長期的に見て型安全性が損なわれる可能性があります")
            self.console.print()

        self.console.print(  # noqa: E501
            "3. [bold blue]アドバイス項目は品質向上のための参考情報として活用して"
            "ください[/bold blue]"
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

    def _get_current_time(self) -> str:
        """現在の時刻を取得（シンプルな実装）"""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
