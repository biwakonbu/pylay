# pylay 開発者ガイド

pylayは**Pythonの型ヒントとドキュメントの自動変換**を実現するツールです。

## 🎯 プロジェクトコンセプト

### 基本理念
- **型安全性**: Pythonの型ヒントを活用した堅牢なデータ処理
- **自動化**: 型定義からドキュメントを自動生成
- **YAML中間形式**: 型情報をYAMLで表現し、相互変換を可能に

### 変換の流れ
```
Python型定義 → YAML型仕様 → Pydanticモデル → Markdownドキュメント
     ↑              ↓              ↓              ↓
   抽出        変換・検証     バリデーション     生成
```

## 🏗️ アーキテクチャ

### 主要コンポーネント
- **`src/core/converters/`**: 型変換のコア機能
  - `type_to_yaml.py`: Python型 → YAML変換
  - `yaml_to_type.py`: YAML → Python型変換
  - `infer_types.py`: mypyによる型推論
- **`src/core/doc_generators/`**: ドキュメント生成
  - `type_doc_generator.py`: 型情報からMarkdown生成
  - `yaml_doc_generator.py`: YAMLからドキュメント生成
- **`src/cli/`**: コマンドラインツール
- **`src/tui/`**: 対話型ユーザーインターフェース

### 技術スタック
- **Python 3.12+**: 最新の型ヒント機能を使用
- **Pydantic v2**: 高速なデータバリデーション
- **NetworkX**: 依存関係のグラフ表現
- **mypy**: 静的型解析と推論
- **uv**: 高速なPythonパッケージ管理

## 🚀 クイックスタート

### 環境セットアップ
```bash
# 依存関係をインストール（uv使用）
make install

# 開発準備完了
make dev
```

### 基本操作
```bash
# プロジェクト解析（自動ドキュメント生成）
make analyze

# テスト実行
make test

# 品質チェック
make quality
```

### 実行確認
```bash
# CLIツール
uv run python -m src.cli.main --help

# TUIツール
uv run python -m src.tui.main

# 型推論テスト
uv run python src/infer_deps.py src/cli/main.py
```

## 📁 プロジェクト構造

```
pylay/
├── src/                    # ソースコード
│   ├── cli/               # コマンドラインインターフェース
│   ├── core/              # コア機能
│   │   ├── converters/    # 型変換機能
│   │   ├── doc_generators/# ドキュメント生成
│   │   └── schemas/       # 型定義
│   └── tui/               # テキストユーザーインターフェース
├── tests/                 # テストコード
├── docs/                  # ドキュメント
│   ├── development/       # 開発者向けガイド
│   └── pylay-types/       # 自動生成された型情報
└── scripts/               # ユーティリティスクリプト
```

## 🔧 設定ファイル

`pyproject.toml` の `[tool.pylay]` セクションで動作を制御：

```toml
[tool.pylay]
target_dirs = ["src", "scripts", "utils"]
output_dir = "docs/pylay-types"
generate_markdown = true
clean_output_dir = true  # 自動クリーンアップ有効
```

## 🎨 使用例

### 型定義からドキュメント生成
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    """ユーザーを表すデータクラス"""
    id: int
    name: str
    email: Optional[str] = None

# これをYAMLに変換し、Markdownドキュメントを自動生成
```

### 依存関係の可視化
```bash
# プロジェクトの依存関係をグラフで表示
uv run python -c "
from src.core.converters.ast_dependency_extractor import ASTDependencyExtractor
extractor = ASTDependencyExtractor()
graph = extractor.extract_dependencies('src/cli/main.py')
print(f'依存関係: {len(graph.nodes)} ノード, {len(graph.edges)} エッジ')
"
```

## 🔍 技術的詳細

### 型推論システム
- **AST解析**: Pythonの抽象構文木を解析
- **mypy統合**: 静的型解析による型推論
- **ハイブリッド**: AST + mypyの組み合わせで高精度な型抽出

### YAML型仕様
```yaml
User:
  type: dict
  description: ユーザーを表すデータ構造
  properties:
    id:
      type: int
      description: ユーザーID
      required: true
    name:
      type: str
      description: ユーザー名
      required: true
```

### 自動ドキュメント生成
- **型情報からMarkdown**: クラス・関数の説明を自動生成
- **構造の可視化**: 依存関係のグラフ表現
- **相互変換**: 型 ↔ YAML ↔ ドキュメントの双方向変換

## 📚 参考資料

- [Python 型ヒント](https://docs.python.org/3/library/typing.html)
- [Pydantic v2](https://docs.pydantic.dev/)
- [mypy ドキュメント](https://mypy.readthedocs.io/)

---

**このプロジェクトの価値**: Pythonの型システムを活用した、保守性が高く自動化されたドキュメント生成を実現します。
