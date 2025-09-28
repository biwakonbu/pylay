# 📦 PyPI 公開ガイド

このドキュメントでは、pylayプロジェクトをPyPI（Python Package Index）に公開する手順を詳しく説明します。

## 🎯 公開の概要

PyPI公開は以下の流れで行います：

1. **準備段階**: PyPIアカウントとAPIトークンの設定
2. **ビルド段階**: パッケージのビルドとテスト
3. **公開段階**: テストPyPIと本番PyPIへの公開
4. **確認段階**: 公開状況の確認と動作テスト

## 1. 準備段階

### 1.1 PyPIアカウントの登録

1. [PyPI](https://pypi.org/) にアクセス
2. アカウント登録（https://pypi.org/account/register/）
3. メールアドレスの確認

### 1.2 APIトークンの取得

1. PyPIアカウント設定ページ（https://pypi.org/manage/account/）にアクセス
2. 「API tokens」セクションで「Add API token」をクリック
3. トークン名を入力（例: `pylay-publisher`）
4. スコープ: **「Entire account」**を選択
5. 「Create token」をクリック
6. 表示されたトークンを安全な場所に保存

### 1.3 環境変数の設定

```bash
# APIトークンを環境変数に設定
export TWINE_USERNAME=__token__
export TWINE_PASSWORD="pypi-XXXXXX..."  # 取得したAPIトークン

# 設定を確認
echo $TWINE_USERNAME
echo $TWINE_PASSWORD
```

**⚠️ セキュリティ注意**: APIトークンはGitリポジトリにコミットしないよう注意してください。

## 2. ビルド段階

### 2.1 クリーンアップ

```bash
# 古いビルドファイルを削除
make clean
```

### 2.2 バージョン確認

```bash
# 現在のバージョンを確認
grep 'version = ' pyproject.toml

# 必要に応じてバージョンを更新
# 例: 0.1.0 -> 0.1.1
```

### 2.3 パッケージビルド

```bash
# パッケージをビルド
make build

# または直接
uv build

# ビルドされたファイルを確認
ls -la dist/
# 出力例:
# -rw-r--r-- 1 user user 12345 2024-01-01 12:00 pylay-0.1.0-py3-none-any.whl
# -rw-r--r-- 1 user user 23456 2024-01-01 12:00 pylay-0.1.0.tar.gz
```

### 2.4 テストインストール

```bash
# ビルドしたパッケージをテストインストール
make test-install

# または手動で
pip install dist/pylay-0.1.0-py3-none-any.whl --force-reinstall

# 動作確認
pylay --version
pylay --help
```

## 3. 公開段階

### 3.1 Twineのインストール

```bash
# Twineがインストールされていない場合
pip install twine
```

### 3.2 テストPyPIへの公開

**推奨: 本番公開前にテストPyPIで動作確認してください**

```bash
# テストPyPIに公開
make publish-test

# または手動で
twine upload --repository testpypi dist/*
```

### 3.3 テストPyPIでの確認

```bash
# テストPyPIでの公開状況を確認
make check-test-pypi

# テストインストール
pip install --index-url https://test.pypi.org/simple/ pylay

# 動作確認
pylay --version
```

### 3.4 本番PyPIへの公開

**⚠️ 注意: 公開前に以下の確認をお願いします**
- PyPIアカウントとAPIトークンが正しく設定されていること
- バージョン番号が適切であること
- テストPyPIで動作確認済みであること

```bash
# 本番PyPIに公開
make publish

# または手動で
twine upload dist/*
```

## 4. 確認段階

### 4.1 公開状況の確認

```bash
# 本番PyPIでの公開状況を確認
make check-pypi

# テストPyPIでの公開状況を確認
make check-test-pypi
```

### 4.2 公開されたパッケージの確認

```bash
# PyPIプロジェクトページを確認
open https://pypi.org/project/pylay/

# またはcurlでJSON情報を取得
curl -s https://pypi.org/pypi/pylay/json | python -m json.tool
```

### 4.3 インストールテスト

```bash
# クリーンインストールでテスト
pip uninstall pylay -y
pip install pylay

# 動作確認
pylay --version
pylay --help
```

## 5. Makefile コマンドリファレンス

| コマンド | 説明 |
|----------|------|
| `make build` | パッケージをビルド |
| `make test-install` | ビルドしてテストインストール |
| `make publish-test` | テストPyPIに公開 |
| `make publish` | 本番PyPIに公開（要確認） |
| `make check-pypi` | 本番PyPIの状況確認 |
| `make check-test-pypi` | テストPyPIの状況確認 |

## 6. トラブルシューティング

### 6.1 認証エラー

```bash
# 環境変数が正しく設定されているか確認
echo $TWINE_USERNAME
echo $TWINE_PASSWORD

# APIトークンが有効か確認
twine check dist/*
```

### 6.2 バージョン競合

```bash
# 既存バージョンを確認
curl -s https://pypi.org/pypi/pylay/json | python -c "import sys, json; data = json.load(sys.stdin); print('\n'.join(data.get('releases', {})))"

# バージョン番号を更新
# pyproject.tomlのversionを更新
```

### 6.3 ネットワークエラー

```bash
# ネットワーク接続を確認
ping pypi.org

# プロキシ設定が必要な場合
export HTTPS_PROXY=your-proxy-server:port
```

### 6.4 ビルドエラー

```bash
# 依存関係を最新に更新
uv sync --upgrade

# クリーンアップしてから再ビルド
make clean
make build
```

## 7. ベストプラクティス

### 7.1 リリース前のチェックリスト

- [ ] バージョン番号が適切か確認
- [ ] 全テストが通過しているか確認
- [ ] 依存関係の脆弱性チェック完了
- [ ] ドキュメントが最新か確認
- [ ] テストPyPIで動作確認済み
- [ ] PyPIアカウントとトークンが有効か確認

### 7.2 セキュリティ対策

- APIトークンはGitリポジトリに含めない
- 環境変数やシークレットマネージャーを使用
- 公開前に機密情報が含まれていないか確認

### 7.3 バージョン管理

- セマンティックバージョニング（Semantic Versioning）を採用
- メジャーアップデート: `1.0.0` → `2.0.0`
- マイナーアップデート: `1.0.0` → `1.1.0`
- パッチアップデート: `1.0.0` → `1.0.1`

## 8. 参考資料

- [PyPI公式ドキュメント](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
- [Twineドキュメント](https://twine.readthedocs.io/)
- [セマンティックバージョニング](https://semver.org/)

---

このドキュメントはプロジェクトの状況に応じて更新してください。公開手順に不明な点があれば、IssueやPRで質問してください。
