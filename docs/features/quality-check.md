# 品質チェック機能 (pylay quality)

## 概要

`pylay quality` コマンドは、プロジェクトの型定義品質を分析し、問題箇所を検出して改善プランを提示する機能です。テンプレートベースの実装により、LLMを使用せずに実用的な品質チェックツールとして機能します。

**設計方針**: 型安全性（mypy/pyright静的解析）を最優先とし、バリデーションは補助的保証として位置づけます。

## 主要機能

### 1. 型定義レベル分析

プロジェクト内の全型定義を以下の3レベルに分類し、比率を分析します：

- **Level 1**: `type` エイリアス（制約なし）
- **Level 2**: `NewType` + `Annotated` + (`Field` | `AfterValidator`)（★プリミティブ型代替）
- **Level 3**: `dataclass` + Pydantic または `BaseModel`（複雑なドメイン型）

### 2. 品質指標の計測

以下の指標を計測し、pyproject.toml設定の閾値と比較します：

| 指標 | 説明 | 推奨値 |
|------|------|--------|
| Level 1 比率 | 制約なし型エイリアスの割合 | 最大15% |
| Level 2 比率 | 制約付き型の割合 | 最小50% |
| Level 3 比率 | 複雑なドメイン型の割合 | 最小20% |
| ドキュメント実装率 | docstringがある型の割合 | 最小70% |
| Primitive型使用率 | 直接使用されているprimitive型の割合 | 最大10% |

### 3. 問題検出と分類

検出された問題を深刻度で分類します：

- **ERROR**: 型定義品質に深刻な影響を及ぼす問題
  - Level 2比率が低すぎる（< 50%）
  - Primitive型使用が多すぎる（> 10%）

- **WARNING**: 品質低下の兆候
  - Level 1比率が高すぎる（> 15%）
  - ドキュメント実装率が低い（< 70%）

- **ADVICE**: 品質向上のための推奨事項
  - Level 3比率の最適化
  - 未使用型の整理

### 4. 改善プランの提示

各問題に対して、以下を含む詳細な改善プランを生成します：

**テンプレートベースの提案**:
- 型名候補のヒューリスティック推測
- バリデーションパターンのカタログ
- 段階的な修正手順（Step 1, 2, 3...）
- 関連ファイルのリスト
- 実装コンテキスト（Why, Effect, Impact）

## 使用方法

### 基本的な使用法

```bash
# 基本的な品質チェック
pylay quality src/

# 詳細な問題箇所を表示（コード周辺を含む）
pylay quality --show-details src/

# 厳格モードで実行（エラー時は終了コード1）
pylay quality --strict src/
```

### 出力形式の指定

```bash
# コンソール出力（デフォルト）
pylay quality src/

# Markdownレポート出力
pylay quality --format markdown --output report.md src/

# JSON形式で出力
pylay quality --format json --output report.json src/

# YAML形式で問題詳細をエクスポート（修正計画含む）
pylay quality --export-details problems.yaml src/
```

### カスタム設定の使用

```bash
# カスタム設定ファイル使用
pylay quality --config custom.toml src/

# pyproject.tomlの設定を使用（デフォルト）
pylay quality src/
```

## 設定ファイル（pyproject.toml）

### 基本設定

```toml
[tool.pylay.quality_check]
# 型レベル閾値（厳格モード）
level1_ratio_max = 0.15  # Level 1型エイリアスの最大比率（15%）
level2_ratio_min = 0.50  # Level 2制約付き型の最小比率（50%）
level3_ratio_min = 0.20  # Level 3ドメイン型の最小比率（20%）

# 品質指標閾値
documentation_ratio_min = 0.70  # ドキュメント実装率の最小値（70%）
primitive_usage_max = 0.10      # primitive型使用の最大比率（10%）

# エラー条件（これらを超えるとエラー扱い）
error_conditions = [
    "level2_ratio < 0.50",
    "primitive_usage > 0.10",
]

# 深刻度レベル
severity_levels = { error = "エラー", warning = "警告", advice = "アドバイス" }

# 改善プランのガイダンス（テンプレート）
[tool.pylay.quality_check.guidance]
primitive_usage = """
primitive型 {primitive_type} をドメイン型に置き換える手順:

Step 1: src/core/schemas/types.py に型定義を作成

  # Level 2: NewType + Annotated（推奨）
  from typing import NewType, Annotated
  from pydantic import Field

  {TypeName} = NewType('{TypeName}', Annotated[{primitive_type}, Field(...)])

Step 2: 使用箇所を修正

  from src.core.schemas.types import {TypeName}

  # Before
  def process(value: {primitive_type}) -> {primitive_type}:
      ...

  # After
  def process(value: {TypeName}) -> {TypeName}:
      ...
"""
```

## 出力例

### 基本出力（コンソール）

```
────────────────────────────────────────────────────────────────────────────────
  Type Quality Check
────────────────────────────────────────────────────────────────────────────────

Target:              src/core/analyzer/
Config:              pyproject.toml
Format:              console
Strict Mode:         Off
Quality Check:       Enabled

────────────────────────────────────────────────────────────────────────────────


  Summary
────────────────────────────────────────────────────────────────────────────────

Overall Score:       0.72/1.0
Total Issues:        8
Errors:              2
Warnings:            4
Advice:              2


  Statistics
────────────────────────────────────────────────────────────────────────────────

Metric                    Value      Threshold    Status
────────────────────────────────────────────────────────────────────────────────
Level 1 Ratio            18.5%      max 15.0%     OVER
Level 2 Ratio            42.3%      min 50.0%     UNDER
Level 3 Ratio            22.1%      min 20.0%     OK
Documentation Rate       68.2%      min 70.0%     UNDER
Primitive Usage          12.4%      max 10.0%     OVER


  ERROR (2 issues)
────────────────────────────────────────────────────────────────────────────────

Issue Type                Message
────────────────────────────────────────────────────────────────────────────────
level2_ratio_low          Level 2制約付き型の比率が42.3%と低すぎます
                          （下限: 50.0%）

Suggestion:               バリデーションが必要な型をLevel 2に昇格してください

Improvement Plan:
  Level 1型エイリアスをLevel 2に昇格する手順:

  1. 制約が必要な型を特定
     - 値の範囲制限が必要な型（年齢、個数など）
     - 形式チェックが必要な型（メール、URL など）
     - 存在確認が必要な型（ファイルパス、IDなど）

  2. src/core/schemas/types.py で型定義を更新

     from typing import NewType, Annotated
     from pydantic import Field, AfterValidator

     # Pattern A: Field（宣言的制約）
     Count = NewType('Count', Annotated[int, Field(ge=0)])

     # Pattern B: AfterValidator（カスタムロジック）
     def validate_email(v: str) -> str:
         if "@" not in v:
             raise ValueError("無効なメールアドレス")
         return v

     Email = NewType('Email', Annotated[str, AfterValidator(validate_email)])

  参考: docs/typing-rule.md の Level 2 定義パターン

────────────────────────────────────────────────────────────────────────────────

primitive_usage_high      primitive型の直接使用が12.4%と多すぎます

Suggestion:               ドメイン型を定義して置き換えてください

Improvement Plan:
  primitive型をドメイン型に置き換える手順:

  1. src/core/schemas/types.py で型定義を作成

     # Level 2: NewType + Annotated（推奨）
     from typing import NewType, Annotated
     from pydantic import Field

     YourTypeName = NewType('YourTypeName', Annotated[str, Field(...)])

  2. 使用箇所でインポートして使用

     from src.core.schemas.types import YourTypeName

     # Before
     def process(value: str) -> str:
         ...

     # After
     def process(value: YourTypeName) -> YourTypeName:
         ...

  3. 型名の命名規則
     - ドメイン概念を反映（UserId, EmailAddress, FilePath など）
     - PascalCase で命名
     - 用途が明確な名前を使用

  参考:
  - docs/typing-rule.md - 型定義の原則
  - src/core/schemas/types.py - 既存の型定義例


  Recommendations
────────────────────────────────────────────────────────────────────────────────

Priority Actions:
  1. ERROR項目を最優先で修正してください
     - エラーは型定義の品質に深刻な影響を及ぼします
     - CI/CDでエラーが発生した場合、ビルドが失敗する可能性があります

  2. WARNING項目も可能な限り修正することを推奨します
     - 警告は品質低下の兆候です
     - 長期的に見て型安全性が損なわれる可能性があります

  3. ADVICE項目は品質向上のための参考情報として活用してください
     - ベストプラクティスに基づく推奨事項です
     - 段階的に適用することを検討してください

────────────────────────────────────────────────────────────────────────────────
```

### 詳細表示モード（--show-details）

```
────────────────────────────────────────────────────────────────────────────────
  ERROR: primitive_usage_high
────────────────────────────────────────────────────────────────────────────────

Location:                src/core/analyzer/type_classifier.py:45:12

Context:
────────────────────────────────────────────────────────────────────────────────
43   def classify_type(self, type_def: TypeDefinition) -> str:
44       """型定義を分類"""
45       type_name: str = type_def.name
46       if isinstance(type_def, TypeAlias):
47           return "level1"

Problem:                 primitive型 str が直接使用されています
Suggestion:              ドメイン型を定義して使用してください

Improvement Plan:
────────────────────────────────────────────────────────────────────────────────

Step 1: src/core/schemas/types.py に型定義を作成

  型名の候補（コードから推測）:
  - TypeName（type_def.name から推測）
  - TypeIdentifier
  - DefinitionName

  # Level 2: NewType + Annotated（推奨）
  from typing import NewType, Annotated
  from pydantic import AfterValidator, Field

  def validate_type_name(v: str) -> str:
      # Pythonの識別子チェック
      if not v.isidentifier():
          raise ValueError("型名はPython識別子である必要があります")
      if not v:
          raise ValueError("型名は空にできません")
      return v

  TypeName = NewType('TypeName', Annotated[str, AfterValidator(validate_type_name)])

Step 2: 使用箇所を修正

  File: src/core/analyzer/type_classifier.py

  # インポート追加
  from src.core.schemas.types import TypeName

  # Before (line 45)
  type_name: str = type_def.name

  # After
  type_name: TypeName = type_def.name

Step 3: バリデーションの検討

  この型に必要な制約を検討してください:
  - [ ] 空文字チェック
  - [ ] 形式チェック（識別子、メール、URL など）
  - [ ] 長さ制限
  - [ ] 許可リスト/拒否リスト
  - [ ] 既存データとの整合性チェック

Implementation Context:
  - Why: primitive型の直接使用は型の意図を不明確にします
  - Effect: 型名により「何の文字列か」が明確になります
  - Impact: TypeNameを使う全ての箇所で型安全性が向上します

Tools and References:
  - Pydantic Field/AfterValidator - バリデーション実装
  - typing.NewType + Annotated - 型レベル区別
  - docs/typing-rule.md - 型定義ルール
  - src/core/schemas/types.py - 既存の型定義例

Related Files:
  - src/core/analyzer/type_classifier.py:45 - 修正対象
  - src/core/schemas/types.py - 型定義を追加

────────────────────────────────────────────────────────────────────────────────
```

## CI/CD統合

### GitHub Actionsでの使用例

```yaml
name: Type Quality Check

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main, develop]

jobs:
  quality-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          pip install uv
          uv sync

      - name: Run quality check
        run: |
          uv run pylay quality --strict --format markdown --output quality-report.md src/

      - name: Upload quality report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: quality-report
          path: quality-report.md

      - name: Comment PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('quality-report.md', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: report
            });
```

### pre-commitフックとしての使用

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pylay-quality-check
        name: pylay quality check
        entry: uv run pylay quality --strict
        language: system
        types: [python]
        pass_filenames: false
```

## 型定義方針（2025-10-06更新）

品質チェック機能で推奨される型定義パターン：

### Level 2: NewType + Annotated（最頻出パターン）

#### Pattern A: Field（宣言的制約）

```python
from typing import NewType, Annotated
from pydantic import Field

Count = NewType('Count', Annotated[int, Field(ge=0)])
UserId = NewType('UserId', Annotated[str, Field(min_length=8, max_length=20)])
Email = NewType('Email', Annotated[str, Field(pattern=r'^[a-zA-Z0-9._%+-]+@.*')])
```

#### Pattern B: AfterValidator（カスタムロジック）

```python
from typing import NewType, Annotated
from pydantic import AfterValidator

def validate_module_name(v: str) -> str:
    if not v.islower():
        raise ValueError("モジュール名は小文字のみで構成してください")
    if not v.replace("_", "").isalnum():
        raise ValueError("モジュール名は英数字とアンダースコアのみです")
    return v

ModuleName = NewType('ModuleName', Annotated[str, AfterValidator(validate_module_name)])
```

#### Pattern C: Field + AfterValidator（併用）

```python
from typing import NewType, Annotated
from pydantic import Field, AfterValidator

def validate_port_range(v: int) -> int:
    if 0 < v < 1024:
        raise ValueError(f"ポート {v} は予約されています（1-1023）")
    return v

Port = NewType('Port', Annotated[int, Field(ge=1, le=65535), AfterValidator(validate_port_range)])
```

### Level 3: dataclass + Pydantic

**Pattern A: 不変値オブジェクト**
```python
from dataclasses import dataclass
from pydantic import Field

@dataclass(frozen=True)
class CodeLocation:
    file: str = Field(min_length=1)
    line: int = Field(ge=1)
    column: int = Field(ge=0, default=0)
```

**Pattern B: 複雑なドメインモデル**
```python
from pydantic import BaseModel, Field, model_validator

class ModuleAnalysisResult(BaseModel):
    module_name: ModuleName
    total_lines: int = Field(ge=0)
    code_lines: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_line_counts(self) -> "ModuleAnalysisResult":
        if self.total_lines < self.code_lines:
            raise ValueError("行数の整合性エラー")
        return self
```

## 設計思想

1. **型安全性が最優先**: mypy/pyrightによる静的解析で問題を検出
2. **NewTypeの役割**: 型チェッカーでプリミティブ型を区別
3. **Annotatedの役割**: ランタイムバリデーション（補助的保証）
4. **テンプレートベース**: LLM不要で実用的な改善提案

## 関連ドキュメント

- [型定義ルール (docs/typing-rule.md)](../typing-rule.md) - 型定義の詳細な原則
- [型レベル分析詳細 (type-analysis-details.md)](type-analysis-details.md) - 問題検出の詳細
- [type: ignore診断 (diagnose-type-ignore.md)](diagnose-type-ignore.md) - 型無視の原因診断

## 実装状況

- ✅ 基本的な品質チェック機能
- ✅ 型レベル分析と統計
- ✅ 問題検出と分類（ERROR/WARNING/ADVICE）
- ✅ 改善プランのテンプレート生成
- ✅ コンソール/Markdown/JSON出力
- 🚧 詳細なコードロケーション表示（Issue #45で実装予定）
- 🚧 シンタックスハイライト付きコード表示（Issue #45で実装予定）
- 🚧 型名候補のヒューリスティック推測（Issue #45で実装予定）

最新の実装状況は [GitHub Issue #45](https://github.com/biwakonbu/pylay/issues/45) を参照してください。
