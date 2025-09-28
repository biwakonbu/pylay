# create-pr

現在のブランチでの作業をまとめてGitHubのPRを作成します。

## 概要

GitHubのPRを作成し、以下の情報を自動的に設定します：

- **タイトル**: 作業内容に基づいた適切なタイトル
- **説明**: 変更内容の詳細な説明
- **ブランチ**: 現在の作業ブランチ（自動取得）
- **マージ先ブランチ**: mainブランチ
- **参照Issues**: 完了したIssue番号（自動解決）
- **レビュワー**: プロジェクト設定に基づく適切なレビュワー
- **ラベル**: 作業タイプに応じた適切なラベル
- **担当者**: 現在の作業者

## 実行内容

### 基本的なPR作成コマンド
```bash
gh pr create --title "作業内容のタイトル" --body "変更内容の詳細説明" --base "main" --head "$(git branch --show-current)" --web
```

### 詳細なオプション付きコマンド
```bash
gh pr create \
  --title "Issue #3: PyPI公開準備とパッケージング完了" \
  --body "Issue #3の完了に伴い、以下の作業を実施しました..." \
  --base "main" \
  --head "$(git branch --show-current)" \
  --reviewer "@biwakonbu" \
  --label "enhancement" \
  --assignee "@biwakonbu" \
  --web
```

### 作業ブランチの自動解決機能
```bash
# 現在のブランチ名を取得
CURRENT_BRANCH=$(git branch --show-current)

# Issue番号をブランチ名から抽出（feature/issue-3-pypiの場合）
ISSUE_NUMBER=$(echo "$CURRENT_BRANCH" | sed -n 's/.*issue-\([0-9]\+\).*/\1/p')

# タイトルと説明の自動生成
PR_TITLE="Issue #$ISSUE_NUMBER: $(gh issue view $ISSUE_NUMBER --json title -q .title)"
PR_BODY="Issue #$ISSUE_NUMBER の完了に伴い、以下の作業を実施しました：\n\n## 実施した作業\n\n- [作業項目1]\n- [作業項目2]\n\n## テスト結果\n\n- 全てのテストが通過\n- CLIツールが正常に動作\n\n## 関連ファイル\n\n- 変更されたファイル一覧"
```

## 使用例

### 基本的な使用方法
```bash
/create-pr
```

### カスタムメッセージ付き
```bash
/create-pr "PyPI公開準備完了" "Issue #3の完了に伴い、パッケージングとCLIツールの動作確認を実施。README.mdも更新。"
```

### 複数のIssueを同時に解決する場合
```bash
/create-pr "Issue #3, #4: 複数Issue解決" "複数のIssueをまとめて解決しました。詳細はコミットメッセージ参照。"
```

## 前提条件

- GitHub CLI (`gh`) がインストールされ、認証されていること
- 作業ブランチが作成済みであること
- 作業内容がコミットされていること
- GitHubリポジトリがリモートoriginに設定されていること

## 実行後の動作

1. 指定されたパラメータでPRが作成されます
2. `--web` オプションにより、ブラウザでPRページが開きます
3. レビュワーに通知が送信されます
4. 関連Issueが自動的にCloseされます（`Closes #番号` 記法使用時）

## 注意事項

- PR作成前に作業内容を適切にコミットしてください
- 大きな変更の場合はドラフトPRとして作成することを検討してください
- 機密情報が含まれないことを確認してください
