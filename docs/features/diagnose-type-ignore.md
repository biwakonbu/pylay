# type: ignore 診断機能

## 概要

`pylay check --focus ignore` コマンドは、プロジェクト内で使用されている `# type: ignore` コメントの原因を自動的に特定し、具体的な解決策を提案する機能です。

## 背景と目的

`# type: ignore` コメントは型チェックエラーを一時的に回避するために使用されますが、以下の課題がありました：

1. **原因の不明確さ**: なぜ型チェックを回避する必要があったのかが不明
2. **技術的負債の蓄積**: 放置された type: ignore が増加し、型安全性が低下
3. **解決方法の不明確さ**: どのように修正すべきか分からない

この機能により、型安全性の向上と技術的負債の削減を実現します。

## 主な機能

### 1. 自動検出
- 正規表現による `# type: ignore` コメントの検出
- ignore種別の識別（`call-arg`, `arg-type`, `general` など）

### 2. 原因特定
- mypy実行による型エラー情報の取得
- エラーメッセージと行番号の紐付け
- AST解析による原因式の特定

### 3. 優先度判定
問題を3段階で分類：

- **HIGH**: Any型の多用、重要な型チェック回避
- **MEDIUM**: 局所的な型エラー（引数・戻り値）
- **LOW**: 既知の制約（Pydantic動的属性等）

### 4. 解決策提案
コンテキストに応じた具体的な修正方法を提示：

- **Pydantic関連**: `model_construct()` や `TypedDict` の使用
- **dict型アクセス**: Pydanticモデルでの直接操作
- **call-arg**: 型アノテーションの追加
- **汎用的**: キャストやバリデーション追加

## 使用方法

### CLIコマンド

#### 基本的な使い方
```bash
# プロジェクト全体を診断
pylay check --focus ignore

# 特定ファイルを診断
pylay check --focus ignore src/core/converters/type_to_yaml.py

# 解決策を含む詳細表示
pylay check --focus ignore -v

# JSON形式で出力（準備中：実装未完了）
# pylay check --focus ignore --format json --output report.json
```

#### オプション一覧

| オプション | 説明 |
|----------|------|
| `TARGET` | 解析対象のファイルまたはディレクトリ（指定しない場合はカレントディレクトリ） |
| `--focus ignore` | type-ignore診断を実行 |
| `-v`, `--verbose` | 解決策を含む詳細情報を表示 |
| `--format` | **（準備中）** 出力形式（console/json、デフォルト: console） |
| `--output`, `-o` | **（準備中）** 出力ファイルパス（format=jsonの場合に使用） |

### Makeターゲット

開発ワークフローに簡単に統合できるMakeターゲットを提供：

```bash
# プロジェクト全体を診断
make diagnose-ignore

# 特定ファイルを診断（FILE変数で指定）
make diagnose-ignore-file FILE=src/cli/analyze_issues.py

# 高優先度のみ診断
make diagnose-ignore-high
```

## 出力例

### コンソール出力

```
─────────────────────────── Type Ignore Diagnostics ────────────────────────────

src/cli/analyze_issues.py

  MEDIUM     Line 270     type: ignore[general]

  Cause     型チェックを回避: general
  Detail    dict型の値アクセスで型が不明確

  Code

  267         print(f"⚠️ 問題のあるチェック: {issues}/{total}")
  268
  269         print("\n📋 詳細結果:")
❱ 270         for result in summary["results"]:  # type: ignore
  271             status = (
  272                 "✅"
  273                 if result["success"] and not result["has_issues"]

  Solution
    • Pydanticモデルのまま操作（model_dump()を使わない）
    • TypedDict形式のスキーマを追加

────────────────────────────────────────────────────────────────────────────────

Summary by Priority


  Priority   Category                           Count    Ratio
 ──────────────────────────────────────────────────────────────
  HIGH       Anyの多用、重要な型チェック回避        0     0.0%
  MEDIUM     局所的な型エラー（引数・戻り値）       4   100.0%
  LOW        既知の制約（Pydantic動的属性等）       0     0.0%
             Total                                  4     100%
```

### JSON出力

```json
[
  {
    "file_path": "src/cli/analyze_issues.py",
    "line_number": 270,
    "ignore_type": "general",
    "cause": "型チェックを回避: general",
    "detail": "dict型の値アクセスで型が不明確",
    "code_context": {
      "before_lines": ["..."],
      "target_line": "for result in summary[\"results\"]:  # type: ignore",
      "after_lines": ["..."],
      "line_number": 270
    },
    "priority": "MEDIUM",
    "solutions": [
      "Pydanticモデルのまま操作（model_dump()を使わない）",
      "TypedDict形式のスキーマを追加"
    ]
  }
]
```

## 技術詳細

### アーキテクチャ

```
┌─────────────────────────────────────────┐
│        diagnose-type-ignore CLI         │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│       TypeIgnoreAnalyzer                │
│  - type: ignore検出                     │
│  - mypy実行と型エラー取得               │
│  - 優先度判定                           │
│  - 解決策生成                           │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│       TypeIgnoreReporter                │
│  - Richベースのコンソール出力           │
│  - JSON形式エクスポート                 │
└─────────────────────────────────────────┘
```

### データモデル

#### TypeIgnoreIssue
```python
class TypeIgnoreIssue(BaseModel):
    file_path: FilePath
    line_number: LineNumber
    ignore_type: str  # e.g., "call-arg", "general"
    cause: str
    detail: str
    code_context: CodeContext
    priority: Priority  # "HIGH" | "MEDIUM" | "LOW"
    solutions: list[str]
```

#### TypeIgnoreSummary
```python
class TypeIgnoreSummary(BaseModel):
    total_count: int
    high_priority_count: int
    medium_priority_count: int
    low_priority_count: int
    by_category: dict[str, int]
```

### 優先度判定アルゴリズム

```python
def _determine_priority(
    ignore_type: str,
    code_context: CodeContext,
    errors: list[dict[str, str]],
) -> Priority:
    # HIGH: Any型の多用、重要な型チェック回避
    if "Any" in target and ignore_type in ["assignment", "arg-type", "return-value"]:
        return "HIGH"

    # MEDIUM: 局所的な型エラー
    if ignore_type in ["call-arg", "arg-type", "attr-defined"]:
        return "MEDIUM"

    # LOW: 既知の制約（Pydantic動的属性等）
    if "BaseModel" in target or "model_construct" in target:
        return "LOW"

    return "MEDIUM"
```

## ユースケース

### 1. 技術的負債の可視化
```bash
# プロジェクト全体のtype: ignoreを診断
make diagnose-ignore

# 結果をJSON形式で保存
pylay check --focus ignore --format json --output tech-debt.json
```

### 2. 優先的な修正対象の特定
```bash
# 高優先度の問題のみ表示
make diagnose-ignore-high

# 結果を元に計画的に修正
```

### 3. コードレビューでの活用
```bash
# PRで追加されたtype: ignoreを診断
pylay check --focus ignore path/to/changed_file.py -v

# 解決策を参考に修正
```

### 4. CI/CDパイプラインへの統合
```yaml
# .github/workflows/type-check.yml
- name: Diagnose type: ignore
  run: |
    pylay check --focus ignore --format json --output type-ignore-report.json
    # レポートをアーティファクトとして保存
```

## 期待される効果

1. **型安全性の向上**: type: ignore の適切な削減により型安全性が向上
2. **技術的負債の削減**: 放置された type: ignore の原因が明確化され、計画的な解消が可能
3. **開発者体験の向上**: 具体的な解決策により、修正が容易に
4. **コード品質の可視化**: 優先度別の集計により、問題の重要度が一目瞭然

## 今後の拡張予定

- [ ] pyright統合による型エラー情報の充実
- [ ] 自動修正機能（`--fix` オプション）
- [ ] CI/CDパイプラインへの統合サンプル
- [ ] HTML形式レポートの生成
- [ ] 型エラーパターンの学習と提案精度の向上

## 関連リンク

- [Issue #36](https://github.com/biwakonbu/pylay/issues/36)
- [PR #43](https://github.com/biwakonbu/pylay/pull/43)
- [型定義ルール](../typing-rule.md)
