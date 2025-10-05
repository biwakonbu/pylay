"""
type: ignore 診断レポート生成

Richライブラリを使用して、モダンで洗練されたCLI UIを提供します。
"""

from __future__ import annotations

from pathlib import Path

from rich.box import SIMPLE
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from .type_ignore_analyzer import Priority, TypeIgnoreIssue, TypeIgnoreSummary


class TypeIgnoreReporter:
    """type: ignore 診断レポート生成クラス"""

    def __init__(self) -> None:
        """レポーター初期化"""
        self.console = Console()

    def generate_console_report(
        self,
        issues: list[TypeIgnoreIssue],
        summary: TypeIgnoreSummary,
        show_solutions: bool = False,
    ) -> None:
        """
        コンソール用レポートを生成・表示

        Args:
            issues: type: ignore 問題のリスト
            summary: サマリー情報
            show_solutions: 解決策を表示するか
        """
        # ヘッダー
        self.console.rule(
            "[bold cyan]Type Ignore Diagnostics[/bold cyan]", style="cyan"
        )
        self.console.print()

        # ファイルごとにグループ化
        issues_by_file: dict[str, list[TypeIgnoreIssue]] = {}
        for issue in issues:
            file_path = str(issue.file_path)
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append(issue)

        # 各ファイルのレポート
        for file_path, file_issues in issues_by_file.items():
            self._print_file_section(file_path, file_issues, show_solutions)

        # サマリー
        self._print_summary(summary)

        self.console.rule(style="cyan")

    def _print_file_section(
        self, file_path: str, issues: list[TypeIgnoreIssue], show_solutions: bool
    ) -> None:
        """
        ファイルセクションを表示

        Args:
            file_path: ファイルパス
            issues: 該当ファイルの問題リスト
            show_solutions: 解決策を表示するか
        """
        # ファイル名
        file_p = Path(file_path)
        if file_p.is_absolute():
            try:
                rel_path = file_p.relative_to(Path.cwd())
            except ValueError:
                rel_path = file_p
        else:
            rel_path = file_p
        self.console.print(f"[bold]{rel_path}[/bold]\n")

        # 各問題を表示
        for issue in sorted(issues, key=lambda i: i.line_number):
            self._print_issue(issue, show_solutions)

        self.console.rule(style="dim")

    def _print_issue(self, issue: TypeIgnoreIssue, show_solutions: bool) -> None:
        """
        個別の問題を表示

        Args:
            issue: type: ignore 問題
            show_solutions: 解決策を表示するか
        """
        # 優先度ラベル
        priority_color = self._get_priority_color(issue.priority)
        priority_text = Text(f"  {issue.priority}", style=f"bold {priority_color}")
        line_info = Text(f"    Line {issue.line_number}", style="dim")
        ignore_type_info = Text(
            f"    type: ignore[{issue.ignore_type}]", style="yellow"
        )

        self.console.print(priority_text, line_info, ignore_type_info)
        self.console.print()

        # 原因
        self.console.print(f"  [bold]Cause[/bold]     {issue.cause}")
        self.console.print(f"  [bold]Detail[/bold]    {issue.detail}")
        self.console.print()

        # コードブロック
        self.console.print("  [bold]Code[/bold]")
        self._print_code_context(issue)
        self.console.print()

        # 解決策（オプション）
        if show_solutions and issue.solutions:
            self.console.print("  [bold]Solution[/bold]")
            for solution in issue.solutions:
                self.console.print(f"    • {solution}")
            self.console.print()

        # 提案コード例（オプション）
        if show_solutions and issue.solutions:
            self._print_suggested_code(issue)

    def _print_code_context(self, issue: TypeIgnoreIssue) -> None:
        """
        コードコンテキストを表示（Syntax highlightingとマーカー付き）

        Args:
            issue: type: ignore 問題
        """
        ctx = issue.code_context
        start_line = ctx.line_number - len(ctx.before_lines)

        # コード全体を構築
        code_lines = ctx.before_lines + [ctx.target_line] + ctx.after_lines
        code = "\n".join(code_lines)

        # Syntax highlight
        syntax = Syntax(
            code,
            "python",
            theme="monokai",
            line_numbers=True,
            start_line=start_line,
            highlight_lines={ctx.line_number},
        )

        self.console.print("    ", syntax)

    def _print_suggested_code(self, issue: TypeIgnoreIssue) -> None:
        """
        提案コードを表示

        Args:
            issue: type: ignore 問題
        """
        # 簡易的な提案コード生成（実際の実装では、より詳細な提案を生成）
        target_line = issue.code_context.target_line
        suggested = target_line.replace("# type: ignore", "").strip()

        # Pydantic関連の提案
        if "BaseModel" in target_line and issue.ignore_type == "call-arg":
            suggested = (
                target_line.replace("TypeSpec(", "TypeSpec.model_construct(")
                .replace("# type: ignore", "")
                .strip()
            )

        if suggested != target_line.replace("# type: ignore", "").strip():
            self.console.print("  [bold]Suggested[/bold]")
            syntax = Syntax(
                suggested,
                "python",
                theme="monokai",
                line_numbers=False,
            )
            self.console.print("    ", syntax)
            self.console.print()

    def _print_summary(self, summary: TypeIgnoreSummary) -> None:
        """
        サマリーテーブルを表示

        Args:
            summary: サマリー情報
        """
        self.console.print("\n[bold cyan]Summary by Priority[/bold cyan]\n")

        # 優先度テーブル
        table = Table(box=SIMPLE, show_header=True, header_style="bold")
        table.add_column("Priority", style="bold")
        table.add_column("Category", style="cyan")
        table.add_column("Count", justify="right")
        table.add_column("Ratio", justify="right")

        total = summary.total_count or 1  # ゼロ除算回避

        # HIGH
        high_ratio = (summary.high_priority_count / total) * 100
        table.add_row(
            Text("HIGH", style="bold red"),
            "Anyの多用、重要な型チェック回避",
            str(summary.high_priority_count),
            f"{high_ratio:.1f}%",
        )

        # MEDIUM
        medium_ratio = (summary.medium_priority_count / total) * 100
        table.add_row(
            Text("MEDIUM", style="bold yellow"),
            "局所的な型エラー（引数・戻り値）",
            str(summary.medium_priority_count),
            f"{medium_ratio:.1f}%",
        )

        # LOW
        low_ratio = (summary.low_priority_count / total) * 100
        table.add_row(
            Text("LOW", style="bold green"),
            "既知の制約（Pydantic動的属性等）",
            str(summary.low_priority_count),
            f"{low_ratio:.1f}%",
        )

        # Total
        total_ratio = "0%" if summary.total_count == 0 else "100%"
        table.add_row(
            "",
            "[bold]Total[/bold]",
            f"[bold]{summary.total_count}[/bold]",
            f"[bold]{total_ratio}[/bold]",
            style="dim",
        )

        self.console.print(table)
        self.console.print()

    def _get_priority_color(self, priority: Priority) -> str:
        """
        優先度に応じた色を取得

        Args:
            priority: 優先度

        Returns:
            色の文字列
        """
        return {"HIGH": "red", "MEDIUM": "yellow", "LOW": "green"}.get(
            priority, "white"
        )

    def export_json_report(
        self, issues: list[TypeIgnoreIssue], output_path: str
    ) -> None:
        """
        JSON形式でレポートをエクスポート

        Args:
            issues: type: ignore 問題のリスト
            output_path: 出力先パス
        """
        import json

        data = [issue.model_dump() for issue in issues]

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        msg = f"[bold green]✅ JSONレポートをエクスポートしました: {output_path}"
        msg += "[/bold green]"
        self.console.print(msg)
