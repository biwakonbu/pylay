# クリーン再生成ガイド

このガイドでは、pylayのクリーン再生成機能の使い方と、安全な運用方法を説明します。

## 目次

- [概要](#概要)
- [基本概念](#基本概念)
- [使用方法](#使用方法)
- [安全性の仕組み](#安全性の仕組み)
- [ベストプラクティス](#ベストプラクティス)
- [トラブルシューティング](#トラブルシューティング)

## 概要

### クリーン再生成とは

クリーン再生成は、古い `.lay.*` ファイルを削除してから新しいファイルを生成する機能です。

**目的**:

- 古い型定義ファイルの削除
- ファイル名変更の追跡
- 一貫性のある型定義の維持

**Django ORM**の`makemigrations`や**Rails**の`db:migrate:reset`と同様の概念です。

### いつ使うべきか

クリーン再生成は以下の状況で使用します：

1. **型定義ファイル名を変更したとき**

   ```text
   old_types.lay.py → new_types.lay.py
   # old_types.lay.pyは削除されるべき
   ```

2. **複数の型定義を統合したとき**

   ```text
   user.lay.py + profile.lay.py → user_profile.lay.py
   # user.lay.pyとprofile.lay.pyは削除されるべき
   ```

3. **プロジェクト構造を大幅に変更したとき**

   ```text
   src/models/ → src/core/models/
   # 古いsrc/models/*.lay.pyは削除されるべき
   ```

## 基本概念

### 1. 警告ヘッダーによる判定

クリーン再生成は、ファイル内容を解析して安全性を確保します。

#### pylay生成ファイル（削除対象）

```python
"""
====================================
pylay自動生成ファイル
このファイルを直接編集しないでください
次回の pylay types 実行時に削除・再生成されます
====================================
...
"""
```

**判定基準**:

- `"pylay自動生成ファイル"` が含まれる
- `"このファイルを直接編集しないでください"` が含まれる

#### 手動実装ファイル（保護対象）

```python
"""User models for the application"""
from pydantic import BaseModel

class User(BaseModel):
    name: str
```

**判定基準**:

- 警告ヘッダーが**ない**
- → 手動実装ファイルとみなし、削除しない

### 2. 削除範囲

#### ディレクトリ単位

```python
clean_lay_files(target_dir, ".lay.py")
# → target_dir直下の.lay.pyファイルのみ削除
```

#### 再帰的削除

```python
clean_lay_files_recursive(target_dir, ".lay.py")
# → target_dirとすべてのサブディレクトリの.lay.pyファイルを削除
```

## 使用方法

### 基本的な使い方

#### 1. 単一ディレクトリのクリーンアップ

```python
from pathlib import Path
from src.core.converters.clean_regeneration import clean_lay_files

output_dir = Path("src/generated")
deleted_files = clean_lay_files(output_dir, ".lay.py")

print(f"削除されたファイル: {len(deleted_files)}個")
for file in deleted_files:
    print(f"  - {file}")
```

**出力例**:

```text
削除されたファイル: 3個
  - src/generated/old_types.lay.py
  - src/generated/deprecated.lay.py
  - src/generated/temp.lay.py
```

#### 2. 再帰的クリーンアップ

```python
from pathlib import Path
from src.core.converters.clean_regeneration import clean_lay_files_recursive

project_root = Path("src")
deleted_files = clean_lay_files_recursive(project_root, ".lay.py")

print(f"削除されたファイル: {len(deleted_files)}個")
```

**ディレクトリ構造**:

```text
src/
├── models.py              # 保護（手動実装）
├── types.lay.py          # 削除
└── core/
    ├── api.py            # 保護（手動実装）
    └── schemas.lay.py    # 削除
```

#### 3. .lay.yamlファイルのクリーンアップ

```python
from pathlib import Path
from src.core.converters.clean_regeneration import clean_lay_files

docs_dir = Path("docs/pylay")
deleted_files = clean_lay_files(docs_dir, ".lay.yaml")

print(f"削除されたYAMLファイル: {len(deleted_files)}個")
```

### 実践的なワークフロー

#### パターン1: 型定義の再生成

```python
from pathlib import Path
from src.core.converters.clean_regeneration import clean_lay_files
import subprocess

# ステップ1: 古い型定義を削除
output_dir = Path("src/generated")
deleted = clean_lay_files(output_dir, ".lay.py")
print(f"古いファイル削除: {len(deleted)}個")

# ステップ2: 新しい型定義を生成
subprocess.run([
    "uv", "run", "pylay", "types",
    "specs/api.yaml",
    "-o", "src/generated/types"
])

print("型定義の再生成完了")
```

#### パターン2: プロジェクト全体のクリーンアップ

```python
from pathlib import Path
from src.core.converters.clean_regeneration import (
    clean_lay_files_recursive,
    is_lay_generated_file
)

project_root = Path(".")

# ステップ1: 削除対象ファイルのプレビュー
print("削除対象ファイル:")
for py_file in project_root.rglob("*.lay.py"):
    if is_lay_generated_file(py_file):
        print(f"  - {py_file}")

# ステップ2: ユーザー確認
confirm = input("削除しますか？ (y/N): ")
if confirm.lower() == "y":
    deleted = clean_lay_files_recursive(project_root, ".lay.py")
    print(f"削除完了: {len(deleted)}個")
else:
    print("キャンセルしました")
```

#### パターン3: CI/CDでの自動クリーンアップ

```python
# scripts/clean_and_regenerate.py
from pathlib import Path
from src.core.converters.clean_regeneration import clean_lay_files_recursive
import subprocess
import sys

def main():
    # ステップ1: クリーンアップ
    src_dir = Path("src")
    deleted_py = clean_lay_files_recursive(src_dir, ".lay.py")

    docs_dir = Path("docs/pylay")
    deleted_yaml = clean_lay_files_recursive(docs_dir, ".lay.yaml")

    print(f"削除: {len(deleted_py)} .lay.py, {len(deleted_yaml)} .lay.yaml")

    # ステップ2: 再生成
    result = subprocess.run([
        "uv", "run", "pylay", "yaml",
        "src/models.py",
        "-o", "docs/pylay/models"
    ])

    if result.returncode != 0:
        print("エラー: 型定義の再生成に失敗しました")
        sys.exit(1)

    print("成功: クリーン再生成完了")

if __name__ == "__main__":
    main()
```

**CI設定例**:

```yaml
# .github/workflows/regenerate-types.yml
name: Regenerate Types

on:
  push:
    paths:
      - 'src/models.py'
      - 'specs/*.yaml'

jobs:
  regenerate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Clean and regenerate
        run: uv run python scripts/clean_and_regenerate.py

      - name: Commit changes
        run: |
          git add docs/pylay/
          git commit -m "chore: regenerate type definitions"
          git push
```

## 安全性の仕組み

### 1. 多層防御

クリーン再生成は複数の安全装置を持っています：

#### 第1層: 警告ヘッダーチェック

```python
def is_lay_generated_file(file_path: Path) -> bool:
    content = file_path.read_text()

    # 両方のキーワードが必要
    return (
        "pylay自動生成ファイル" in content
        and "このファイルを直接編集しないでください" in content
    )
```

#### 第2層: 拡張子チェック

```python
# .lay.py ファイルのみ対象
for file_path in target_dir.glob("*.lay.py"):
    if is_lay_generated_file(file_path):
        file_path.unlink()
```

#### 第3層: 例外処理

```python
try:
    file_path.unlink()
    deleted_files.append(file_path)
except OSError:
    # 削除に失敗した場合はスキップ
    pass
```

### 2. 保護される条件

以下のファイルは**絶対に削除されません**：

1. **警告ヘッダーがないファイル**

   ```python
   # models.py（手動実装）
   from pydantic import BaseModel

   class User(BaseModel):
       name: str
   ```

2. **拡張子が一致しないファイル**

   ```python
   # api.py（.lay.py ではない）
   from fastapi import FastAPI
   ```

3. **読み込みエラーが発生したファイル**

   ```python
   # バイナリファイル、アクセス権限エラー等
   ```

### 3. テストによる品質保証

```python
# tests/test_clean_regeneration.py より

def test_manual_files_are_not_deleted(tmp_path: Path):
    """手動実装ファイルが保護されることを確認"""

    # 手動実装ファイルを作成
    manual_file = tmp_path / "models.py"
    manual_file.write_text("# manual implementation")

    # pylay生成ファイルを作成
    lay_file = tmp_path / "types.lay.py"
    lay_file.write_text(
        '"""\npylay自動生成ファイル\n'
        'このファイルを直接編集しないでください\n"""'
    )

    # クリーン再生成実行
    deleted = clean_lay_files(tmp_path, ".lay.py")

    # 検証
    assert len(deleted) == 1
    assert not lay_file.exists()     # pylay生成ファイルは削除
    assert manual_file.exists()      # 手動実装ファイルは保護
```

## ベストプラクティス

### 1. プレビュー機能の実装

削除前にファイルリストを表示：

```python
from pathlib import Path
from src.core.converters.clean_regeneration import is_lay_generated_file

def preview_clean(target_dir: Path, suffix: str) -> list[Path]:
    """削除対象ファイルをプレビュー"""
    files_to_delete = []

    for file_path in target_dir.rglob(f"*{suffix}"):
        if is_lay_generated_file(file_path):
            files_to_delete.append(file_path)

    return files_to_delete

# 使用例
output_dir = Path("src/generated")
files = preview_clean(output_dir, ".lay.py")

print(f"削除対象: {len(files)}個")
for file in files:
    print(f"  - {file}")

confirm = input("削除しますか？ (y/N): ")
if confirm.lower() == "y":
    deleted = clean_lay_files(output_dir, ".lay.py")
    print(f"削除完了: {len(deleted)}個")
```

### 2. ログ記録

削除操作をログに記録：

```python
import logging
from pathlib import Path
from src.core.converters.clean_regeneration import clean_lay_files

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def clean_with_logging(target_dir: Path, suffix: str) -> list[Path]:
    """ログ付きクリーンアップ"""
    logger.info(f"クリーンアップ開始: {target_dir}, suffix={suffix}")

    deleted_files = clean_lay_files(target_dir, suffix)

    logger.info(f"削除完了: {len(deleted_files)}個")
    for file in deleted_files:
        logger.debug(f"削除: {file}")

    return deleted_files

# 使用例
output_dir = Path("src/generated")
deleted = clean_with_logging(output_dir, ".lay.py")
```

### 3. バックアップ作成

重要なプロジェクトでは削除前にバックアップ：

```python
import shutil
from datetime import datetime
from pathlib import Path
from src.core.converters.clean_regeneration import clean_lay_files

def clean_with_backup(target_dir: Path, suffix: str) -> tuple[list[Path], Path]:
    """バックアップ付きクリーンアップ"""

    # バックアップディレクトリを作成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"backups/lay_files_{timestamp}")
    backup_dir.mkdir(parents=True, exist_ok=True)

    # 削除対象ファイルをバックアップ
    for file_path in target_dir.rglob(f"*{suffix}"):
        if is_lay_generated_file(file_path):
            rel_path = file_path.relative_to(target_dir)
            backup_path = backup_dir / rel_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, backup_path)

    # クリーンアップ実行
    deleted_files = clean_lay_files(target_dir, suffix)

    print(f"バックアップ: {backup_dir}")
    print(f"削除: {len(deleted_files)}個")

    return deleted_files, backup_dir

# 使用例
output_dir = Path("src/generated")
deleted, backup = clean_with_backup(output_dir, ".lay.py")
```

### 4. ドライラン（dry-run）モード

実際には削除せずにシミュレーション：

```python
from pathlib import Path
from src.core.converters.clean_regeneration import is_lay_generated_file

def dry_run_clean(target_dir: Path, suffix: str) -> list[Path]:
    """ドライラン: 削除対象ファイルを表示するのみ"""
    files_to_delete = []

    for file_path in target_dir.rglob(f"*{suffix}"):
        if is_lay_generated_file(file_path):
            files_to_delete.append(file_path)
            print(f"[DRY RUN] 削除対象: {file_path}")

    print(f"\n合計: {len(files_to_delete)}個のファイルが削除されます")
    return files_to_delete

# 使用例
output_dir = Path("src/generated")
files = dry_run_clean(output_dir, ".lay.py")
```

## トラブルシューティング

### Q1: 手動実装ファイルが誤って削除された

**A**: 警告ヘッダーが含まれていた可能性があります。

**確認方法**:

```bash
# Gitで復元
git checkout HEAD -- src/models.py

# ファイル内容を確認
cat src/models.py | head -20
```

**予防策**:

- 手動実装ファイルには警告ヘッダーを書かない
- バックアップ機能を使用

### Q2: 削除されるべきファイルが残っている

**A**: 警告ヘッダーがない、または形式が不正です。

**確認方法**:

```python
from pathlib import Path
from src.core.converters.clean_regeneration import is_lay_generated_file

file_path = Path("src/generated/types.lay.py")
is_generated = is_lay_generated_file(file_path)

print(f"pylay生成ファイル: {is_generated}")

# ファイル内容を確認
with open(file_path) as f:
    print(f.read()[:500])
```

**解決策**:

- `pylay` コマンドで再生成し、警告ヘッダーを追加
- 手動で削除

### Q3: 削除処理が失敗する

**A**: ファイルアクセス権限またはファイルが使用中の可能性があります。

**確認方法**:

```bash
# ファイル権限を確認
ls -la src/generated/types.lay.py

# ファイルを使用しているプロセスを確認
lsof src/generated/types.lay.py
```

**解決策**:

```bash
# 権限を変更
chmod 644 src/generated/types.lay.py

# ファイルを使用しているプロセスを終了
```

### Q4: すべてのファイルが削除されてしまった

**A**: 再帰的削除を使用した可能性があります。

**復元方法**:

```bash
# Gitで復元
git checkout HEAD -- src/

# 特定のファイルのみ復元
git checkout HEAD -- src/models.py
```

**予防策**:

- `clean_lay_files()` を使用（再帰的ではない）
- ドライランで確認
- バックアップを作成

## 関連ドキュメント

- [.lay.* ファイルワークフロー](./lay-file-workflow.md)
- [型定義ルール](../typing-rule.md)
- [開発ガイドライン](../../AGENTS.md)

---

🤖 このガイドはpylayプロジェクトの一部です。
