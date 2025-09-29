# pylay - 製品要件ドキュメント (PRD)

## 1. プロジェクト概要

### 1.1 プロジェクト名
pylay

### 1.2 プロジェクトの目的
Pythonのtype hintとdocstringsを活用した、types（型情報）とdocs（ドキュメント）間の透過的なジェネレータツールを開発する。
主に、Pythonで扱える型情報を全て利用し、型 <-> YAMLの相互コンパイルを実現する。これにより、型の仕様をYAMLとして表現し、Pydanticによる高速バリデーションを可能とする。
最終目標として、YAMLからMarkdownファイルへの変換をサポートし、ドキュメントの自動生成を達成する。

### 1.3 対象ユーザー
- Python開発者（特に型安全性を重視するプロジェクト）
- ドキュメント自動生成を求めるチーム
- PydanticやYAMLを活用した型仕様管理を必要とするアプリケーション開発者

### 1.4 プロジェクトの範囲
- 型情報（type hint）の抽出とYAMLシリアライズ/デシリアライズ
- YAMLベースの型仕様バリデーション（Pydantic統合）
- YAMLからMarkdownドキュメントの生成
- 基本的なテストと相互変換の整合性検証
- 実装内容からの型推論と依存関係抽出（mypy + astハイブリッド）

範囲外：
- 高度なロジック処理（YAMLは状態表現のみ）
- 外部API統合やUI開発

## 2. 機能要件

### 2.1 型 <-> YAML 相互変換
- **型からYAML生成**:
  - Pythonの型オブジェクト（str, int, List, Dict, Unionなど）をYAML形式の型仕様に変換。
  - サポートする型: 基本型（str, int, float, bool）、コレクション（List[T], Dict[K, V]）、Union[X, Y]。
  - docstringsをYAMLのdescriptionフィールドに反映（オプション）。
- **YAMLから型生成**:
  - YAMLをPydantic BaseModel（TypeSpec）としてパースし、バリデーションを実行。
  - YAML構造: name, type, description, required, items/properties/variants など。

### 2.2 バリデーション
- Pydantic v2を活用した高速ランタイムバリデーション。
- YAML型仕様に基づくデータ検証（例: 型不整合時のエラー検出）。
- シリアライズ/デシリアライズのサポート（model_dump, model_validate）。

### 2.3 YAML -> Markdown 変換
- YAML型仕様からMarkdownドキュメントを自動生成。
  - ヘッダー: 型名と説明。
  - 本文: YAMLコードブロック、プロパティ/要素の再帰的記述。
  - フッター: 自動生成注記。
- 出力: レイヤー別または型別MDファイル（例: docs/yaml_types/{type}.md）。

### 2.4 型推論と依存関係抽出（新機能）
- **型推論**:
  - 未アノテーションのコードに対してmypyの`--infer`フラグを活用し、型を自動推測（例: `x = 42` → `int`）。
  - 推論結果を既存の型アノテーションとマージし、完全な型情報を構築。
- **依存関係抽出**:
  - Python AST (astモジュール) でコードを解析し、型依存グラフを構築（例: 関数引数の型Aが型Bを参照）。
  - サポート: 変数/関数/クラスのアノテーション抽出、継承関係、コレクション型。
  - グラフ化: NetworkXで依存ツリーを作成（オプション: Graphviz視覚化）。
- **YAML化**:
  - 抽出された依存をTypeSpec拡張形式でYAML出力（例: dependencies: {User: [str, List[Order]]}）。
  - 統合: 既存のtype_to_yamlと連動し、モジュール全体の型依存仕様を生成。
- **トリガー**: CLIコマンド（例: `pylay infer-deps src/module.py`）で実行。自動化（pre-commit hook）対応。

### 2.5 ユーティリティ機能
- エントリーポイントスクリプト: generate_type_docs.py, generate_yaml_docs.py, infer_deps.py など。
- テストフレームワーク: pytestによるラウンドトリップテスト（型 -> YAML -> 型 -> MDの整合性、依存抽出の正確性）。

### 2.6 プロジェクト全体解析機能（pyproject.toml統合）
- **設定駆動解析**: pyproject.tomlの[tool.pylay]セクションで設定を一元管理。
- **ディレクトリ走査**: 指定ディレクトリ内のPythonファイルを自動検出・解析。
- **一括生成**: 型情報抽出、依存関係グラフ化、YAML/Markdownドキュメント生成を一括実行。
- **CLI統合**: `pylay project-analyze`コマンドで実行（dry-run、verboseモード対応）。
- **設定項目**:
  - target_dirs: 解析対象ディレクトリ
  - output_dir: 出力先ディレクトリ
  - generate_markdown: Markdown生成有無
  - extract_deps: 依存関係抽出有無
  - exclude_patterns: 除外パターン
  - infer_level: 型推論レベル
- **出力構造**:
  ```
  docs/pylay-types/
  ├── src/                    # YAML型仕様
  └── documents/              # Markdownドキュメント
  ```

## 3. 非機能要件

### 3.1 パフォーマンス
- 型変換: 100型以内で1秒以内。
- バリデーション: Pydanticの高速性を活用（ミリ秒オーダー）。
- 生成: Markdown出力はストリーミング可能。
- 型推論/抽出: 1モジュールあたり5秒以内（mypy + ast）。

### 3.2 互換性
- Python 3.13+。
- mypy厳格モード対応（型アノテーション完全）。
- 既存ツール（doc_generatorsパッケージ）と共存。

### 3.3 セキュリティ
- YAMLパース時の安全ロード（yaml.safe_load）。
- 型バリデーションによる入力サニタイズ。
- 深さ制限（無限再帰防止）。

### 3.4 保守性
- モジュラー設計（converters, schemas, doc_generators, type_extractor）。
- docstringsと型ヒントの徹底。
- 自動ドキュメント生成による同期維持。

## 4. 技術スタック

- **言語/フレームワーク**: Python 3.13+, Pydantic v2 (バリデーション/モデル), typing/collections.abc (型抽出)。
- **ライブラリ**: PyYAML/ruamel.yaml (YAMLハンドリング), pytest (テスト), mypy (型推論), ast/NetworkX (依存抽出)。
- **ビルド/テスト**: Makefile統合（type-index, test, infer-deps）。
- **ドキュメント**: Markdown自動生成, Sphinx対応予定。

## 5. リスクと依存

### 5.1 リスク
- YAMLの曖昧性 → Pydanticの厳格モードで緩和。
- mypy推論の限界（動的型未対応） → astハイブリッドで補完。

### 5.2 依存
- Pydanticの型システム。
- Pythonのtypingモジュール（get_origin/get_args）。
- mypyのinfer/dump-types機能。

## 6. スケジュールとマイルストーン

- **Phase 1**: 基本構造実装（型<->YAML, バリデーション） - 完了。
- **Phase 2**: Markdown生成と統合 - 完了。
- **Phase 3**: テスト/ドキュメント/拡張 - 進行中。
- **Phase 4**: 型推論/依存抽出実装 - 完了。
- **Phase 5**: リファクタリングとアーキテクチャ最適化 - 完了。
- **リリース**: v0.1.0 (基本機能完成)。

## 8. 実装状況とアーキテクチャ変更

### 8.1 リファクタリングの概要
Phase 5で実施したコード解析部分のリファクタリングにより、以下の改善を実現：

**変更内容**:
- **src/core/analyzer/ ディレクトリ新規作成**: 解析エンジンを独立化し、疎結合アーキテクチャを採用。
- **Analyzer インターフェース**: `base.py` で抽象基底クラスを実装。`create_analyzer(config, mode)` でモード選択可能（"types_only", "deps_only", "full"）。
- **型推論/依存抽出の分離**: `TypeInferenceAnalyzer` (mypy + AST) と `DependencyExtractionAnalyzer` (AST + NetworkX) に分離。
- **GraphProcessor**: NetworkXを活用したグラフ分析/視覚化/メトリクス計算を提供。循環検出を標準機能に。
- **疎結合の接合**: `TypeDependencyGraph` を共通出力に統一。他コンポーネント（converters, doc_generators）はこれを入力に使用。
- **CLI/TUI適応**: 直接的なAST/mypy呼び出しを削除し、analyzer経由に変更。
- **スキーマ拡張**: `inferred_nodes` 追加と `weight` バリデーション（0-1範囲）。

**効果**:
- **開発複雑さ軽減**: 解析変更が変換/生成に波及せず、独立性向上。
- **柔軟性向上**: configで解析モード切り替え（例: CI高速化のための軽量モード）。
- **拡張性向上**: 新解析（例: 動的解析）の追加が容易に。
- **型安全性維持**: Pydanticで型安全、循環防止、キャッシュ機構。
- **グラフ活用**: 視覚化/サイクル検出が標準化。`make analyze` の出力が豊か（docs/にグラフPNG自動生成）。

**テスト状況**:
- 新テストスイート追加（`test_analyzer.py`）: 19テスト中全通過。
- カバレッジ: 78% → 80%目標に近づく（低カバレッジ部分のテスト追加）。
- CI: 全チェック通過（テスト209 passed, 型チェックOK, フォーマットOK, セキュリティOK）。

**影響範囲**:
- 既存CLIコマンド（`infer-deps`, `analyze types --mode full`）が強化。
- ドキュメント生成にグラフ情報（循環依存、統計）が自動追加。
- プロジェクト全体解析で依存グラフと循環検出を含む。

## 7. 参考資料

- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Python Typing](https://docs.python.org/3/library/typing.html)
- [mypy Documentation](https://mypy.readthedocs.io/en/stable/)
- [ChatGPT共有やり取り](https://chatgpt.com/share/68d753a4-053c-800b-804c-ad2f0bcf0d3d)（型推論方針の議論）
- プロジェクトREADME.mdとAGENTS.md。

このドキュメントはプロジェクト進捗に応じて更新されます。
