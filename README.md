# pylay
Python の type hint と docstrings を利用した types <-> docs 間の透過的なジェネレータ

## 開発環境セットアップ

### 必要なツール

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (推奨) または [Poetry](https://python-poetry.org/)
- [pre-commit](https://pre-commit.com/)

### セットアップ

```bash
# 依存関係をインストール
make install
# または
uv sync

# pre-commitフックをインストール
make pre-commit-install
# または
uv run pre-commit install
```

## 開発コマンド

### 品質チェックとテスト

```bash
# すべてのチェックを実行（推奨）
make all-check

# 個別のチェック
make format          # コードフォーマット
make type-check      # 型チェック（mypy）
make lint           # リンター（Ruff）
make test           # テスト実行
make quality-check  # 品質チェック（mypy + Ruff + pre-commit）
make coverage       # カバレッジレポートを開く

# 高速テスト（カバレッジなし）
make test-fast

# 追加のチェック
make safety-check    # 依存関係のセキュリティチェック
make radon-check     # コード複雑度チェック
make interrogate-check  # docstringカバレッジチェック
```

### VSCode での実行

VSCode を使用している場合、以下のタスクが利用可能です：

- **Format: All** - コードのフォーマット
- **Quality: Check** - 品質チェック（mypy + Ruff + pre-commit）
- **Test: Run** - テスト実行（デフォルトのテストタスク）
- **All: Check** - すべてのチェックを実行
- **MyPy: Check** - 型チェックのみ
- **Ruff: Check** - リンターのみ
- **Pre-commit: Run** - pre-commitチェックのみ

### CI/CD

```bash
# CIで実行する全チェック
make ci
```

### クリーンアップ

```bash
make clean  # キャッシュと一時ファイルを削除
```

## プロジェクト構造

```
pylay/
├── src/                    # ソースコード
│   ├── converters/        # 型変換機能
│   ├── schemas/          # 型定義
│   └── ...
├── tests/                 # テストコード
├── docs/                  # ドキュメント
├── .pre-commit-config.yaml # pre-commit設定
├── pyproject.toml         # プロジェクト設定
├── mypy.ini              # mypy設定
└── Makefile              # 開発コマンド
```
