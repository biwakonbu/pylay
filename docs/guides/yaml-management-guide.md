# プロジェクト全体のYAML管理ガイド

このガイドでは、pylayを使用してプロジェクト全体の型定義をYAML形式で管理する方法を説明します。

## 目次

- [概要](#概要)
- [基本的な使い方](#基本的な使い方)
- [ディレクトリ構造の管理](#ディレクトリ構造の管理)
- [Git統合](#git統合)
- [チーム開発での運用](#チーム開発での運用)
- [ベストプラクティス](#ベストプラクティス)
- [トラブルシューティング](#トラブルシューティング)

## 概要

pylayの `pylay yaml` コマンドは、プロジェクト全体の型定義をYAML形式に変換し、バージョン管理できるようにします。

### なぜYAML管理が必要か？

1. **型定義の可視化**: Python型定義をYAML形式で表現し、レビューしやすくする
2. **変更履歴の追跡**: Gitで型定義の変更履歴を追跡できる
3. **ドキュメント生成**: YAMLからMarkdownドキュメントを自動生成
4. **型の再生成**: YAMLからPython型定義を再生成可能（ラウンドトリップ変換）

### YAML管理の基本方針

- **`.lay.yaml`ファイルはGit管理対象**: 型仕様の変更履歴を追跡
- **`.lay.py`ファイルは除外**: 自動生成されるため、Gitで管理しない
- **ディレクトリ構造を保持**: `docs/pylay/` 配下にソース構造をミラーリング

## 基本的な使い方

### 単一ファイルの変換

```bash
# 特定のファイルをYAMLに変換
uv run pylay yaml src/core/schemas/types.py

# 出力先が自動生成される:
#   docs/pylay/src/core/schemas/types.lay.yaml
```

### ディレクトリの再帰的変換

```bash
# ディレクトリ全体を再帰的にYAML化（構造を保持）
uv run pylay yaml src/core/schemas/

# 出力構造:
#   docs/pylay/src/core/schemas/
#   ├── types.lay.yaml
#   ├── graph.lay.yaml
#   └── pylay_config.lay.yaml
```

### プロジェクト全体の変換（推奨）

```bash
# pyproject.tomlの設定に基づいてプロジェクト全体を変換
uv run pylay yaml

# pyproject.toml設定例:
# [tool.pylay]
# target_dirs = ["src/core", "src/cli"]
# output_dir = "docs/pylay"
```

## ディレクトリ構造の管理

### 構造の保持

`pylay yaml` コマンドは、ソースディレクトリの構造を `docs/pylay/` 配下にミラーリングします。

**例**:

```
プロジェクト構造:
src/
├── core/
│   ├── schemas/
│   │   ├── types.py
│   │   └── graph.py
│   ├── converters/
│   │   └── type_to_yaml.py
│   └── analyzer/
│       └── type_inferrer.py
└── cli/
    └── commands/
        └── yaml.py

↓ pylay yaml 実行後

docs/pylay/
├── src/
│   ├── core/
│   │   ├── schemas/
│   │   │   ├── types.lay.yaml
│   │   │   └── graph.lay.yaml
│   │   ├── converters/
│   │   │   └── type_to_yaml.lay.yaml
│   │   └── analyzer/
│   │       └── type_inferrer.lay.yaml
│   └── cli/
│       └── commands/
│           └── yaml.lay.yaml
```

### 出力先のカスタマイズ

```bash
# 出力先を指定する
uv run pylay yaml src/core/schemas/types.py -o custom/output/types.lay.yaml
```

### 型定義の自動検出

`pylay yaml` は以下の型定義を自動検出します:

- **BaseModel**: Pydantic BaseModelクラス
- **type文**: 型エイリアス（`type UserId = str`）
- **NewType**: NewType定義
- **dataclass**: dataclassデコレーター
- **Enum**: Enum継承クラス

**除外される**:
- テストファイル（`test_*.py`）
- `__init__.py`

## Git統合

### .gitignore設定

```gitignore
# pylay generated files in docs/pylay/
# YAML型仕様ファイル（.lay.yaml）はGit管理対象
# 自動生成されたその他のファイルは除外
docs/pylay/**/*.md
docs/pylay/**/*.json
docs/pylay/**/*.png
docs/pylay/**/*.dot
# .lay.yamlファイルは管理対象（型仕様のバージョン管理）
!docs/pylay/**/*.lay.yaml

# pylay generated files
# YAMLスキーマファイル（.lay.yaml）は管理対象に含める
# 自動生成されたPython型定義（.lay.py）は除外
*.lay.py
```

### コミット戦略

```bash
# 1. 型定義を変更（src/core/schemas/types.py）
vim src/core/schemas/types.py

# 2. YAMLを再生成
uv run pylay yaml src/core/schemas/types.py

# 3. 変更を確認
git diff docs/pylay/src/core/schemas/types.lay.yaml

# 4. 型定義とYAMLをまとめてコミット
git add src/core/schemas/types.py
git add docs/pylay/src/core/schemas/types.lay.yaml
git commit -m "feat: UserId型の制約を追加"
```

### プルリクエストでのレビュー

YAMLファイルがGit管理されているため、プルリクエストで型定義の変更を視覚的にレビューできます。

**例**: UserId型の制約追加

```diff
# docs/pylay/src/core/schemas/types.lay.yaml

 UserId:
   type: NewType
   base_type: str
+  constraints:
+    min_length: 8
+    max_length: 32
```

## チーム開発での運用

### ワークフロー

```
開発者A:
  1. 型定義を変更（types.py）
  2. YAML再生成（pylay yaml）
  3. 変更をコミット
  4. プルリクエスト作成
     ↓
レビュアーB:
  5. YAML差分を確認
  6. 型定義の妥当性をレビュー
  7. 承認/修正依頼
     ↓
開発者A:
  8. マージ
     ↓
他の開発者C:
  9. プル（git pull）
  10. 最新のYAMLを取得
  11. 必要に応じて型定義を再生成（pylay types）
```

### CI/CDでの自動チェック

```yaml
# .github/workflows/type-check.yml
name: Type Check

on: [push, pull_request]

jobs:
  type-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Install dependencies
        run: uv sync
      - name: Regenerate YAML
        run: uv run pylay yaml
      - name: Check for changes
        run: |
          if git diff --exit-code docs/pylay/; then
            echo "✅ YAML is up to date"
          else
            echo "❌ YAML is out of date. Please run 'pylay yaml' and commit."
            exit 1
          fi
```

## ベストプラクティス

### 1. 定期的なYAML再生成

型定義を変更した際は、必ずYAMLを再生成してコミットします。

```bash
# 型定義変更後、必ず実行
uv run pylay yaml

# または、プロジェクト全体
uv run pylay yaml
```

### 2. メタデータの活用

生成されたYAMLには `_metadata` セクションが含まれており、ソースファイルの情報が記録されています。

```yaml
_metadata:
  generated_by: pylay yaml
  source: src/core/schemas/types.py
  source_hash: a1b2c3d4e5f6...
  source_size: 1024
  source_modified_at: 2025-10-08T10:30:00+00:00
  generated_at: 2025-10-08T11:00:00+00:00
  pylay_version: 0.5.0
```

**活用例**:
- `source_hash`: ソースファイルが変更されたかチェック
- `source_modified_at`: 最終更新日時の追跡
- `pylay_version`: 生成に使用したpylayバージョンの記録

### 3. ディレクトリ別のYAML管理

大規模プロジェクトでは、ディレクトリ別にYAMLを管理します。

```bash
# coreモジュールのみ
uv run pylay yaml src/core/

# cliモジュールのみ
uv run pylay yaml src/cli/
```

### 4. ドキュメント生成との連携

YAMLからMarkdownドキュメントを生成します。

```bash
# YAMLからドキュメントを生成
uv run pylay docs -i docs/pylay/src/core/schemas/types.lay.yaml -o docs/api/
```

### 5. 型の再生成（ラウンドトリップ変換）

必要に応じて、YAMLからPython型定義を再生成できます。

```bash
# YAMLからPython型定義を生成（.lay.py拡張子で生成）
uv run pylay types docs/pylay/src/core/schemas/types.lay.yaml

# 生成されたファイル:
#   docs/pylay/src/core/schemas/types.lay.py
```

**注意**: `.lay.py` ファイルは参照用であり、本番コードでは元の `types.py` を使用してください。

## トラブルシューティング

### 問題1: YAMLが生成されない

**症状**:
```
ℹ️  型定義なしのためスキップ: src/core/utils/helpers.py
```

**原因**:
ファイルに型定義（BaseModel, type文, NewType, dataclass, Enum）が含まれていない

**解決策**:
```python
# helpers.pyに型定義を追加
from typing import NewType

UserId = NewType('UserId', str)
```

### 問題2: Git差分が大量に発生

**症状**:
YAMLファイルに大量の変更が発生

**原因**:
- メタデータの `generated_at` が毎回更新される
- ソースファイルが変更されていないのにYAMLが再生成された

**解決策**:
```bash
# ソースファイルが変更された場合のみYAMLを再生成
# メタデータのsource_hashで判定可能

# または、generated_atを除外して差分を確認
git diff --ignore-matching-lines='generated_at:' docs/pylay/
```

### 問題3: 型定義の検出漏れ

**症状**:
型定義があるのにYAMLが生成されない

**原因**:
検出パターンにマッチしない型定義の書き方

**解決策**:
```python
# ❌ 検出されない
from typing import NewType as NT
UserId = NT('UserId', str)

# ✅ 検出される
from typing import NewType
UserId = NewType('UserId', str)
```

### 問題4: 出力先が想定と異なる

**症状**:
YAMLが期待した場所に出力されない

**原因**:
相対パス/絶対パスの解釈が異なる

**解決策**:
```bash
# 絶対パスを使用
uv run pylay yaml /full/path/to/src/core/schemas/types.py

# または、-o オプションで明示的に指定
uv run pylay yaml src/core/schemas/types.py -o docs/pylay/custom/types.lay.yaml
```

## 運用例

### 小規模プロジェクト（1-10ファイル）

```bash
# プロジェクト全体を一括変換
uv run pylay yaml

# 定期的に実行（週1回程度）
# または、型定義変更時に手動実行
```

### 中規模プロジェクト（10-100ファイル）

```bash
# モジュール別に変換
uv run pylay yaml src/core/
uv run pylay yaml src/cli/

# CI/CDで自動チェック（PRごと）
# 変更があった場合のみコミット
```

### 大規模プロジェクト（100+ファイル）

```bash
# ディレクトリ単位で管理
uv run pylay yaml src/core/schemas/
uv run pylay yaml src/core/converters/
uv run pylay yaml src/core/analyzer/

# CI/CDで変更検出と自動再生成
# 型定義変更時のみYAML更新
```

## まとめ

YAML管理の成功基準:

- [ ] `.lay.yaml` ファイルがGit管理されている
- [ ] `.lay.py` ファイルが `.gitignore` で除外されている
- [ ] ディレクトリ構造が保持されている
- [ ] メタデータセクションが含まれている
- [ ] 型定義変更時にYAMLが再生成されている
- [ ] プルリクエストでYAML差分がレビューされている

## 関連ガイド

- [Django風パッケージ構造ガイド](./django-style-structure.md)
- [types.py作成ガイドライン](./types-creation-guide.md)
- [既存モジュールの移行手順](./migration-guide.md)

## 参考資料

- [pylay CLI リファレンス](../../README.md#cli-usage)
- [YAML型仕様フォーマット](../../docs/yaml-spec-format.md)
