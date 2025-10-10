# pylayプロジェクト UI/UXガイドライン

このドキュメントは、pylayプロジェクトにおけるCLIのユーザーインターフェース設計原則を定義します。

## 目次

- [基本原則](#基本原則)
- [テキストと言語](#テキストと言語)
- [ビジュアルデザイン](#ビジュアルデザイン)
- [実装ガイドライン](#実装ガイドライン)
- [具体例](#具体例)

## 基本原則

### 1. モダンでカッコイイビジュアル

- **Rich**ライブラリを最大限活用したモダンなターミナルUI
- 情報の階層構造を視覚的に明確に表現
- 適度な余白と罫線で空間をデザイン
- 色彩を効果的に使用した情報の強調

### 2. シンプルで洗練されたデザイン

- 装飾過多を避け、必要最小限の要素で構成
- **絵文字は使用しない**（例外：ユーザーが明示的に要求した場合のみ）
- テキスト、色、罫線、余白のみでビジュアルを構築
- 読みやすさと情報の明確さを最優先

## テキストと言語

### 項目名・ラベル：英語

**すべての項目名、ラベル、キーワードは英語で記述します。**

#### 良い例

```python
# 統計テーブル
table.add_column("Item", style="cyan")
table.add_column("Value", style="white")
table.add_column("Status", style="green")

table.add_row("Level 1 Ratio", "45.0%", "OK")
table.add_row("Documentation Rate", "85.0%", "Good")
```

#### 悪い例

```python
# ❌ 項目名に日本語
table.add_column("項目", style="cyan")
table.add_column("値", style="white")
table.add_column("状態", style="green")
```

### 説明文・メッセージ：日本語

**ユーザー向けの説明文、ヘルプメッセージ、詳細情報は日本語で記述します。**

#### 良い例

```python
console.print("1. [bold red]Fix error items with highest priority[/bold red]")
console.print("   - エラーは型定義の品質に深刻な影響を及ぼします")
console.print("   - CI/CDでエラーが発生した場合、ビルドが失敗する可能性があります")
```

#### 悪い例

```python
# ❌ 説明文も英語にしてしまう
console.print("   - Errors have a serious impact on type definition quality")
```

### 定数値・内部値：英語

**severity、status、その他の内部で使用される定数値は英語で定義します。**

#### 良い例

```python
type SeverityName = Literal["advice", "warning", "error"]

SEVERITIES: Final[tuple[Literal["error", "warning", "advice"], ...]] = (
    "error",
    "warning",
    "advice",
)
```

#### 悪い例

```python
# ❌ 内部値に日本語
type SeverityName = Literal["アドバイス", "警告", "エラー"]
```

## ビジュアルデザイン

### 1. 色の使用

**意味を持った色を一貫して使用します。**

| 色 | 用途 | 例 |
|----|------|-----|
| `red` | エラー、危険、超過 | エラーメッセージ、閾値超過 |
| `yellow` | 警告、注意 | 警告メッセージ、要改善 |
| `green` | 成功、正常 | 正常状態、合格 |
| `blue` | 情報、アドバイス | アドバイスメッセージ |
| `cyan` | ラベル、見出し | テーブルのヘッダー、項目名 |
| `magenta` | 強調、特別 | 統計情報のタイトル |
| `dim` | 補足、低優先度 | 注釈、補助情報 |

### 2. 罫線と区切り

**Richの罫線機能を活用して情報を視覚的に区切ります。**

```python
# セクション区切り
console.rule("[bold cyan]Type Definition Quality Report[/bold cyan]")

# セクション内の区切り（severity別）
console.rule(f"[bold {color}]{severity_label} ({count} issues)[/bold {color}]", style=color)
```

### 3. パネルとテーブル

**情報のグルーピングにはパネルとテーブルを活用します。**

```python
# サマリー情報はパネルで表示
summary_panel = Panel(
    summary_content,
    title="[bold]Summary[/bold]",
    border_style=score_color,
)

# 統計情報はテーブルで表示
table = Table(
    title="Statistics",
    show_header=True,
    header_style="bold magenta"
)
```

### 4. 余白と階層

**適切な余白で情報の階層を表現します。**

```python
# セクション間に空行を挿入
console.print()

# インデントで階層を表現（2スペース単位）
console.print("1. [bold red]Fix error items with highest priority[/bold red]")
console.print("   - エラーは型定義の品質に深刻な影響を及ぼします")
console.print("   - CI/CDでエラーが発生した場合、ビルドが失敗する可能性があります")
```

## 実装ガイドライン

### 1. 絵文字の禁止

**絵文字は使用しません。テキストと色で表現します。**

#### 変更前（悪い例）

```python
console.print("[bold cyan]💡 Recommendations[/bold cyan]")
console.print("[green]✅ 品質問題は検出されませんでした[/green]")

severity_emoji = {"error": "❌", "warning": "⚠️", "advice": "💡"}
```

#### 変更後（良い例）

```python
console.print("[bold cyan]Recommendations[/bold cyan]")
console.print("[green]No quality issues detected[/green]")

# 色とテキストで表現
severity_label = {"error": "ERROR", "warning": "WARNING", "advice": "ADVICE"}
```

### 2. 項目名の英語化

**すべてのラベル、項目名、ステータス表示は英語にします。**

| 変更前（日本語） | 変更後（英語） |
|------------------|---------------|
| 全体スコア | Overall Score |
| 総問題数 | Total Issues |
| エラー数 | Error Count |
| 警告数 | Warning Count |
| Level 1比率 | Level 1 Ratio |
| ドキュメント実装率 | Documentation Rate |
| primitive使用率 | Primitive Usage Ratio |
| 正常 | OK |
| 超過 | Exceeded |
| 不足 | Low |
| 要改善 | Needs Improvement |
| 良好 | Good |
| 過多 | High |

### 3. Rich機能の活用

**Richの豊富な機能を積極的に活用します。**

- `Console`: 基本的な出力管理
- `Table`: 表形式データの表示
- `Panel`: 情報のグルーピング
- `Rule`: セクション区切り
- `Syntax`: コードブロックのシンタックスハイライト
- `Text`: 複雑なスタイル適用

```python
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()

# シンタックスハイライト付きコード表示
syntax = Syntax(code_block, "python", theme="monokai", line_numbers=True)
console.print(syntax)
```

## 具体例

### 品質チェックレポート（良い例）

```python
def _show_summary_panel(self, check_result: QualityCheckResult) -> None:
    """サマリーパネルを表示"""
    score_text = f"[bold {score_color}]{check_result.overall_score:.2f}/1.0[/bold {score_color}]"

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
    console.print(summary_panel)
    console.print()
```

### 統計テーブル（良い例）

```python
def _show_statistics_table(self, check_result: QualityCheckResult) -> None:
    """統計情報テーブルを表示"""
    table = Table(
        title="Statistics",
        show_header=True,
        header_style="bold magenta"
    )
    table.add_column("Item", style="cyan", width=30)
    table.add_column("Value", style="white", justify="right")
    table.add_column("Status", style="green")

    # 型レベル統計
    table.add_row(
        "Level 1 Ratio",
        f"{check_result.statistics.level1_ratio * 100:.1f}%",
        f"[bold {level1_color}]{l1_status}[/bold {level1_color}]",
    )

    console.print(table)
    console.print()
```

### 推奨事項（良い例）

```python
def _show_recommendations(self, check_result: QualityCheckResult) -> None:
    """推奨事項を表示"""
    console.print("[bold cyan]Recommendations[/bold cyan]")
    console.print()

    if check_result.error_count > 0:
        console.print(
            "1. [bold red]Fix error items with highest priority[/bold red]"
        )
        console.print("   - エラーは型定義の品質に深刻な影響を及ぼします")
        console.print("   - CI/CDでエラーが発生した場合、ビルドが失敗する可能性があります")
        console.print()
```

## チェックリスト

新しいUI要素を実装する際は、以下をチェックしてください：

- [ ] 項目名・ラベルはすべて英語か？
- [ ] 説明文・メッセージは日本語か？
- [ ] 絵文字を使用していないか？
- [ ] Richの機能を適切に活用しているか？
- [ ] 色の使い方は一貫しているか？
- [ ] 適切な余白と階層構造があるか？
- [ ] 情報は視覚的に明確に区別できるか？

## 参考リソース

- [Rich Documentation](https://rich.readthedocs.io/)
- [プロジェクトのCLAUDE.md](../CLAUDE.md) - プロジェクト全体のガイドライン
- [Issue #44](https://github.com/biwakonbu/pylay/issues/44) - CLI出力の項目名英語化の議論

---

このガイドラインは、プロジェクトの進化に応じて更新されます。変更が必要な場合は、PRで提案してください。
