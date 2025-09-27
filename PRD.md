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
- 複雑な型（Generic, ForwardRef）の完全サポート未実装 → 段階的拡張。
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
- **Phase 4**: 型推論/依存抽出実装 - 開始（プロトタイプ作成）。
- **リリース**: v0.1.0 (基本機能完成)。

## 7. 参考資料

- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Python Typing](https://docs.python.org/3/library/typing.html)
- [mypy Documentation](https://mypy.readthedocs.io/en/stable/)
- [ChatGPT共有やり取り](https://chatgpt.com/share/68d753a4-053c-800b-804c-ad2f0bcf0d3d)（型推論方針の議論）
- プロジェクトREADME.mdとAGENTS.md。

このドキュメントはプロジェクト進捗に応じて更新されます。
