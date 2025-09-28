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

### 対象ユーザー
- 型安全性を重視するPython開発者
- ドキュメントの自動生成を求めるチーム
- PydanticやYAMLを活用した型仕様管理が必要なアプリケーション開発者

## CLI ツール使用例

pylay を CLI ツールとして使用できます：

### 型ドキュメント生成
```bash
# Python ファイルからMarkdownドキュメントを生成
pylay generate type-docs --input src/core/schemas/yaml_type_spec.py --output docs/types.md

# YAML ファイルからMarkdownドキュメントを生成
pylay generate yaml-docs --input examples/sample_types.yaml --output docs/yaml_types.md

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

### ヘルプの表示
```bash
# 全体のヘルプ
pylay --help

# サブコマンドのヘルプ
pylay generate --help
pylay analyze --help
pylay convert --help
```

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

## 参考資料

- [Pydantic ドキュメント](https://docs.pydantic.dev/)
- [Python 型付け](https://docs.python.org/3/library/typing.html)
- [mypy ドキュメント](https://mypy.readthedocs.io/en/stable/)
