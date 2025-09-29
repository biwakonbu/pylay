# pylay
Python の type hint と docstrings を利用した types <-> docs 間の透過的なジェネレータ

[![PyPI version](https://img.shields.io/pypi/v/pylay.svg)](https://pypi.org/project/pylay/)
[![Python version](https://img.shields.io/pypi/pyversions/pylay.svg)](https://pypi.org/project/pylay/)
[![License](https://img.shields.io/pypi/l/pylay.svg)](https://github.com/biwakonbu/pylay/blob/main/LICENSE)

## プロジェクト概要

**pylay** は、Pythonの型ヒント（type hint）とdocstringsを活用して、型情報（types）とドキュメント（docs）間の自動変換を実現するツールです。主な目的は、Pythonの型をYAML形式の仕様に変換し、PydanticによるバリデーションやMarkdownドキュメントの生成を容易にすることです。

### 主な機能
- Pythonの型オブジェクトをYAML形式の型仕様に変換
- YAML型仕様からPydantic BaseModelとしてパース・バリデーション
- YAML型仕様からMarkdownドキュメントを自動生成
- 型推論と依存関係抽出（mypy + ASTハイブリッド）
- 型 <-> YAML <-> 型 <-> Markdownのラウンドトリップ変換
- **プロジェクト全体解析**（pyproject.toml設定駆動）

### 対象ユーザー
- 型安全性を重視するPython開発者
- ドキュメントの自動生成を求めるチーム
- PydanticやYAMLを活用した型仕様管理が必要なアプリケーション開発者

## インストール

### pip 経由のインストール
```bash
pip install pylay
```

### オプション機能のインストール

視覚化機能を使用する場合:
```bash
pip install pylay[viz]  # matplotlibとnetworkxを追加
```

## 設定ファイル（pyproject.toml）

pylay は `pyproject.toml` の `[tool.pylay]` セクションで設定を管理できます：

```toml
[tool.pylay]
# 解析対象ディレクトリ
target_dirs = ["src/"]

# 出力ディレクトリ
output_dir = "docs/"

# ドキュメント生成フラグ
generate_markdown = true

# 依存関係抽出フラグ
extract_deps = true

# 型推論レベル
infer_level = "strict"

# 除外パターン
exclude_patterns = [
    "**/tests/**",
    "**/*_test.py",
    "**/__pycache__/**",
]

# 最大解析深度
max_depth = 10
```

## CLI ツール使用例

pylay を CLI ツールとして使用できます：

### 型ドキュメント生成
```bash
# Python ファイルからMarkdownドキュメントを生成
pylay generate type-docs --input src/core/schemas/yaml_type_spec.py --output docs/types.md

# YAML ファイルからMarkdownドキュメントを生成
pylay generate yaml-docs --input examples/sample_types.yaml --output docs/pylay-types/documents/yaml_docs.md

# テストカタログを生成
pylay generate test-catalog --input tests/ --output docs/test_catalog.md

# 依存関係グラフを生成（matplotlibが必要）
pylay generate dependency-graph --input src/ --output docs/dependency_graph.png
```

### 型解析と変換
```bash
# モジュールから型を解析してYAML出力
pylay analyze types --input src/core/schemas/yaml_type_spec.py --output-yaml types.yaml

# mypyによる型推論を実行
pylay analyze types --input src/core/schemas/yaml_type_spec.py --infer

# Python型をYAMLに変換
pylay convert to-yaml --input src/core/schemas/yaml_type_spec.py --output types.yaml

# YAMLをPydantic BaseModelに変換
pylay convert to-type --input types.yaml --output-py model.py
```

### プロジェクト全体解析
```bash
# pyproject.toml設定に基づいてプロジェクト全体を解析
pylay project project-analyze

# 設定ファイルを指定して解析
pylay project project-analyze --config-path /path/to/pyproject.toml

# 実際の処理を行わず、解析対象ファイルのみ表示（dry-run）
pylay project project-analyze --dry-run

# 詳細なログを出力
pylay project project-analyze --verbose
```

### ヘルプの表示
```bash
# 全体のヘルプ
pylay --help

# サブコマンドのヘルプ
pylay generate --help
pylay analyze --help
pylay convert --help
```

## pylay による自己解析結果

pylayプロジェクトは自らのツールを使って自己解析を行っています：

### 📊 プロジェクト構造
- **解析済みファイル**: 44個
- **抽出されたクラス**: 12個
- **抽出された関数**: 89個
- **抽出された変数**: 5個

### 🏗️ 主要コンポーネント
- **PylayCLI**: CLIツールのメインクラス
- **NetworkXGraphAdapter**: 依存関係グラフ処理
- **RefResolver**: 参照解決と循環参照検出
- **型変換システム**: YAML ↔ Python型変換
- **ProjectScanner**: プロジェクト全体解析

### 📁 生成されたドキュメント
pylayは自らのプロジェクトを解析し、`docs/pylay-types/`ディレクトリに以下のファイルを生成しています：

- 各Pythonファイルの型情報（`*_types.yaml`）
- 依存関係グラフ
- テストカタログ
- APIドキュメント

```bash
# pylayプロジェクトを解析
pylay project project-analyze

# 解析結果を確認
find docs/pylay-types -name "*.yaml" | wc -l
ls docs/pylay-types/src/
```

## 開発者向けドキュメント

このプロジェクトを開発・貢献したい場合は、[AGENTS.md](AGENTS.md) と [PRD.md](PRD.md) を参照してください。

## 参考資料

- [Pydantic ドキュメント](https://docs.pydantic.dev/)
- [Python 型付け](https://docs.python.org/3/library/typing.html)
- [mypy ドキュメント](https://mypy.readthedocs.io/en/stable/)
