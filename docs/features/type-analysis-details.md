# 型レベル分析: 警告箇所の詳細表示機能

## 概要

型レベル分析で検出された問題（primitive型の使用、Level 1型の放置、使用されていない型定義など）について、該当するコードの位置（ファイルパス、行番号、カラム位置）と実際の実装内容を特定し、ユーザーに提示する機能です。

## 機能

### 1. 検出対象

以下の4種類の問題を検出し、詳細情報を提供します：

#### 1.1 Primitive型の直接使用

**対象**: 関数引数、戻り値、クラス属性で `str`, `int`, `float`, `bool` などが直接使用されている箇所

**除外**:
- `__init__`, `__str__`, `__repr__` などの特殊メソッド
- プライベートメソッド（`_`始まり）の内部実装
- テストコード内の使用

**提供情報**:
- ファイルパス、行番号、カラム位置
- 使用箇所の種類（関数引数/戻り値/クラス属性）
- 使用されているprimitive型
- 周辺コード（前後2行）

#### 1.2 Level 1型の長期放置

**対象**: `type` エイリアスとして定義されているが、制約もビジネスロジックもない型

**検出条件**:
- Level 1に分類されている
- `@target-level: level1` や `@keep-as-is: true` などのdocstringタグがない
- 参照回数が1回以上ある（実際に使用されている）

**提供情報**:
- 型定義の場所（ファイルパス、行番号）
- 型定義の内容（例: `type UserId = str`）
- 使用箇所の数
- 使用箇所の例（最大3件）
- docstring（存在する場合）
- 推奨事項

#### 1.3 被参照0の型定義

**対象**: 定義されているが、プロジェクト内で一度も使用されていない型

**除外**:
- `__all__` でエクスポートされている型（公開API）
- `@keep-as-is: true` タグがある型

**提供情報**:
- 型定義の場所（ファイルパス、行番号）
- 型定義の内容
- 型のレベル（Level 1/2/3）
- docstring（存在する場合）
- 削除推奨 or 調査推奨の判定理由

#### 1.4 非推奨typing使用

**対象**: `typing.List`, `typing.Dict`, `typing.Union`, `typing.Optional`, `typing.NewType` の使用

**推奨**: Python 3.13標準構文への移行

**提供情報**:
- ファイルパス、行番号
- 使用している非推奨型
- 推奨される代替構文
- 周辺コード（前後2行）

## 使用方法

### 基本的な使用（統計のみ）

```bash
# 統計情報と推奨事項のみ表示
uv run pylay check --focus types src/
```

### 詳細表示付き

```bash
# 統計情報 + 問題箇所の詳細テーブル
uv run pylay check --focus types src/ -v
```

**出力例**:

```text
────────────────────── 🔍 問題詳細: Primitive型の直接使用 ──────────────────────

  ファイル                   行      種類        型     コード
 ───────────────────────────────────────────────────────────────────────────────
  yaml_spec.py               20   attribute     str     ref_name: str
  yaml_spec.py              179    argument     int     def check_depth(items: list...
  types.py                   59    argument     str     def validate_index_filename...
  ...

────────────────────── 🔍 問題詳細: Level 1型の放置 ──────────────────────────────

  型定義               ファイル                     行    使用回数  推奨
 ───────────────────────────────────────────────────────────────────────────────
  type UserId = str    src/core/schemas/types.py    15    12       Level 2へ昇格
  type Email = str     src/core/schemas/types.py    18    8        Level 2へ昇格
  ...
```

### YAML出力

```bash
# 詳細情報をYAMLファイルにエクスポート
uv run pylay check --focus types src/ --output=./analysis-details.yaml
```

**YAML出力例**:

```yaml
problem_details:
  primitive_usage:
    - file: src/core/models.py
      line: 42
      column: 18
      type: function_argument
      primitive_type: str
      context:
        before:
          - "class UserService:"
          - '    """ユーザー管理サービス"""'
        code: "def process_user(user_id: str, email: str) -> dict:"
        after:
          - '    """ユーザー情報を処理"""'
          - "    return {...}"
      suggestion: |
        primitive型 'str' を使用しています。
        ドメイン型への移行を検討してください。

  level1_types:
    - type_name: UserId
      definition: "type UserId = str"
      file: src/core/schemas/types.py
      line: 15
      usage_count: 12
      docstring: "ユーザーID"
      usage_examples:
        - file: src/core/models.py
          line: 42
          context: "user_id: UserId"
          kind: function_argument
      recommendation: |
        Level 1型として定義されていますが、使用回数が12回と多いです。
        バリデーションを追加してLevel 2へ昇格させることを推奨します。

  unused_types:
    - type_name: SessionToken
      definition: "type SessionToken = str"
      file: src/core/schemas/types.py
      line: 89
      level: Level 1
      docstring: "セッショントークン（未使用）"
      reason: implementation_in_progress
      recommendation: |
        使用箇所が見つかりません。
        実装途中の場合は使用箇所を追加、不要な場合は削除を検討してください。

  deprecated_typing:
    - file: src/core/converters/type_to_yaml.py
      line: 5
      imports:
        - deprecated: List
          recommended: list
        - deprecated: Dict
          recommended: dict
      context:
        code: "from typing import List, Dict, Optional"
      suggestion: |
        Python 3.13標準構文への移行を推奨します:
        - List[str] → list[str]
        - Dict[str, int] → dict[str, int]
```

### オプション

- `-v`: 問題箇所の詳細（ファイルパス、行番号、コード内容）を表示
- `--output PATH`: 問題詳細をYAMLファイルにエクスポート
- `--no-stats`: 統計情報を非表示（詳細のみ表示）
  - 実装: [src/cli/commands/analyze_types.py:79-82](../../src/cli/commands/analyze_types.py#L79-L82)

## アーキテクチャ

### CodeLocatorクラス

問題箇所のコード位置と内容を特定するエンジンです。

**場所**: `src/core/analyzer/code_locator.py`

**主要メソッド**:

- `find_primitive_usages()`: Primitive型の直接使用箇所を検出
- `find_level1_types()`: Level 1型の詳細情報を取得
- `find_unused_types()`: 被参照0型の詳細情報を取得
- `find_deprecated_typing()`: 非推奨typing使用箇所を検出

**内部実装**:

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

@dataclass
class CodeLocation:
    """コード位置情報"""
    file: Path
    line: int
    column: int
    code: str
    context_before: list[str]
    context_after: list[str]

@dataclass
class PrimitiveUsageDetail:
    """Primitive型使用の詳細情報"""
    location: CodeLocation
    kind: Literal["function_argument", "return_type", "class_attribute"]
    primitive_type: str
    function_name: str | None = None
    class_name: str | None = None

class CodeLocator:
    """コード位置特定エンジン"""

    def __init__(self, target_dirs: list[Path]) -> None:
        self.target_dirs = target_dirs
        self._file_cache: dict[Path, list[str]] = {}

    def find_primitive_usages(self) -> list[PrimitiveUsageDetail]:
        """Primitive型の直接使用箇所を検出"""
        ...
```

### TypeReporter拡張

詳細レポートを生成・表示する機能です。

**場所**: `src/core/analyzer/type_reporter.py`

**主要メソッド**:

- `generate_detailed_report()`: 詳細レポートをコンソールに出力
- `_create_primitive_usage_table()`: Primitive型使用の詳細テーブルを生成
- `_create_level1_types_table()`: Level 1型の詳細テーブルを生成
- `_create_unused_types_table()`: 被参照0型の詳細テーブルを生成
- `_create_deprecated_typing_table()`: 非推奨typing使用の詳細テーブルを生成

### CLI統合

**場所**: `src/cli/commands/analyze_types.py`

**追加オプション**:

```python
@click.option(
    "-v",
    is_flag=True,
    default=False,
    help="問題箇所の詳細（ファイルパス、行番号、コード内容）を表示",
)
@click.option(
    "--output",
    type=click.Path(),
    default=None,
    help="問題詳細をYAMLファイルにエクスポート（指定したパスに保存）",
)
```

## パフォーマンス

### キャッシュ戦略

- ファイル内容は初回読み込み時にキャッシュ（`CodeLocator._file_cache`）
- AST解析結果は再利用（既存の `TypeInferrer` のキャッシュを活用）

### 処理順序の最適化

1. 統計情報の計算（既存）
2. 問題箇所の特定（新規、`-v`指定時のみ）
3. 詳細テーブルの生成（新規、`-v`指定時のみ）

### 大規模プロジェクト対応

- 問題数が多い場合（100件以上）は、優先度の高いもの（primitive型、Level 1放置）から最大50件表示
- YAML出力では全件出力（`--output`）

## 使用例

### 開発効率の向上

```bash
# 1. 問題箇所を特定
uv run pylay check --focus types src/ -v

# 2. 該当ファイルを直接編集
vim src/core/models.py +42

# 3. 修正後、再度分析
uv run pylay check --focus types src/ -v
```

### AI修正用

```bash
# 1. 詳細YAMLを生成
uv run pylay check --focus types src/ --output=./analysis-details.yaml

# 2. AIがYAMLを読み込んで自動修正
# （別のツールやスクリプトで実装）
```

### CI/CD統合

```bash
# プルリクエスト時に問題箇所をチェック
uv run pylay check --focus types src/ --output=./analysis.yaml

# 問題数をカウント
problem_count=$(yq '.problem_details.primitive_usage | length' analysis.yaml)
if [ "$problem_count" -gt 0 ]; then
  echo "Warning: $problem_count primitive型の使用が見つかりました"
fi
```

## 期待される効果

1. **開発効率の向上**: 問題箇所を手動で探す時間を削減
2. **修正精度の向上**: AIが正確な位置情報を基に修正可能
3. **コードレビューの効率化**: レビュー時に問題箇所を即座に確認可能
4. **学習コストの低減**: 具体例を見ながら型定義のベストプラクティスを学べる

## 関連ドキュメント

- [型定義ルール](../typing-rule.md)
- [型レベル分析・監視機能](../PRD.md#phase-5)
- [Issue #28: 型レベル分析: 警告箇所の詳細表示機能の実装](https://github.com/biwakonbu/pylay/issues/28)

## テスト

関連するテストファイル：

- `tests/test_code_locator.py`: CodeLocatorのユニットテスト
- `tests/test_analyze_types_details.py`: CLI統合テスト

```bash
# テスト実行
uv run pytest tests/test_code_locator.py tests/test_analyze_types_details.py -v
```
