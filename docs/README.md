# pylay ドキュメント

pylayプロジェクトのドキュメント一覧です。

## 目次

### コアドキュメント

- [typing-rule.md](typing-rule.md) - **型定義ルール（必読）**: Python 3.13準拠の型定義3レベル、ドメイン型定義の原則
- [ui-guidelines.md](ui-guidelines.md) - **UI/UXガイドライン**: CLI/TUIのデザイン原則、Rich活用法

### 開発ガイド

- [development/](development/) - **開発環境セットアップとIDE設定**
  - [README.md](development/README.md) - 開発環境セットアップ概要
  - [ide-settings.md](development/ide-settings.md) - VSCode設定とPyright/mypy統合
- [PUBLISH.md](PUBLISH.md) - **PyPI公開手順**: リリースプロセス、タグ作成、パッケージング

### 機能ガイド

- [features/](features/) - **機能詳細ドキュメント**
  - [type-analysis-details.md](features/type-analysis-details.md) - 型レベル分析機能: 警告箇所の詳細表示
  - [diagnose-type-ignore.md](features/diagnose-type-ignore.md) - type: ignore原因診断機能
  - [quality-check.md](features/quality-check.md) - コード品質チェック機能

### 使い方ガイド

- [guides/](guides/) - **実践ガイド**
  - [types-creation-guide.md](guides/types-creation-guide.md) - 型定義作成ガイド（Level 1/2/3の使い分け）
  - [yaml-management-guide.md](guides/yaml-management-guide.md) - YAML型仕様管理ガイド
  - [django-style-structure.md](guides/django-style-structure.md) - Django風パッケージ構造ガイド
  - [orm-integration.md](guides/orm-integration.md) - ORM統合ガイド（SQLAlchemy/Django ORM）
  - [framework-patterns.md](guides/framework-patterns.md) - フレームワーク統合パターン
  - [lay-file-workflow.md](guides/lay-file-workflow.md) - .layファイルワークフロー
  - [clean-regeneration.md](guides/clean-regeneration.md) - クリーン再生成ガイド
  - [migration-guide.md](guides/migration-guide.md) - マイグレーションガイド

### リファレンス

- [reference/](reference/) - **技術リファレンス**
  - [type-detection-rules.md](reference/type-detection-rules.md) - 型検出ルール詳細

## ドキュメント構造

```
docs/
├── README.md              # このファイル
├── typing-rule.md         # 型定義ルール（必読）
├── ui-guidelines.md       # UI/UXガイドライン
├── PUBLISH.md             # PyPI公開手順
├── development/           # 開発環境セットアップ
├── features/              # 機能詳細ドキュメント
├── guides/                # 実践ガイド
└── reference/             # 技術リファレンス
```

## はじめに

pylayは、Pythonの型ヒントとdocstringsを活用した、型情報とドキュメント間の透過的なジェネレータツールです。

### 主な機能

- Python型 → YAML型仕様への変換
- YAML型仕様 → Pydanticモデルとしてのバリデーション
- YAML型仕様 → Markdownドキュメント自動生成
- 型推論と依存関係抽出（mypy + ASTハイブリッド）
- 型定義レベル分析・監視（Level 1/2/3）
- type: ignore原因診断

### 推奨される学習順序

1. **[typing-rule.md](typing-rule.md)** - 型定義の基礎を理解
2. **[guides/types-creation-guide.md](guides/types-creation-guide.md)** - 型定義の実践方法を学習
3. **[features/type-analysis-details.md](features/type-analysis-details.md)** - 型レベル分析機能の使い方
4. 必要に応じて他のガイドを参照

## 参考資料

- [AGENTS.md](../AGENTS.md) - 開発者向けガイドライン
- [CLAUDE.md](../CLAUDE.md) - Claude Code向けガイドライン
- [PRD.md](../PRD.md) - 製品要件定義
- [README.md](../README.md) - プロジェクト概要

## 外部リソース

- [Pydantic ドキュメント](https://docs.pydantic.dev/)
- [Python 3.13 型ヒント](https://docs.python.org/3.13/library/typing.html)
- [mypy ドキュメント](https://mypy.readthedocs.io/en/stable/)
- [PEP 695: Type Parameter Syntax](https://peps.python.org/pep-0695/)
- [PEP 604: Union Type as X | Y](https://peps.python.org/pep-0604/)
