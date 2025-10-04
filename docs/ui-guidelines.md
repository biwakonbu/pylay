# pylay UI実装統一ガイドライン

このガイドラインは、pylayプロジェクト全体で統一された美しいUI体験を提供するための基準を定義します。すべてのコマンドでこれらのガイドラインを遵守し、一貫したユーザー体験を提供してください。

## 基本原則

### 1. Richライブラリの積極的な活用
すべてのUI実装で `Rich` ライブラリを活用し、視覚的に魅力的なインターフェースを提供します。

### 2. 一貫性のあるデザイン
すべてのコマンドで同じUIパターンを維持し、ユーザーが直感的に操作できるようにします。

### 3. 情報量の適切なバランス
必要な情報を明確に表示しつつ、過度な情報量でユーザーを圧倒しないようにします。

### 4. 控えめな絵文字使用
絵文字は必要最小限に使用し、視覚的なノイズを避けます。

## UIコンポーネントの使用指針

### 1. Panel（枠付き情報表示）
処理の開始・完了、エラー情報などで使用します。

```python
from rich.panel import Panel

# 処理開始時のPanel
start_panel = Panel(
    f"[bold cyan]入力ファイル:[/bold cyan] {input_file}\n"
    f"[bold cyan]出力ファイル:[/bold cyan] {output_file}",
    title="[bold green]🚀 処理開始[/bold green]",
    border_style="green",
)
console.print(start_panel)

# エラー時のPanel
error_panel = Panel(
    f"[red]エラー: {error_message}[/red]",
    title="[bold red]❌ 処理エラー[/bold red]",
    border_style="red",
)
console.print(error_panel)
```

### 2. Table（テーブル表示）
結果のサマリーや統計情報などで使用します。

```python
from rich.table import Table
from rich.box import SIMPLE

result_table = Table(
    title="処理結果サマリー",
    show_header=True,
    border_style="green",
    width=80,
    header_style="",
    box=SIMPLE,
)
result_table.add_column("項目", style="cyan", no_wrap=True, width=40)
result_table.add_column("結果", style="green", justify="right", width=30)

result_table.add_row("入力ファイル", input_file)
result_table.add_row("出力ファイル", output_file)
result_table.add_row("処理時間", f"{elapsed:.2f}秒")

console.print(result_table)
```

### 3. Progress（プログレスバー）
処理の進行状況を表示します。

```python
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)

with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    TimeRemainingColumn(),
    console=console,
    transient=True,
) as progress:
    task = progress.add_task("処理実行中...", total=total_items)
    # 実際の処理
    for item in items:
        process_item(item)
        progress.advance(task)
```

### 4. console.rule（セクション区切り）
処理の各段階を明確に区切ります。

```python
console.rule("[bold cyan]処理開始[/bold cyan]")
# 処理実行
console.rule("[bold green]処理完了[/bold green]")
```

### 5. console.status（ステータス表示）
処理中の状態を表示します。

```python
with console.status("[bold green]ファイル読み込み中...") as status:
    # ファイル読み込み処理
    data = load_file(input_file)
```

## コマンド別UIパターン

### パターン1: ファイル変換コマンド（type_to_yaml, yaml_to_type, generate_docs）

#### 処理開始時
```python
start_panel = Panel(
    f"[bold cyan]入力ファイル:[/bold cyan] {input_path.name}\n"
    f"[bold cyan]出力ファイル:[/bold cyan] {output_path}",
    title="[bold green]🚀 変換開始[/bold green]",
    border_style="green",
)
console.print(start_panel)
```

#### 処理中（ステータス表示）
```python
with console.status("[bold green]ファイル処理中...") as status:
    # 実際の処理
    result = process_file(input_file)
```

#### 結果表示（テーブル）
```python
result_table = Table(
    title="変換結果",
    show_header=True,
    border_style="green",
    width=80,
    box=SIMPLE,
)
result_table.add_column("項目", style="cyan", width=40)
result_table.add_column("結果", style="green", justify="right", width=30)

result_table.add_row("入力ファイル", input_path.name)
result_table.add_row("出力ファイル", output_path.name)
result_table.add_row("処理時間", f"{elapsed:.2f}秒")

console.print(result_table)
```

#### 処理完了時
```python
complete_panel = Panel(
    f"[bold green]✅ 変換が完了しました[/bold green]\n\n"
    f"[bold cyan]出力ファイル:[/bold cyan] {output_path}",
    title="[bold green]🎉 処理完了[/bold green]",
    border_style="green",
)
console.print(complete_panel)
```

### パターン2: 解析コマンド（analyze_types, project_analyze）

#### 処理開始時
```python
start_panel = Panel(
    f"[bold cyan]解析対象:[/bold cyan] {target_path}\n"
    f"[bold cyan]出力形式:[/bold cyan] {format_type}",
    title="[bold green]🔍 解析開始[/bold green]",
    border_style="green",
)
console.print(start_panel)
```

#### 処理中（プログレスバー）
```python
with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    TimeRemainingColumn(),
    console=console,
    transient=True,
) as progress:
    if target_path.is_file():
        task = progress.add_task("ファイル解析中...", total=1)
        report = analyzer.analyze_file(target_path)
    else:
        file_count = sum(1 for _ in target_path.rglob("*.py"))
        task = progress.add_task("ディレクトリ解析中...", total=file_count)
        report = analyzer.analyze_directory(target_path)

    progress.advance(task)
```

#### エラー時
```python
error_panel = Panel(
    f"[red]エラー: {error_message}[/red]",
    title="[bold red]❌ 解析エラー[/bold red]",
    border_style="red",
)
console.print(error_panel)
```

## 色分けルール

### 基本色
- **青系（cyan/blue）**: ファイル名、パス、通常情報
- **緑（green）**: 成功、完了、正常値
- **赤（red）**: エラー、失敗、異常値
- **黄色（yellow）**: 警告、注意事項
- **マゼンタ（magenta）**: 統計情報、コード品質指標

### 動的な色分け
状態に応じて色を動的に変更します：

```python
# 成功・失敗の動的表示
status_icon = "✓" if success else "✗"
status_color = "green" if success else "red"
console.print(f"[{status_color}]{status_icon} {message}[/{status_color}]")
```

## テーブルデザインの統一

### 基本設定
```python
table = Table(
    title="タイトル",
    show_header=True,
    border_style="green",  # または適切な色
    width=80,  # 適切な幅を設定
    header_style="",
    box=SIMPLE,
)
```

### カラム設定例
```python
table.add_column("項目名", style="cyan", no_wrap=True, width=40)
table.add_column("値", style="green", justify="right", width=20)
table.add_column("状態", style="yellow", justify="center", width=10)
```

## 絵文字の使用基準

### 推奨絵文字
- ✅ 成功・完了
- ❌ エラー・失敗
- ⚠️ 警告・注意
- 🚀 開始・起動
- 🔍 検索・分析
- 📁 ファイル・ディレクトリ
- 📊 統計・レポート

### 使用原則
1. 意味を明確に伝える場合のみ使用
2. 過度な使用を避け、視覚的なノイズを防ぐ
3. タイトルや重要なメッセージでのみ使用を検討

## 実装例

### 完全な実装例（基準実装）
実際の基準実装は以下のファイルで確認してください：

- **[src/cli/commands/project_analyze.py](src/cli/commands/project_analyze.py)** - Panel/Progress/Table/Treeの総合実装
- **[src/core/analyzer/type_reporter.py](src/core/analyzer/type_reporter.py)** - Table/rule/動的色分けの完璧な実装

### 改善後の実装例
- **[src/cli/commands/generate_docs.py](src/cli/commands/generate_docs.py)** - 本ガイドラインに基づく実装
- **[src/cli/commands/type_to_yaml.py](src/cli/commands/type_to_yaml.py)** - 本ガイドラインに基づく実装
- **[src/cli/commands/yaml_to_type.py](src/cli/commands/yaml_to_type.py)** - 本ガイドラインに基づく実装
- **[src/cli/commands/analyze_types.py](src/cli/commands/analyze_types.py)** - 本ガイドラインに基づく実装

## 遵守事項

### 必須遵守
1. 新しいコマンド実装時は必ず本ガイドラインを参照
2. 既存のコマンドを改善する場合は本ガイドラインに準拠
3. UIの変更時はプロジェクト全体の一貫性を考慮

### 品質基準
- 本ガイドラインを下回るUI実装は受け入れられません
- すべてのコマンドで統一された美しいUI体験を提供してください
- ユーザビリティを最優先に考慮した設計を心がけてください

## 参考資料

- [Rich 公式ドキュメント](https://rich.readthedocs.io/)
- [プロジェクトの基準実装例](#実装例)
- [現在の美しい実装例](#改善後の実装例)
