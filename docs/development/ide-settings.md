# IDE 設定ガイド

このドキュメントでは、pylay プロジェクトで使用する mypy、ruff、uv などのツールを主要な IDE で適切に設定する方法を説明します。

## 設定の原則

- **mypy**: `mypy.ini` ファイルを直接使用するため、IDE の設定で `mypy.ini` を指定してください
- **ruff**: `pyproject.toml` の設定を使用します
- **uv**: Python 環境管理に使用します

## VSCode / Cursor

### 拡張機能のインストール

1. **Python 拡張機能** (Microsoft)
   - 必須: Python 開発に必要
   - Pylance または Jedi 言語サーバーを選択

2. **Ruff 拡張機能**
   ```bash
   code --install-extension charliermarsh.ruff
   ```

3. **mypy 拡張機能**
   ```bash
   code --install-extension ms-python.mypy-type-checker
   ```

### settings.json 設定

`.vscode/settings.json` に以下の設定を追加してください：

```json
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "python.terminal.activateEnvironment": true,

    // mypy 設定
    "mypy.enabled": true,
    "mypy.configFile": "mypy.ini",
    "mypy.runUsingActiveInterpreter": true,
    "mypy.severity": {
        "error": true,
        "note": true,
        "warning": true
    },

    // ruff 設定
    "ruff.enable": true,
    "ruff.organizeImports": true,
    "ruff.fixAll": true,
    "ruff.importStrategy": "fromEnvironment",

    // フォーマット設定
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "charliermarsh.ruff",
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff"
    },

    // 型チェック設定
    "python.analysis.typeCheckingMode": "basic",
    "python.analysis.autoImportCompletions": true,

    // テスト設定
    "python.testing.pytestEnabled": true,
    "python.testing.pytestPath": "./.venv/bin/pytest",
    "python.testing.pytestArgs": [
        "tests"
    ]
}
```

### tasks.json 設定

`.vscode/tasks.json` に以下のタスクを追加してください：

```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "uv: sync",
            "type": "shell",
            "command": "uv",
            "args": ["sync"],
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "silent",
                "focus": false,
                "panel": "shared"
            }
        },
        {
            "label": "mypy: check",
            "type": "shell",
            "command": "uv",
            "args": ["run", "mypy"],
            "group": {
                "kind": "test",
                "isDefault": false
            },
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "shared"
            }
        },
        {
            "label": "ruff: check",
            "type": "shell",
            "command": "uv",
            "args": ["run", "ruff", "check", "."],
            "group": {
                "kind": "test",
                "isDefault": false
            },
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "shared"
            }
        },
        {
            "label": "ruff: format",
            "type": "shell",
            "command": "uv",
            "args": ["run", "ruff", "format", "."],
            "group": {
                "kind": "test",
                "isDefault": false
            },
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "shared"
            }
        }
    ]
}
```

## PyCharm / IntelliJ

### 設定方法

1. **Project Interpreter の設定**
   - `Settings > Project > Python Interpreter`
   - 既存のインタープリターを選択または新規作成
   - `uv sync` で作成した仮想環境を使用

2. **mypy の設定**
   - `Settings > Tools > mypy`
   - `Configuration file` に `mypy.ini` を指定
   - `Run mypy for:` を `Whole project` に設定

3. **Ruff の設定**
   - `Settings > Tools > External Tools`
   - 新規ツールを追加:
     - Name: `Ruff Check`
     - Program: `uv`
     - Arguments: `run ruff check .`
     - Working directory: `$ProjectFileDir$`

     - Name: `Ruff Format`
     - Program: `uv`
     - Arguments: `run ruff format .`
     - Working directory: `$ProjectFileDir$`

4. **Pre-commit hooks の設定**
   - `Settings > Tools > Pre-commit`
   - `Configure hooks` で `pre-commit install` を実行

## Cursor 固有の設定

Cursor を使用している場合、VSCode 互換の設定がそのまま使用できますが、以下の追加設定を検討してください：

1. **Chat 機能との連携**
   - `Settings > Cursor Settings > AI`
   - `Code Review` で mypy エラーを自動検出するよう設定

2. **リアルタイム型チェック**
   - `Settings > Python > Type Checking`
   - `Enable type checking` を有効化

## トラブルシューティング

### mypy が動作しない場合

1. `mypy.ini` ファイルの場所を確認してください
2. Python インタープリターが仮想環境を指しているか確認してください
3. VSCode の場合: `Python: Select Interpreter` で正しいインタープリターを選択してください

### ruff が動作しない場合

1. `pyproject.toml` の `[tool.ruff]` セクションが存在することを確認してください
2. `uv run ruff --version` で ruff が動作するか確認してください

### 仮想環境の有効化

```bash
# uv を使用する場合
uv sync

# 従来の方法
source .venv/bin/activate
```

## 推奨されるワークフロー

1. **開発開始時**
   ```bash
   uv sync  # 依存関係のインストール
   ```

2. **コーディング中**
   - IDE の自動保存時に ruff format が実行される
   - 型エラーはリアルタイムで mypy が検出

3. **コミット前**
   ```bash
   uv run ruff check .  # リンター実行
   uv run mypy          # 型チェック実行
   uv run pytest        # テスト実行
   ```

この設定により、mypy.ini と pyproject.toml の設定が IDE で適切に連携され、効率的な開発環境が構築されます。
