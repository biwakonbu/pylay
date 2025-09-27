# pylay
Python の type hint と docstrings を利用した types <-> docs 間の透過的なジェネレータ

## プロジェクト概要

**pylay** は、Pythonの型ヒント（type hint）とdocstringsを活用して、型情報（types）とドキュメント（docs）間の自動変換を実現するツールです。主な目的は、Pythonの型をYAML形式の仕様に変換し、PydanticによるバリデーションやMarkdownドキュメントの生成を容易にすることです。

### 主な機能
- Pythonの型オブジェクトをYAML形式の型仕様に変換
- YAML型仕様からPydantic BaseModelとしてパース・バリデーション
- YAML型仕様からMarkdownドキュメントを自動生成
- 型推論と依存関係抽出（mypy + ASTハイブリッド、開発中）
- 型 <-> YAML <-> 型 <-> Markdownのラウンドトリップ変換

### 対象ユーザー
- 型安全性を重視するPython開発者
- ドキュメントの自動生成を求めるチーム
- PydanticやYAMLを活用した型仕様管理が必要なアプリケーション開発者

### プロジェクトステータス
- **実装済み**: 型 <-> YAML 相互変換、Pydantic v2バリデーション、YAML -> Markdown生成、基本テスト
- **開発中**: 型推論と依存関係抽出
- **範囲外**: 高度なロジック処理、外部API/UI統合

詳細は [PRD.md](PRD.md) を参照してください。

## 開発環境セットアップ

### 必要なツール
- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (推奨) または [Poetry](https://python-poetry.org/)
- [pre-commit](https://pre-commit.com/)

**重要**: システムPythonの使用を避け、常に `uv run` 経由で仮想環境を使用してください。

### セットアップ手順
```bash
# 1. 依存関係をインストール（Python 3.13環境が自動作成）
make install
# または
uv sync

# 2. pre-commitフックをインストール
make pre-commit-install
# または
uv run pre-commit install
```

### VSCode設定
推奨拡張機能:
- Python (Microsoft)
- Pylint
- MyPy Type Checker
- Ruff (オプション)

## 開発コマンド

Makefileを使って開発作業を統一的に管理します。すべてのPythonコマンドは `uv run` で実行してください。

```bash
# ヘルプを表示
make help

# 依存関係インストール
make install

# コードフォーマット
make format

# リンター実行（修正適用）
make lint

# 型チェック (mypy)
make type-check

# テスト実行（カバレッジ付き）
make test

# 高速テスト（カバレッジなし）
make test-fast

# カバレッジレポート確認
make coverage

# 品質チェック（型 + リンター + pre-commit）
make quality-check

# すべてのチェック実行
make all-check

# セキュリティチェック
make safety-check

# コード複雑度チェック
make radon-check

# docstringカバレッジチェック
make interrogate-check

# CIチェック
make ci

# クリーンアップ
make clean
```

詳細は [AGENTS.md](AGENTS.md) を参照してください。

## プロジェクト構造

```
pylay/
├── src/                    # ソースコード
│   ├── converters/        # 型変換機能
│   │   ├── type_to_yaml.py    # Python型 → YAML変換
│   │   └── yaml_to_type.py    # YAML → Python型変換
│   ├── schemas/           # 型定義
│   │   └── yaml_type_spec.py  # YAML型仕様のPydanticモデル
│   ├── doc_generators/    # ドキュメント生成
│   │   ├── base.py           # 基底クラス
│   │   ├── config.py         # 設定管理
│   │   ├── filesystem.py     # ファイルシステム操作
│   │   ├── markdown_builder.py # Markdown生成
│   │   ├── type_doc_generator.py  # 型ドキュメント生成
│   │   ├── yaml_doc_generator.py  # YAMLドキュメント生成
│   │   └── test_catalog_generator.py # テストカタログ生成
│   └── generate_*.py      # エントリーポイントスクリプト
├── tests/                 # テストコード
├── docs/                  # 生成されたドキュメント
├── .vscode/               # VSCode設定
├── .pre-commit-config.yaml # pre-commit設定
├── pyproject.toml         # プロジェクト設定
├── mypy.ini              # mypy設定
├── Makefile              # 開発コマンド
└── README.md             # プロジェクト説明
```

## 技術スタック

- **言語/フレームワーク**: Python 3.13+, Pydantic v2, typing/collections.abc
- **ライブラリ**: PyYAML/ruamel.yaml, pytest, mypy, ast/NetworkX, Ruff, uv
- **ツール**: pre-commit, Makefile, VSCode

## 参考資料

- [Pydantic ドキュメント](https://docs.pydantic.dev/)
- [Python 型付け](https://docs.python.org/3/library/typing.html)
- [mypy ドキュメント](https://mypy.readthedocs.io/en/stable/)
- [AGENTS.md](AGENTS.md): 開発ガイドライン
- [PRD.md](PRD.md): 製品要件
