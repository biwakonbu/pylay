# Doc Generators パッケージ

自動ドキュメント生成のためのモジュラーアーキテクチャを提供するパッケージです。

## 概要

このパッケージは、テストドキュメントと型ドキュメントの生成を統一的な設計で実装します。依存性注入、テスタビリティ、保守性を重視した設計となっています。

## アーキテクチャ

### 共通基盤

- **`base.py`**: 全ジェネレーターの基底クラス（`DocumentGenerator`）
- **`filesystem.py`**: ファイルシステム抽象化（`RealFileSystem`, `InMemoryFileSystem`）
- **`markdown_builder.py`**: Fluent APIによるMarkdown生成
- **`config.py`**: 設定管理（`GeneratorConfig`, `TestCatalogConfig`, `TypeDocConfig`）

### 専用ジェネレーター

- **`test_catalog_generator.py`**: テストカタログ生成（`TestCatalogGenerator`）
- **`type_doc_generator.py`**: 型ドキュメント生成（`LayerDocGenerator`, `IndexDocGenerator`）
- **`type_inspector.py`**: 型情報抽出ユーティリティ（`TypeInspector`）

## 主要特徴

### 1. 依存性注入によるテスタビリティ

```python
from scripts.doc_generators.filesystem import InMemoryFileSystem
from scripts.doc_generators.test_catalog_generator import TestCatalogGenerator

# テスト用にインメモリファイルシステムを注入
filesystem = InMemoryFileSystem()
generator = TestCatalogGenerator(filesystem=filesystem)
```

### 2. Fluent APIによる直感的なMarkdown生成

```python
from scripts.doc_generators.markdown_builder import MarkdownBuilder

md = MarkdownBuilder()
content = (md
    .heading(1, "タイトル")
    .paragraph("説明文")
    .code_block("python", "print('Hello')")
    .build())
```

### 3. 設定外部化

```python
from scripts.doc_generators.config import TypeDocConfig
from pathlib import Path

config = TypeDocConfig(
    output_directory=Path("custom/output"),
    skip_types={"IgnoreMe"},
)
```

## 使用方法

### テストドキュメント生成

```python
from scripts.doc_generators.test_catalog_generator import TestCatalogGenerator
from scripts.doc_generators.config import TestCatalogConfig
from pathlib import Path

# 設定を作成
config = TestCatalogConfig(
    test_directory=Path("tests/schemas"),
    output_path=Path("docs/test_catalog.md"),
)

# ジェネレーターを作成して実行
generator = TestCatalogGenerator(config=config)
generator.generate()
```

### 型ドキュメント生成

```python
from scripts.doc_generators.type_doc_generator import LayerDocGenerator
from scripts.doc_generators.config import TypeDocConfig
from pathlib import Path

# レイヤー固有のドキュメント生成
config = TypeDocConfig(output_directory=Path("docs/types"))
generator = LayerDocGenerator(config=config)

layer_types = {"UserId": str, "Email": str}
generator.generate("primitives", layer_types)
```

### インデックスドキュメント生成

```python
from scripts.doc_generators.type_doc_generator import IndexDocGenerator

# 全体インデックスの生成
generator = IndexDocGenerator(config=config)
type_registry = {
    "primitives": {"UserId": str},
    "domain": {"User": UserModel},
}
generator.generate(type_registry)
```

## 後方互換性

既存の`generate_test_docs.py`と`generate_type_docs.py`のAPIは完全に保持されています：

```python
# 既存API（変更なし）
from scripts.generate_test_docs import generate_test_docs
from scripts.generate_type_docs import generate_docs, generate_layer_docs

generate_test_docs("docs/test_catalog.md")
generate_docs("docs/types")
```

## テスト戦略

### 単体テスト

各コンポーネントは独立してテスト可能：

```python
# InMemoryFileSystemを使用した高速テスト
filesystem = InMemoryFileSystem()
generator = TestCatalogGenerator(filesystem=filesystem)
generator.generate()

# 結果をメモリ内で検証
content = filesystem.get_content(output_path)
assert "期待する内容" in content
```

### 統合テスト

`test_integration_doc_generators.py`で全体フローをテスト：

- 両ジェネレーターの互換性
- 並列実行での競合状態
- エラー分離
- パフォーマンス特性

## 設計原則

### 1. 単一責任の原則

- `TypeInspector`: 型情報抽出のみ
- `MarkdownBuilder`: Markdown生成のみ
- `TestCatalogGenerator`: テストカタログ生成のみ

### 2. 依存性逆転の原則

```python
# 抽象化（Protocol）に依存
class DocumentGenerator:
    def __init__(self, filesystem: FileSystemInterface):
        self.fs = filesystem  # 具象実装ではなく抽象化に依存
```

### 3. オープン・クローズドの原則

新しいジェネレーターは`DocumentGenerator`を継承して拡張：

```python
class CustomGenerator(DocumentGenerator):
    def generate(self, **kwargs):
        # カスタム実装
        pass
```

## パフォーマンス

### メモリ効率

- `InMemoryFileSystem`による高速テスト
- ストリーミング型Markdownビルダー
- 必要時のみファイルI/O実行

### 実行時間

- 74型の完全ドキュメント生成: ~2秒以内
- テストカタログ生成: ~1秒以内
- 並列実行対応

## 拡張性

### 新しいドキュメント種別の追加

```python
class APIDocGenerator(DocumentGenerator):
    def __init__(self, config: APIDocConfig, **kwargs):
        super().__init__(**kwargs)
        self.config = config

    def generate(self, api_specs: dict, **kwargs):
        self.md.heading(1, "API ドキュメント")
        # カスタム生成ロジック
        content = self.md.build()
        self._write_file(output_path, content)
```

### 新しい出力形式の追加

```python
class JSONDocumentGenerator(DocumentGenerator):
    def _write_file(self, path: Path, content: str):
        # JSONとして出力
        import json
        data = {"content": content, "timestamp": self._format_timestamp()}
        self.fs.write_text(path, json.dumps(data, ensure_ascii=False))
```

## トラブルシューティング

### よくある問題

1. **ImportError**: パッケージパスの確認
   ```python
   # ✅ 正しい
   from scripts.doc_generators.config import TypeDocConfig

   # ❌ 間違い
   from doc_generators.config import TypeDocConfig
   ```

2. **FileNotFoundError**: 出力ディレクトリの自動作成
   ```python
   # 自動的にディレクトリが作成される
   config = TypeDocConfig(output_directory=Path("deep/nested/path"))
   ```

3. **型エラー**: 適切な型アノテーション
   ```python
   # ✅ 正しい
   types: dict[str, type[Any]] = {"UserId": str}

   # ❌ 間違い
   types = {"UserId": str}  # 型情報不足
   ```

### デバッグ

```python
# デバッグ用にInMemoryFileSystemを使用
filesystem = InMemoryFileSystem()
generator = TestCatalogGenerator(filesystem=filesystem)
generator.generate()

# 生成されたファイル一覧を確認
print("Generated files:", filesystem.list_files())

# 内容を確認
for file_path in filesystem.list_files():
    print(f"=== {file_path} ===")
    print(filesystem.get_content(file_path))
```

## 今後の展開

- CLI インターフェースの追加
- 設定ファイル（YAML/TOML）対応
- プラグインシステム
- リアルタイム更新（ファイル監視）
- 他の出力形式対応（HTML、PDF等）