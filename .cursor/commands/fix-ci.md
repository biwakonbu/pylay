# fix-ci
CIを修正します。

## 概要

GitHub ActionsのCIワークフローを修正します。このコマンドは、CIエラーを解析し、原因を特定して修正するためのガイドラインを提供します。

- 指定されたPR番号（$PR_NUMBER）がある場合、PRに関連するCIを実行・修正します。
- 指定されたAction ID（$ACTION_ID）がある場合、単独のActions実行を対象にします。
- どちらも指定されていない場合、最新のCI実行を対象にします。

PR依存のCIか単独ActionsかをIDで判断し、適切に対応します。プロジェクトのCIは`.github/workflows/ci.yml`に基づき、テスト、Lint、型チェックなどを含みます。

## 前提条件

- GitHub CLI（gh）がインストールされていること。
- プロジェクトリポジトリにアクセス可能であること（認証済み）。
- 修正にはコード編集権限が必要です。

## 実行手順

### 1. CI情報の取得

CIの詳細ログを取得してエラーを解析します。

#### PR関連のCIの場合
```bash
# PRのCIログを表示
gh pr view $PR_NUMBER --json checks
# または詳細ログ
gh run list --repo $(gh repo view --json name | jq -r .name) --branch $(gh pr view $PR_NUMBER --json headRefName | jq -r .headRefName) --limit 1 --json databaseId
gh run view $RUN_ID --log
```

#### 単独Actionsの場合
```bash
# Actionsの詳細を表示
gh run view $ACTION_ID --log
# またはリストから最新を取得
gh run list --limit 1 --json databaseId
```

ログからエラーメッセージを特定します。よくあるエラー：
- **テスト失敗**: pytestエラー（uv run pytest）。
- **Lintエラー**: Ruffやmypyの違反（uv run ruff check .、uv run mypy .）。
- **依存エラー**: uv sync失敗やpyproject.tomlの不整合。
- **ビルドエラー**: Pythonバージョン不一致（3.13+必須）。

### 2. エラーの解析

ログを読み、エラーの種類を分類します。

- **pytest失敗**: テストケースの失敗箇所を特定（例: `tests/test_*.py`の特定関数）。
- **mypy/Ruffエラー**: ファイルと行番号を抽出（例: `src/core/converters/type_to_yaml.py:123: error: Incompatible types`）。
- **依存関連**: uv.lockの更新が必要か確認（make install）。
- **環境関連**: uv run使用を徹底（システムPython禁止）。

ログの関連部分をコピーし、原因をメモします。必要に応じてローカルで再現：
```bash
# ローカルでCI再現
make test  # テスト実行
make lint  # Lintチェック
make type-check  # 型チェック
```

### 3. 修正対応

解析に基づき、修正を実施します。

#### テストエラーの場合
- 失敗したテストを修正（コードのバグ修正、型アノテーション追加）。
- docstringやコメントを日本語で更新。

#### Lint/型エラーの場合
- Ruff/mypyのエラーを個別に修正（ファイル単位でuv run ruff check --fix）。
- 型アノテーションをPython 3.13+の新機能で簡潔に（Union -> |）。

#### 依存エラーの場合
```bash
uv sync  # 依存更新
make install  # 再インストール
```

修正後、pre-commitを実行：
```bash
uv run pre-commit run --all-files
```

### 4. 検証

修正を検証します。

- ローカルCI実行：
```bash
make ci  # 全CI再現（Makefileに定義）
```

- リモート再実行：
  - PRの場合: `gh run rerun $RUN_ID`
  - 新規Actions: PRをプッシュしてトリガー。

CIが通過するまで繰り返します。失敗時はログを再解析。

## 注意事項

- すべてのコマンドはuv run経由で実行（システムPython禁止）。
- Makefileを優先（例: make test）。
- 修正は最小限にし、テストカバレッジ80%以上を維持。
- セキュリティ: safetyチェック（make security）。
- 未実装機能の変更時はAGENTS.mdを確認。

## トラブルシューティング

- ghコマンドエラー: `gh auth login`で再認証。
- ログが多すぎる: `--log-failed`オプション使用。
- 権限不足: リポジトリオーナーに相談。

このガイドでCI修正を効率化してください。追加の詳細が必要なら、AGENTS.mdを参照。
