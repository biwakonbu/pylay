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
- **型定義レベル分析・監視機能**（Level 1/2/3の自動分類と昇格/降格推奨）
- **ドキュメント品質分析**（docstring実装率、詳細度、総合スコア算出）
- **高度な型推論と依存関係抽出**（mypy + ASTハイブリッド + NetworkXグラフ分析）
- 型 <-> YAML <-> 型 <-> Markdownのラウンドトリップ変換
- **プロジェクト全体解析**（pyproject.toml設定駆動 + 循環依存検出）
- **疎結合アーキテクチャ**（Analyzerインターフェースで柔軟な解析モード選択）

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

### ドキュメント生成（新コマンド）
```bash
# YAMLからMarkdownドキュメントを生成（シンプル）
pylay docs
pylay docs -i examples/sample_types.yaml -o docs/api

# フォーマット指定
pylay docs -i types.yaml --format single
```

### その他のドキュメント生成（補助コマンド）
```bash
# Python ファイルからMarkdownドキュメントを生成
pylay generate type-docs --input src/core/schemas/yaml_type_spec.py --output docs/types.md

# テストカタログを生成
pylay generate test-catalog --input tests/ --output docs/test_catalog.md

# 依存関係グラフを生成（matplotlibが必要）
pylay generate dependency-graph --input src/ --output docs/dependency_graph.png
```

### 型解析と変換
```bash
# Python型をYAMLに変換（推奨コマンド）
pylay yaml                                   # pyproject.toml の target_dirs を使用
pylay yaml src/core/schemas/yaml_spec.py     # 単一ファイル変換
pylay yaml src/core/schemas/                 # ディレクトリ再帰変換
pylay yaml src/core/schemas/yaml_spec.py -o types.yaml  # 出力先指定

# YAMLをPydantic BaseModelに変換
pylay types types.yaml                       # 標準出力
pylay types types.yaml -o model.py           # ファイル出力

# プロジェクト全体解析（統計・品質分析）
pylay check                                   # プロジェクト全体を解析（型定義レベル + type-ignore + 品質）
pylay check --focus quality                   # 品質チェックのみ
```

### 型定義レベル分析
```bash
# ファイルの型定義レベルを分析
pylay check --focus types src/core/schemas/types.py

# ディレクトリ全体を分析
pylay check --focus types src/core/analyzer/

# 詳細情報を含めて分析
pylay check --focus types src/core/analyzer/ -v

# JSON形式で出力
pylay check --focus types src/core/schemas/types.py --format json --output type_analysis.json

# Markdown形式で出力
pylay check --focus types src/ --format markdown --output docs/type_analysis.md
```

#### 新機能: 詳細情報表示

`-v` (`--verbose`) オプションを使用すると、以下の問題箇所を詳細に表示できます：
- Primitive型の直接使用（ファイルパス、行番号、コード内容）
- Level 1型の長期放置（使用箇所の例を最大3件表示）
- 被参照0の型定義（削除または調査推奨の判定理由）
- 非推奨typing使用（Python 3.13標準構文への移行推奨）

詳細は [型レベル分析: 警告箇所の詳細表示機能](docs/features/type-analysis-details.md) を参照してください。

### type: ignore 診断（NEW!）

```bash
# プロジェクト全体のtype: ignoreを診断
pylay check --focus ignore

# 特定ファイルのtype: ignoreを診断（詳細情報付き）
pylay check --focus ignore src/core/converters/type_to_yaml.py -v

# JSON形式で出力
pylay check --focus ignore --format json --output report.json
```

`# type: ignore` が使用されている箇所の原因を自動的に特定し、具体的な解決策を提案します：
- **優先度判定**: HIGH/MEDIUM/LOW で問題を分類
- **原因特定**: mypy実行による型エラー情報の取得と紐付け
- **解決策提案**: コンテキストに応じた具体的な修正方法を提示（`-v`オプションで表示）
- **モダンUI**: Richベースの見やすいコンソール出力

詳細は [type: ignore診断機能](docs/features/diagnose-type-ignore.md) を参照してください。

### 品質チェック

```bash
# プロジェクト全体の品質をチェック
pylay check --focus quality

# 特定ディレクトリの品質チェック（詳細情報付き）
pylay check --focus quality src/core/ -v

# 全てのチェックを実行（型定義レベル + type-ignore + 品質）
pylay check
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

# 新機能: 解析結果に依存グラフと循環検出を含む
pylay project project-analyze --output docs/  # docs/pylay-types/ にグラフ出力
```

### ヘルプの表示
```bash
# 全体のヘルプ
pylay --help

# サブコマンドのヘルプ
pylay yaml --help
pylay types --help
pylay docs --help
pylay check --help
pylay infer-deps --help
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

## ラウンドトリップ変換（Python ⇄ YAML ⇄ Python）

pylayは完全なラウンドトリップ変換をサポートしています。Python型定義をYAMLに変換し、YAMLから再びPython型定義を完全再現できます。

### Makefileコマンド（推奨）

```bash
# srcディレクトリ全体をYAMLに変換
make analyze-yaml

# YAMLからPython型を再生成
make analyze-python

# 一括実行（YAML生成 + Python再生成）
make analyze-roundtrip
```

### 保持される情報

ラウンドトリップ変換では、以下の情報が完全に保持されます：

- ✅ **Field制約**: `ge`, `le`, `gt`, `lt`, `min_length`, `max_length`, `pattern`, `multiple_of`
- ✅ **デフォルト値**: `default` と `default_factory`
- ✅ **複数行docstring**: インデントを保持したまま再現
- ✅ **import情報**: AST解析による正確な抽出
- ✅ **base_classes情報**: 継承構造の保持
- ✅ **型の依存関係**: トポロジカルソートによる正しい順序

### 生成例

**元のPythonコード:**
```python
from pydantic import BaseModel, Field

class QualityCheckResult(BaseModel):
    """品質チェックの結果"""

    total_issues: int = Field(ge=0, description="総問題数")
    error_count: int = Field(ge=0, description="エラー数")
    overall_score: float = Field(ge=0.0, le=1.0, description="全体スコア（0.0〜1.0）")
```

**生成されたPython（YAML経由）:**
```python
from __future__ import annotations

from pydantic import BaseModel, Field

class QualityCheckResult(BaseModel):
    """品質チェックの結果"""

    total_issues: int = Field(ge=0, description="総問題数")
    error_count: int = Field(ge=0, description="エラー数")
    overall_score: float = Field(ge=0.0, le=1.0, description="全体スコア（0.0〜1.0）")
```

### 技術的な特徴

- **前方参照対応**: `from __future__ import annotations` により型定義の順序に依存しない
- **トポロジカルソート**: 型の依存関係を解析し、正しい定義順序で生成
- **Field統一記法**: `Annotated`ではなく`Field()`に統一（description含め全てField内に集約）
- **AST解析**: 実際の`import`文を正確に抽出（使用されていない型のimportは除外）

### 自動生成ファイル管理

生成されたPythonファイル（`.lay.py`）は自動生成ファイルとして扱われます：

```bash
# .gitignore に追加済み
**/schema.lay.py
```

YAMLファイル（`.lay.yaml`）のみをGit管理し、Pythonファイルは必要に応じて再生成する運用を推奨します。

## プロジェクト全体のYAML型定義管理

pylayは、プロジェクト全体の型定義をYAML形式で一元管理する仕組みを提供します。

### ディレクトリ構造の保持

`pylay yaml`コマンドは、ソースディレクトリの構造を保持したままYAMLを生成します：

```bash
# プロジェクト全体の型定義を一括YAML化
pylay yaml

# 出力構造（docs/pylay/ 配下にソース構造をミラーリング）
docs/pylay/
├── src/
│   ├── core/
│   │   ├── schemas/
│   │   │   ├── yaml_spec.lay.yaml
│   │   │   └── pylay_config.lay.yaml
│   │   ├── converters/
│   │   │   └── models.lay.yaml
│   │   └── analyzer/
│   │       └── models.lay.yaml
└── scripts/
    └── (型定義があればYAML生成)
```

### Git管理との統合

- **`.lay.yaml`ファイル**: Git管理対象（型仕様の変更履歴を追跡）
- **`.lay.py`ファイル**: 除外（YAMLから再生成可能）

```gitignore
# 自動生成されたその他のファイルは除外
docs/pylay/**/*.md
docs/pylay/**/*.json

# YAML型仕様ファイルは管理対象
!docs/pylay/**/*.lay.yaml

# 自動生成されたPython型定義は除外
*.lay.py
```

### 型仕様のバージョン管理

YAMLファイルをGit管理することで以下のメリットがあります：

1. **型構造の変更履歴追跡**: `git diff` で型の変更を確認
2. **PRレビューの容易性**: YAMLのdiffで型構造の変更を確認
3. **ラウンドトリップ変換**: YAML → Python型の再生成が可能

## ORM/フレームワーク統合

pylayのドメイン型は、主要なPythonフレームワークやORMと統合できます。

### FastAPI統合

```python
from typing import NewType, Annotated
from pydantic import BaseModel, Field, TypeAdapter
from fastapi import FastAPI

# ドメイン型の定義
UserId = NewType('UserId', int)
UserIdValidator: TypeAdapter[int] = TypeAdapter(Annotated[int, Field(gt=0)])

def create_user_id(value: int) -> UserId:
    """ユーザーIDを生成"""
    return UserId(UserIdValidator.validate_python(value))

# APIモデル
class UserResponse(BaseModel):
    """ユーザーレスポンス"""
    id: UserId
    name: str

app = FastAPI()

@app.get("/users/{user_id}")
def get_user(user_id: int) -> UserResponse:
    """ユーザーを取得"""
    return UserResponse(id=create_user_id(user_id), name="田中太郎")
```

### SQLAlchemy統合

```python
from sqlalchemy import TypeDecorator, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# TypeDecoratorでドメイン型を使用
class UserIdType(TypeDecorator):
    """UserId型のTypeDecorator"""
    impl = Integer
    cache_ok = True

    def process_result_value(self, value, dialect):
        if value is not None:
            return create_user_id(value)
        return None

class Base(DeclarativeBase):
    pass

class User(Base):
    """ユーザーモデル（全レイヤーでドメイン型を使用）"""
    __tablename__ = 'users'
    id: Mapped[UserId] = mapped_column(UserIdType, primary_key=True)
```

### その他のフレームワーク/ORM

- **Django ORM**: カスタムフィールド型で対応
- **Tortoise ORM**: Fieldサブクラスで対応
- **Flask**: 手動バリデーションで統合

詳細は以下のガイドを参照してください：
- [ORM統合ガイド](docs/guides/orm-integration.md): TypeDecorator、レイヤー分離パターン等の実装例
- [フレームワーク別パターン集](docs/guides/framework-patterns.md): FastAPI、Flask、Django統合の詳細

## 開発者向けドキュメント

このプロジェクトを開発・貢献したい場合は、[AGENTS.md](AGENTS.md) と [PRD.md](PRD.md) を参照してください。

## 参考資料

- [Pydantic ドキュメント](https://docs.pydantic.dev/)
- [Python 型付け](https://docs.python.org/3/library/typing.html)
- [mypy ドキュメント](https://mypy.readthedocs.io/en/stable/)
