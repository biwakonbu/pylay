# pylayスキーマファイル

このディレクトリには、pylayプロジェクトの主要な型定義をYAML形式で管理しています。

## 目的

- **型仕様の可視化**: Pydantic BaseModelの構造をYAML形式で表現
- **ドキュメント生成**: YAMLからMarkdownドキュメントを自動生成
- **型の再生成**: YAMLからPython型定義を再生成可能（ラウンドトリップ変換）
- **バージョン管理**: 型仕様の変更履歴を追跡

## ファイル一覧

| ファイル | 元のモジュール | 説明 |
|---------|---------------|------|
| `yaml_spec.lay.yaml` | `src/core/schemas/yaml_spec.py` | YAML型仕様のPydanticモデル定義（7型） |
| `pylay_config.lay.yaml` | `src/core/schemas/pylay_config.py` | プロジェクト設定型の定義（9型） |

## 使用方法

### YAMLスキーマの生成

```bash
# 特定のモジュールからYAMLを生成
uv run pylay yaml src/core/schemas/yaml_spec.py -o docs/pylay/schemas/yaml_spec.yaml

# プロジェクト全体を解析（pyproject.toml設定に基づく）
uv run pylay project-analyze
```

### YAMLからPython型定義を再生成

```bash
# YAMLからPython型定義を生成（.lay.py拡張子で自動生成）
uv run pylay types docs/pylay/schemas/yaml_spec.lay.yaml

# 生成された型定義は .lay.py 拡張子が付き、.gitignoreで除外される
# 本番コードでは src/core/schemas/ の元のファイルを使用すること
```

### YAMLからMarkdownドキュメントを生成

```bash
# YAMLからAPIドキュメントを生成
uv run pylay docs -i docs/pylay/schemas/yaml_spec.lay.yaml -o docs/api/
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

4. **配置ルール**
   - YAMLスキーマ: `docs/pylay/schemas/*.lay.yaml`
   - プロジェクト全体解析: `docs/pylay/` （pyproject.toml設定: `output_dir = "docs/pylay"`）

## 注意事項

- **手動編集は非推奨**: YAMLファイルは自動生成されるため、手動編集は避けてください
- **元のPythonモジュールを優先**: 型定義の変更は元のPythonモジュール（`src/core/schemas/`）で行ってください
- **警告ヘッダーの尊重**: 各YAMLファイルには警告ヘッダーが含まれており、次回の生成時に上書きされます

## 更新履歴

- 2025-10-08: Issue #54対応として、YAMLスキーマ管理を開始
  - `yaml_spec.lay.yaml`: 7個の型定義（RefPlaceholder, TypeSpec等）
  - `pylay_config.lay.yaml`: 9個の型定義（LevelThresholds, ErrorCondition等）
  - 標準出力先を `docs/pylay/` に統一（pyproject.toml: `output_dir = "docs/pylay"`）
