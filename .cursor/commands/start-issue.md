# start-issue

GitHub Issuesから作業を開始します。

## 概要

Issue番号を指定して以下を実行します：

1. Issueの詳細確認
2. feature/issue-{番号}-{概要} ブランチを作成・チェックアウト
3. mainから最新をpull
4. 作業開始の準備完了

## 実行内容

```bash
# Issue詳細の取得・表示
gh issue view $ISSUE_NUMBER

# ブランチ名の生成（Issueタイトルから適切な名前を生成）
ISSUE_TITLE=$(gh issue view $ISSUE_NUMBER --json title -q .title)
BRANCH_NAME="feature/issue-$ISSUE_NUMBER-$(echo "$ISSUE_TITLE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-\|-$//g')"

# mainブランチに移動して最新をpull
git checkout main
git pull origin main

# 新しいブランチを作成・チェックアウト
git checkout -b "$BRANCH_NAME"

echo "✅ Issue #$ISSUE_NUMBER の作業を開始しました"
echo "ブランチ: $BRANCH_NAME"
```

## 使用例

```
/start-issue 123
```
