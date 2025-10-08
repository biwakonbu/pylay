# pylayスキーマファイル

このディレクトリには、`src/core/schemas/` モジュールの型定義をYAML形式で管理しています。

> **注意**: このREADMEは特定ディレクトリ（schemas/）の説明です。
> プロジェクト全体のYAML型定義管理については、[README.md](../../../README.md) の「プロジェクト全体のYAML型定義管理」セクションを参照してください。

## 目的

- **型仕様の可視化**: Pydantic BaseModelやその他の型定義をYAML形式で表現
- **ドキュメント生成**: YAMLからMarkdownドキュメントを自動生成
- **型の再生成**: YAMLからPython型定義を再生成可能（ラウンドトリップ変換）
- **バージョン管理**: 型仕様の変更履歴を追跡

## ファイル一覧

| ファイル | 元のモジュール | 説明 |
|---------|---------------|------|
| `yaml_spec.lay.yaml` | `src/core/schemas/yaml_spec.py` | YAML型仕様のPydanticモデル定義 |
| `pylay_config.lay.yaml` | `src/core/schemas/pylay_config.py` | プロジェクト設定型の定義 |
| `graph.lay.yaml` | `src/core/schemas/graph.py` | グラフ構造型の定義 |
| その他 | `src/core/schemas/*.py` | schemas/ モジュール内の型定義 |

## 使用方法

### YAMLスキーマの生成

```bash
# 単一ファイルからYAMLを生成（.lay.yaml拡張子が自動付与）
uv run pylay yaml src/core/schemas/yaml_spec.py

# ディレクトリ全体を再帰的にYAML化（構造を保持）
uv run pylay yaml src/core/schemas/

# プロジェクト全体を解析（pyproject.toml設定に基づく）
uv run pylay yaml
```

### YAMLからPython型定義を再生成

```bash
# YAMLからPython型定義を生成（.lay.py拡張子で自動生成）
uv run pylay types docs/pylay/src/core/schemas/yaml_spec.lay.yaml

# 生成された型定義は .lay.py 拡張子が付き、.gitignoreで除外される
# 本番コードでは src/core/schemas/ の元のファイルを使用すること
```

### YAMLからMarkdownドキュメントを生成

```bash
# YAMLからAPIドキュメントを生成
uv run pylay docs -i docs/pylay/src/core/schemas/yaml_spec.lay.yaml -o docs/api/
```

## 設計方針

1. **YAMLスキーマファイル（.lay.yaml）は管理対象**
   - Gitで管理し、型仕様の変更履歴を追跡
   - レビュー時に型構造の変更を確認できる

2. **自動生成されたPython型定義（.lay.py）は除外**
   - `.gitignore`で除外（`*.lay.py`）
   - 元のPythonモジュールが正として管理される

3. **ラウンドトリップ変換の保証**
   - Python型 → YAML → Python型 の変換で情報が失われないことを保証
   - テストで整合性を検証

4. **ディレクトリ構造の保持**
   - `pylay yaml` コマンドはソースの構造を `docs/pylay/` 配下にミラーリング
   - 例: `src/core/schemas/types.py` → `docs/pylay/src/core/schemas/types.lay.yaml`

5. **型定義の自動検出**
   - BaseModel、type文、NewType、dataclass、Enumを自動検出
   - テストファイル（test_*.py）と__init__.pyは除外

## 注意事項

- **手動編集は非推奨**: YAMLファイルは自動生成されるため、手動編集は避けてください
- **元のPythonモジュールを優先**: 型定義の変更は元のPythonモジュール（`src/core/schemas/`）で行ってください
- **警告ヘッダーの尊重**: 各YAMLファイルには警告ヘッダーが含まれており、次回の生成時に上書きされます
- **メタデータの活用**: 各YAMLには`_metadata`セクションが含まれ、ソースファイルのハッシュや更新日時が記録されています

## 参考リンク

- [プロジェクト全体のYAML型定義管理](../../../README.md#プロジェクト全体のyaml型定義管理)
- [Django風パッケージ構造ガイド](../../../docs/guides/django-style-structure.md)（未作成）
- [types.py作成ガイドライン](../../../docs/guides/types-creation-guide.md)（未作成）

## 更新履歴

- 2025-10-08: Issue #54対応として、YAMLスキーマ管理を開始
  - 型定義自動検出の強化（BaseModel, type文, NewType, dataclass, Enum）
  - メタデータセクションの完全実装（SHA256ハッシュ、ファイルサイズ、更新日時）
  - ディレクトリ構造保持による階層的なYAML管理
