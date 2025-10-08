# pylay プロジェクト ガイドライン

このドキュメントは、pylayプロジェクトの開発者向けガイドラインです。すべての開発者は、このガイドラインを遵守し、プロジェクトの一貫性と品質を維持してください。

## 必須遵守事項

- **言語ポリシー**: コメント、ドキュメント、コミットメッセージなど、自然言語で表現する必要がある箇所では日本語を使用してください。また、すべての自然言語のやりとり（会話、説明、ドキュメント、コメント）は日本語で統一してください
- すべての実装/編集/生成タスクは、まず [AGENTS.md](AGENTS.md) のプロジェクト概要、アーキテクチャ、技術スタックを確認してください
- 開発環境のセットアップ、ビルド・テスト・開発コマンドは [AGENTS.md](AGENTS.md) に記載された方法を使用してください
- コーディング規約、命名規則、テスト指針は [AGENTS.md](AGENTS.md) に厳密に従ってください
- **ドキュメント参照**: docs配下のドキュメントについては [docs/README.md](docs/README.md) で全体構造を確認してください
  - 型定義ルール: [docs/typing-rule.md](docs/typing-rule.md)
  - 開発環境: [docs/development/](docs/development/)
  - 機能詳細: [docs/features/](docs/features/)
  - 実践ガイド: [docs/guides/](docs/guides/)
  - 技術リファレンス: [docs/reference/](docs/reference/)
- **型定義ルール**: [docs/typing-rule.md](docs/typing-rule.md) に記載された型定義の4つの核心原則を必ず遵守してください
  1. **個別型をちゃんと定義し、primitive型を直接使わない**
     - `str`, `int` などをそのまま使わず、ドメイン型を定義（`type UserId = str` や `Annotated` を活用）
     - **プロジェクトの設計思想**: 型を軸にした依存関係の洗い出しと、丁寧な型付けによる設計からの自動実装を目指す
     - **低レベル放置を好ましくないとする**: Level 1（単純な型エイリアス）の状態で放置されていることは推奨されない
       - Level 1は一時的な状態であり、適切な制約（Level 2）やビジネスロジック（Level 3）への昇格を検討すべき
       - 型定義レベルの適切性は状況に応じて自動判断可能（Level 3 ↔ Level 2）
       - Level 1やその他への判断はdocstringで制御可能（`@target-level: level1`, `@keep-as-is: true`）
     - **被参照0の型の扱い**: なぜ使われていないか調査し、適切なレベルへの昇格を検討する
       - 実装途中の可能性 → Level 2/3への昇格を推奨
       - 認知不足で既存のprimitive型使用箇所が置き換えられていない → 使用箇所を置き換え
       - 将来の拡張性を考えた設計意図 → docstringで設計意図を明記し、`@keep-as-is: true`で現状維持を宣言
  2. Pydanticによる厳密な型定義（3つのレベルを適切に使い分ける）
     - Level 1: `type` エイリアス（制約なし）
     - Level 2: `NewType` + ファクトリ関数 + `TypeAdapter`（★プリミティブ型代替、最頻出パターン、PEP 484準拠）
     - Level 3: `dataclass` + Pydantic または `BaseModel`（複雑なドメイン型・ビジネスロジック）
       - 3a: `dataclass(frozen=True)` - 不変値オブジェクト
       - 3b: `dataclass` - 状態管理エンティティ
       - 3c: `BaseModel` - 複雑なドメインモデル
  3. typing モジュールは最小限に（Python 3.13標準を優先）
  4. 型と実装を分離（types.py, protocols.py, models.py, services.py）
     - **設計思想**: Djangoのアプリケーション構造のように、各モジュールが独立したパッケージとして完結
     - **各モジュール構造**: converters/, analyzer/, doc_generators/ は以下の4ファイル構造を目指す
       - `types.py`: モジュール固有の型定義（Level 1/2を優先）
       - `protocols.py`: Protocolインターフェース定義
       - `models.py`: Pydanticモデル（Level 3: BaseModel）
       - 実装ファイル（type_to_yaml.py等）: ビジネスロジック実装
     - **依存関係の方向**: 実装 → models.py → types.py、実装 → protocols.py
     - **schemas/の役割**: 複数モジュールで共有される共通型のみ配置
- セキュリティ考慮事項、環境変数設定は [AGENTS.md](AGENTS.md) に記載されたポリシーを遵守してください
- プロジェクトステータス（実装済み/開発予定）を確認し、未実装の機能に対しては「未実装/計画中」と明記してください
- シェルコマンド実行の制限事項（単一コマンドの実行、環境変数の設定制限）を厳守してください
- ドキュメント整合ポリシーを遵守し、実装とドキュメントの乖離を防いでください
- このプロジェクトは日本語で運用するため、コメント、ドキュメント、コミットメッセージは日本語で記述してください

## 1. プロジェクト概要

### 1.1 プロジェクト名と目的
**pylay** は、Pythonのtype hintとdocstringsを活用した、types（型情報）とdocs（ドキュメント）間の透過的なジェネレータツールです。

主な機能：
- Pythonの型オブジェクトをYAML形式の型仕様に変換
- YAML型仕様からPydantic BaseModelとしてパース・バリデーション
- YAML型仕様からMarkdownドキュメントを自動生成
- 型推論と依存関係抽出（mypy + ASTハイブリッド）
- **完全なラウンドトリップ変換**（Python型 → YAML → Python型の完全再現）
  - Field制約（ge, le, gt, lt, min_length, max_length, pattern, multiple_of）の保持
  - 複数行docstringのインデント保持
  - AST解析による正確なimport抽出
  - トポロジカルソートによる依存関係順の型定義
  - 前方参照サポート（`from __future__ import annotations`）
- 型定義レベル分析・監視機能（Level 1/2/3の自動分類と昇格/降格推奨）
- type: ignore 原因診断機能（優先度判定、解決策提案）

### 1.2 対象ユーザー
- Python開発者（特に型安全性を重視するプロジェクト）
- ドキュメント自動生成を求めるチーム
- PydanticやYAMLを活用した型仕様管理を必要とするアプリケーション開発者

### 1.3 範囲
**実装済み**:
- 型 <-> YAML 相互変換（完全なラウンドトリップ変換）
  - Field制約の完全保持（ge, le, gt, lt, min_length, max_length, pattern, multiple_of）
  - 複数行docstringのインデント保持
  - AST解析による正確なimport抽出
  - トポロジカルソートによる依存関係順の型定義
- Pydantic v2による高速バリデーション
- YAML -> Markdownドキュメント生成
- 型推論と依存関係抽出（mypy + ASTハイブリッド）
- CLI（コマンドラインインターフェース）
- TUI（テキストユーザーインターフェース）の基盤
- 基本的なテストと相互変換の整合性検証

**範囲外**:
- 高度なロジック処理（YAMLは状態表現のみ）
- 外部API統合（Web UI等）

## 2. アーキテクチャ

### 2.1 ディレクトリ構造（現状）
```
pylay/
├── src/                    # ソースコード
│   ├── cli/               # コマンドラインインターフェース
│   │   ├── analyze_issues.py  # 問題分析ツール
│   │   └── commands/      # CLIコマンド
│   │       ├── generate_docs.py  # ドキュメント生成コマンド
│   │       ├── type_to_yaml.py   # 型→YAML変換コマンド
│   │       └── yaml_to_type.py   # YAML→型変換コマンド
│   ├── core/              # コア機能
│   │   ├── converters/    # 型変換機能
│   │   │   ├── type_to_yaml.py   # Python型 → YAML変換
│   │   │   ├── yaml_to_type.py   # YAML → Python型変換
│   │   │   ├── extract_deps.py   # 依存関係抽出
│   │   │   ├── mypy_type_extractor.py  # mypy型抽出
│   │   │   └── ast_dependency_extractor.py  # AST依存抽出
│   │   ├── analyzer/      # 型解析
│   │   │   ├── protocols.py      # Protocolインターフェース
│   │   │   ├── models.py         # ドメインモデル
│   │   │   ├── base.py           # 基底クラス
│   │   │   ├── type_inferrer.py  # 型推論エンジン
│   │   │   ├── dependency_extractor.py  # 依存抽出
│   │   │   ├── type_classifier.py  # 型分類
│   │   │   ├── type_level_analyzer.py  # 型レベル解析
│   │   │   ├── docstring_analyzer.py  # docstring解析
│   │   │   └── ... (その他解析関連ファイル)
│   │   ├── doc_generators/ # ドキュメント生成
│   │   │   ├── base.py           # 基底クラス
│   │   │   ├── config.py         # 設定管理
│   │   │   ├── filesystem.py     # ファイルシステム操作
│   │   │   ├── markdown_builder.py # Markdown生成
│   │   │   ├── type_doc_generator.py  # 型ドキュメント生成
│   │   │   ├── yaml_doc_generator.py  # YAMLドキュメント生成
│   │   │   ├── graph_doc_generator.py # グラフドキュメント生成
│   │   │   ├── test_catalog_generator.py # テストカタログ生成
│   │   │   └── type_inspector.py  # 型インスペクタ
│   │   ├── schemas/       # 共通型定義（複数モジュールで共有）
│   │   │   ├── types.py          # 共通ドメイン型
│   │   │   ├── graph.py          # グラフ型定義
│   │   │   ├── yaml_spec.py      # YAML型仕様のPydanticモデル
│   │   │   ├── pylay_config.py   # プロジェクト設定型
│   │   │   └── type_index.py     # 型インデックス
│   │   ├── utils/         # ユーティリティ
│   │   ├── output_manager.py  # 出力管理
│   │   └── project_scanner.py # プロジェクトスキャナ
│   ├── tui/               # テキストユーザーインターフェース
│   │   ├── main.py        # TUIメインモジュール
│   │   ├── views/         # ビューモジュール
│   │   └── widgets/       # ウィジェットモジュール
│   └── infer_deps.py      # 型推論エントリーポイント
├── tests/                 # テストコード
├── docs/                  # 生成されたドキュメント
│   └── typing-rule.md     # 型定義ルール（★必読）
├── scripts/               # ユーティリティスクリプト
├── utils/                 # 補助ツール
├── examples/              # 使用例
├── AGENTS.md              # 開発ガイドライン（本ファイル）
├── CLAUDE.md              # Claude Code向けガイドライン
├── PRD.md                 # 製品要件定義
├── README.md              # プロジェクト説明
├── Makefile               # 開発コマンド
├── mypy.ini              # mypy設定
├── pyproject.toml        # プロジェクト設定
├── pyrightconfig.json     # Pyright設定
└── uv.lock               # uv依存関係ロックファイル
```

### 2.2 主要コンポーネント
- **cli/**: コマンドラインインターフェース
- **core/converters/**: 型とYAML間の相互変換機能
- **core/schemas/**: 型仕様のPydanticデータモデル
- **core/doc_generators/**: ドキュメント生成システム
- **core/extract_deps.py**: 依存関係抽出機能
- **tui/**: テキストユーザーインターフェース
- **tests/**: pytestによる包括的なテストスイート
- **scripts/**: ユーティリティスクリプト
- **utils/**: 補助ツール

### 2.3 新機能詳細
#### 2.3.1 CLI（コマンドラインインターフェース）
**cli/** ディレクトリは、プロジェクトのコマンドライン機能を管理します：
- **analyze_issues.py**: コードベースの問題分析ツール
- **commands/**: 個別のCLIコマンド実装
  - **generate_docs.py**: ドキュメント生成コマンド
  - **type_to_yaml.py**: 型からYAMLへの変換コマンド
  - **yaml_to_type.py**: YAMLから型への変換コマンド

#### 2.3.2 TUI（テキストユーザーインターフェース）
**tui/** ディレクトリは、テキストベースのユーザーインターフェース機能を提供します：
- **main.py**: TUIアプリケーションのエントリーポイント
- **views/**: 異なる画面/ビューの実装
- **widgets/**: 再利用可能なUIコンポーネント

#### 2.3.3 コア機能拡張
**core/** ディレクトリには、従来の機能に加えて以下の拡張が含まれます：
- **extract_deps.py**: ASTとNetworkXを活用した依存関係のグラフ構造化
- **converters/infer_types.py**: 型推論機能の追加
- **schemas/graph_types.py**: グラフ構造の型定義

## 3. 技術スタック

### 3.1 言語/フレームワーク
- **Python 3.13+** (必須、開発基準)
- **Pydantic v2**: バリデーションとドメイン型定義
- **Python 3.13標準型システム**: 組み込み型ジェネリクス、Union型簡潔表記、型パラメータ構文（PEP 695）

### 3.2 主要ライブラリ
- **PyYAML/ruamel.yaml**: YAML形式データの処理
- **pytest**: テスト実行フレームワーク
- **mypy**: 型推論と静的型検査（Python標準的な解釈）
- **Pyright**: 厳格な型チェック（Microsoft製、VSCode統合）
- **ast/NetworkX**: 依存関係の抽出とグラフ構造化
- **Ruff**: 高速なリンターとコードフォーマッター
- **uv**: Pythonパッケージ管理ツール（推奨）
- **Rich**: 美しいターミナルUIとテキストフォーマット
- **Pydot**: Graphvizによるグラフ可視化

### 3.3 開発ツール
- **pre-commit**: コード品質の自動チェック
- **Makefile**: 統一された開発用コマンド集
- **VSCode**: 推奨エディタ（タスク設定済み）
- **型チェック**: mypy + Pyright のダブルチェック体制

### 3.4 外部サービス
- なし（スタンドアローン）

## 4. 開発環境セットアップ

### 4.1 必要なツール
- Python 3.13+
- [uv](https://github.com/astral-sh/uv)
- [pre-commit](https://pre-commit.com/)
- [Node.js](https://nodejs.org/) (pyrightを使用する場合、npx経由で自動インストール可能)

### 4.2 Pythonランタイム管理ポリシー
**重要**: OSに直接インストールされたシステムPythonは使用せず、常にuv管理の仮想環境を使用してください。

- **システムPython使用禁止**: `/usr/bin/python` や `/usr/local/bin/python` などのシステムPythonは使用しません
- **仮想環境必須**: すべての開発作業は `uv run` 経由で実行してください
- **環境分離**: 各プロジェクトは独立した仮想環境を使用し、他のプロジェクトやシステムに影響を与えません

### 4.3 セットアップ手順
```bash
# 1. 依存関係をインストール（Python 3.13環境が自動作成されます）
uv sync

# 2. pre-commitフックをインストール
uv run pre-commit install
```

### 4.4 Pythonコマンド実行ルール
すべてのPythonコマンドは以下の形式で実行してください：

```bash
# ✅ 正しい実行方法
uv run python script.py
uv run pytest
uv run mypy
uv run ruff check .

# ❌ 間違った実行方法（システムPythonを使用）
python script.py
python -m pytest
mypy
```

### 4.5 Makefile の使い方
Makefile は開発コマンドを統一的に管理するためのツールです。主要なコマンドをリストアップし、各コマンドの説明と使用例を記述します。`make help` で全コマンドを表示可能です。

- **make install**: 依存関係をインストールします。初回セットアップに使用。
  使用例: `make install`

- **make dev**: 開発環境をセットアップ（インストール + pre-commitインストール）。
  使用例: `make dev`

- **make format**: コードをRuffでフォーマットします。
  使用例: `make format`

- **make lint**: Ruffでコードをチェックし、修正可能な問題を自動修正します。
  使用例: `make lint`

- **make type-check**: mypy + Pyrightで型チェックを実行します（一括実行、推奨）。
  使用例: `make type-check`

- **make test**: pytestでテストを実行し、カバレッジレポートを生成します。
  使用例: `make test`

- **make test-fast**: カバレッジなしで高速テストを実行します。
  使用例: `make test-fast`

- **make coverage**: カバレッジレポートを表示します。
  使用例: `make coverage`

- **make quality-check**: 型チェック + リンターを一括実行します。
  使用例: `make quality-check`

- **make analyze**: pyproject.toml の設定に基づいてプロジェクト全体の型解析とドキュメント生成を実行します。target_dirs で指定されたディレクトリをスキャンし、型情報をYAMLにエクスポート、依存関係を抽出、Markdownドキュメントを生成します。出力は docs/pylay-types/ に documents/ と src/ 等の階層構造で整理されます。
  使用例: `make analyze`

- **make all-check**: フォーマット、型チェック、テスト、品質チェック、プロジェクト解析を一括実行します。
  使用例: `make all-check`

- **make clean**: キャッシュと一時ファイルをクリーンアップします。
  使用例: `make clean`

- **make ci**: CIで実行する全チェックを実行します。
  使用例: `make ci`

これらのコマンドは、uv run を使用して仮想環境内で実行されます。詳細は `make help` を参照してください。

### 4.6 VSCode設定
VSCodeを使用する場合、以下の拡張機能が推奨されます：
- Python（Microsoft社提供）
- Pylance（Pyrightベース、推奨型チェッカー）
- Pylint
- MyPy Type Checker
- Prettier

**型チェック設定**:
- IDE: Pyrightを使用（pyrightconfig.json で設定、standardモード）
- CLI/CI: mypy + Pyright のダブルチェック（Makefileで統合）
- 両方を通過することで高い型安全性を保証

## 5. コーディング規約

### 5.1 基本原則
- **日本語**でコメント、ドキュメント、コミットメッセージを記述
- **型アノテーション完全**: mypy strictモード + Pyright standardモードを遵守
- **docstring必須**: Google形式で全モジュール/クラス/関数に記述
- Pythonのコメントは、docstringをGoogle Styleで記述し、内容は日本語で記述する
- **インポート順序**: standard library → third party → local imports

### 5.2 命名規則
```python
# クラス: PascalCase
class TypeSpec:

# 関数/変数: snake_case
def convert_type_to_yaml():

# 定数: SCREAMING_SNAKE_CASE
MAX_DEPTH = 10

# プライベート: _prefix
_private_method()
```

### 5.3 フォーマット
- **Ruff**を使用した自動フォーマット（line-length: 88）
- 引用符スタイル: ダブルクォート
- 末尾カンマ: 許可（フォーマッタ管理）

### 5.4 型定義ルール（重要）
**型定義の詳細なルールは [docs/typing-rule.md](docs/typing-rule.md) を必ず参照してください。**

#### 核心原則（4つの必須事項）

**重要**: このプロジェクトの設計思想は、**型を軸にした依存関係の洗い出し**と**丁寧な型付けによる設計からの自動実装**です。そのため、個別型（ドメイン型）の定義を積極的に推奨しています。

1. **個別型をちゃんと定義し、primitive型を直接使わない**
   - `str`, `int` などをそのまま使わず、ドメイン型を定義
   - 例: `type UserId = str` （制約なし）、`type Email = Annotated[str, AfterValidator(...)]` （制約あり）
   - **低レベル放置を好ましくないとする**: Level 1（単純な型エイリアス）の状態で長期間放置されていることは推奨されない
     - Level 1は一時的な状態であり、適切な制約（Level 2）やビジネスロジック（Level 3）への昇格を検討すべき
     - 型定義レベルの適切性は状況に応じて自動判断可能（Level 3 ↔ Level 2）
     - Level 1やその他への判断はdocstringで制御可能（`@target-level: level1`, `@keep-as-is: true`）
   - **被参照0の型**: なぜ使われていないか調査し、適切なレベルへの昇格を検討する
     - 実装途中の可能性 → Level 2/3への昇格を推奨
     - 認知不足で既存のprimitive型使用箇所が置き換えられていない → 使用箇所を置き換え
     - 将来の拡張性を考えた設計意図 → docstringで設計意図を明記し、`@keep-as-is: true`で現状維持を宣言

2. **Pydanticによる厳密な型定義でドメイン型を作成する**
   - **3つのレベル**を適切に使い分ける：
     - Level 1: `type` エイリアス（制約なし）
     - Level 2: `NewType` + ファクトリ関数 + `TypeAdapter`（★プリミティブ型代替、最頻出パターン、PEP 484準拠）
     - Level 3: `dataclass` + Pydantic または `BaseModel`（複雑なドメイン型・ビジネスロジック）
       - 3a: `dataclass(frozen=True)` - 不変値オブジェクト
       - 3b: `dataclass` - 状態管理エンティティ
       - 3c: `BaseModel` - 複雑なドメインモデル
   - Fieldによるバリデーション（`min_length`, `ge`, `pattern` など）

3. **typing モジュールは必要最小限に留める（Python 3.13標準を優先）**
   - ❌ `Union[X, Y]` → ✅ `X | Y`
   - ❌ `Optional[X]` → ✅ `X | None`
   - ❌ `List[X]` → ✅ `list[X]`
   - ❌ `Dict[K, V]` → ✅ `dict[K, V]`
   - ❌ `TypeVar('T')` + `Generic[T]` → ✅ `class Container[T]`
   - ❌ `TypeAlias` → ✅ `type Point = tuple[float, float]`

4. **型と実装を分離し、循環参照を防ぐ**
   - **設計思想**: Djangoのアプリケーション構造のように、各モジュールが独立したパッケージとして完結
   - **モジュール単位構造**: converters/, analyzer/, doc_generators/ は以下の4ファイル構造を目指す
     - `types.py`: モジュール固有の型定義（Level 1/2を優先）
     - `protocols.py`: Protocolインターフェース定義
     - `models.py`: Pydanticモデル（Level 3: BaseModel、型+軽いロジック）
     - 実装ファイル（type_to_yaml.py等）: ビジネスロジック実装
   - **依存関係の方向**: 実装 → models.py → types.py、実装 → protocols.py
   - **schemas/の役割**: 複数モジュールで共有される共通型のみ配置（types.py, graph.py, yaml_spec.py等）

#### Python 3.13基準の型定義
本プロジェクトはPython 3.13を開発基準とし、以下の新機能を活用します：
```python
from typing import NewType, Annotated
from pydantic import AfterValidator, Field, BaseModel
from dataclasses import dataclass

# Level 1: 単純な型エイリアス
type Timestamp = float

# Level 2: NewType + ファクトリ関数（★プリミティブ型代替、最頻出、PEP 484準拠）
from pydantic import TypeAdapter, validate_call

UserId = NewType('UserId', str)
UserIdValidator = TypeAdapter(Annotated[str, Field(min_length=8)])

def create_user_id(value: str) -> UserId:
    validated = UserIdValidator.validate_python(value)
    return UserId(validated)

# または @validate_call パターン
Count = NewType('Count', int)

@validate_call
def Count(value: Annotated[int, Field(ge=0)]) -> Count:  # type: ignore[no-redef]
    return NewType('Count', int)(value)

# Level 3a: dataclass(frozen=True)（不変値オブジェクト）
@dataclass(frozen=True)
class CodeLocation:
    file: str
    line: int = Field(ge=1)

# Level 3b: BaseModel（複雑なドメインモデル）
class User(BaseModel):
    user_id: UserId
    email: Email
    age: Count

    def is_adult(self) -> bool:
        return self.age >= 18

# ✅ Python 3.13標準構文
def process(data: str | int | None) -> list[str]:
    pass

# ✅ 型パラメータ構文（PEP 695）
class Container[T](BaseModel):
    items: list[T]

# ✅ type文（PEP 695）
type Point = tuple[float, float]
type JSONValue = str | int | float | bool | None | dict[str, "JSONValue"]

# ❌ 非推奨（Python 3.9以前の書き方）
from typing import Union, Optional, List, TypeVar, Generic, NewType
def process(data: Union[str, int, None]) -> List[str]:
    pass
Email = NewType('Email', str)  # Annotated を使用
```

**重要**: 型定義の厳密性 = ドキュメント生成の精度

詳細は **[docs/typing-rule.md](docs/typing-rule.md)** を参照してください。

## 6. テスト指針

### 6.1 テスト戦略
- **pytest**を主要テストフレームワークとして使用
- **ラウンドトリップテスト**: 型 → YAML → 型 → Markdownの整合性検証
- **依存関係抽出テスト**: mypy + ASTの精度検証
- **カバレッジ目標**: 80%以上（docstring含む）

### 6.2 テスト実行コマンド
```bash
# 全てのテスト実行（カバレッジ付き）
make test

# 高速テスト（カバレッジなし）
make test-fast

# カバレッジレポートの確認
make coverage
```

### 6.3 テストファイル配置
```
tests/
├── test_*.py              # ユニットテスト
├── test_integration_*.py  # 統合テスト
└── test_migrations.py     # 移行テスト
```

## 7. セキュリティ考慮事項

### 7.1 入力バリデーション
- YAMLパース: `yaml.safe_load`を使用
- Pydanticによる厳格な型バリデーション
- 深さ制限による無限再帰防止

### 7.2 依存関係管理
- **safety**による脆弱性のチェック（CIに統合）
- 最小権限の原則（不要な依存関係を避ける）
- 定期的なセキュリティ更新

### 7.3 コードセキュリティ
- 機密情報のハードコード禁止
- SQLインジェクション対策（本プロジェクトでは該当なし）
- XSS対策（本プロジェクトでは該当なし）

## 8. 環境変数設定

### 8.1 必須環境変数
なし（設定ファイルベース）

### 8.2 オプション環境変数
```bash
# ログレベル（DEBUG、INFO、WARNING、ERROR）
export LOG_LEVEL=INFO

# 出力ディレクトリ
export OUTPUT_DIR=./docs

# mypy推論の詳細度
export MYPY_INFER_LEVEL=2
```

### 8.3 Pythonランタイム実行ポリシー
- **uv必須**: すべてのPythonコマンドは `uv run` を使用してください
- **仮想環境のみ**: OSのシステムPythonは使用禁止です
- **コマンド実行**: `python script.py` ではなく `uv run python script.py` を使用

### 8.4 シェルコマンド実行の制限事項
- **単一コマンドのみ**: パイプラインや複数コマンドは禁止
- **環境変数設定**: 各コマンドで個別に設定
- **サブシェル**: 基本的に禁止（必要な場合のみ許可）

## 9. プロジェクトステータス

### 9.1 実装状況
- ✅ **Phase 1**: 基本構造実装（型<->YAML, バリデーション）
- ✅ **Phase 2**: Markdown生成と統合
- ✅ **Phase 3**: CLI/TUIインターフェース実装 - 完了
- ✅ **Phase 4**: テスト/ドキュメント/拡張 - 進行中（CI/CD実装完了）
- ✅ **Phase 5**: 型推論/依存抽出実装 - 完了（全機能統合）
- ✅ **Phase 6**: CLIツール化とPyPI公開準備（GitHub Issues #1で完了）
- 🚧 **Phase 7**: PyPI公開準備とパッケージング（GitHub Issues #3で進行中）

### 9.2 未実装/計画中機能
- Sphinxドキュメント統合

### 9.3 既知の問題
- なし

## 10. ドキュメント整合ポリシー

### 10.1 ドキュメント自動生成
- Markdownドキュメントは自動生成を優先
- 手動ドキュメントは最小限に抑える
- README.mdとPRD.mdは手動メンテナンス

### 10.2 整合性維持
- 実装とドキュメントの乖離を防ぐ
- コード変更時は自動テストで整合性検証
- PRD.mdは定期的に更新

### 10.3 ドキュメント構造
- **README.md**: ユーザー向けの概要とセットアップ
- **PRD.md**: 開発者向けの詳細要件
- **AGENTS.md**: 開発者向けのガイドライン（本ドキュメント）
- **docs/**: 自動生成されたAPIドキュメント

## 11. コミュニケーションスタイル

### 11.1 基本原則
- **思慮深く行動する**: 各行動や発言について、影響や結果を考慮
- **時系列を重視した会話**: 会話の文脈を尊重し、直近の会話内容のトーンを優先
- **意図の理解**: ユーザーの会話の真の意図や真意を深く考え、同じ方向性で対応
- **誠実なコミュニケーション**: 変なごまかしを避け、常に正直で率直な対応

### 11.2 開発コミュニケーション
- GitHub Issues/PRを使用した透明性確保
- コードレビュー時の建設的フィードバック
- 変更の影響範囲を明記したコミットメッセージ

### 11.3 問題解決アプローチ
1. 問題の理解と明確化
2. 影響範囲の評価
3. 解決策の検討と実装
4. テストによる検証
5. ドキュメントの更新

## 12. 開発ワークフロー

### 12.1 開発サイクル
1. **計画**: 機能追加時はPRD.mdを確認し、Issueを作成
2. **実装**: 型アノテーションとdocstringを徹底
3. **テスト**: ラウンドトリップテストを必ず含む（`uv run pytest` を使用）
4. **レビュー**: mypy/Ruffチェックを通過（`uv run mypy`、`uv run ruff` を使用）
5. **マージ**: pre-commitフックで最終確認（`uv run pre-commit` を使用）

### 12.2 ブランチ戦略
- **main**: 安定版（リリース済み機能）
- **develop**: 開発版（次のリリース候補）
- **feature/**: 新機能開発
- **hotfix/**: 緊急バグ修正

### 12.3 リリースプロセス

#### 12.3.1 リリース前の準備
1. **品質チェック**: `make ci` で全テスト通過を確認
2. **バージョン決定**: リリースバージョンを決定（セマンティックバージョニング準拠）
3. **ブランチ確認**: developブランチで作業中であることを確認

#### 12.3.2 リリース作業
1. **バージョン更新**: `pyproject.toml` のバージョンを更新
2. **CHANGELOG更新**: `CHANGELOG.md` に変更内容を追加
3. **ドキュメント更新**: 必要に応じてREADME.mdやドキュメントを更新
4. **テスト実行**: `make test` で全テストが通過することを確認
5. **リリース準備**: `make release-prepare` でタグ設定とビルドを実行
- 自動的にgitタグを作成・プッシュ（`v{バージョン番号}`）
  - タグメッセージにCHANGELOGの内容を自動的に含める
- パッケージをビルド

#### 12.3.3 PyPI公開
1. **テストPyPI公開**: `make publish-test` でテストPyPIに公開して動作確認
   - 自動的にgitタグを設定（既に設定済みの場合はスキップ）
   - タグメッセージにCHANGELOGの内容を自動的に含める
2. **本番PyPI公開**: `make publish` で本番PyPIに公開
   - 自動的にgitタグを設定（既に設定済みの場合はスキップ）
   - タグメッセージにCHANGELOGの内容を自動的に含める
3. **公開確認**: `make check-pypi` で公開状況を確認

#### 12.3.4 リリース完了
1. **mainブランチマージ**: 変更をmainブランチにマージ
2. **GitHubリリース**: `gh release create` でGitHubリリースを作成
3. **タグ作成**: 必要に応じてGitタグを作成
4. **リリース通知**: チームやユーザーにリリースを通知

#### 12.3.5 詳細手順
詳細な手順は [docs/PUBLISH.md](docs/PUBLISH.md) を参照してください。

#### 12.3.6 リリースチェックリスト

**リリース前の必須確認事項**:
- [ ] 全てのテストが通過している（`make ci`）
- [ ] バージョン番号が適切に設定されている（pyproject.toml）
- [ ] CHANGELOG.mdが最新の変更内容で更新されている
- [ ] ドキュメントが最新の状態である
- [ ] 依存関係のセキュリティチェックが完了している（`make safety-check`）

**PyPI公開時の確認事項**:
- [ ] PyPI APIトークンが正しく設定されている（.envファイル）
- [ ] テストPyPIで動作確認済みである
- [ ] 本番PyPIに同じバージョンのパッケージが存在しない

**リリース後の確認事項**:
- [ ] PyPIでパッケージが正常に公開されている（`make check-pypi`）
- [ ] GitHubリリースが作成されている
- [ ] インストールテストが可能である
- [ ] チームやユーザーにリリースを通知済みである

## 13. 参考資料

### プロジェクトドキュメント
- **[docs/typing-rule.md](docs/typing-rule.md)**: 型定義ルール（必読）
- [PRD.md](PRD.md): 詳細な製品要件
- [README.md](README.md): ユーザー向け概要

### 外部リソース
- [Pydantic ドキュメント](https://docs.pydantic.dev/)
- [Python 3.13 型ヒント](https://docs.python.org/3.13/library/typing.html)
- [mypy ドキュメント](https://mypy.readthedocs.io/en/stable/)
- [PEP 695: Type Parameter Syntax](https://peps.python.org/pep-0695/)
- [PEP 604: Union Type as X | Y](https://peps.python.org/pep-0604/)

---

このガイドラインはプロジェクトの進捗に応じて更新されます。変更が必要な場合は、PRD.mdと合わせて更新してください。
