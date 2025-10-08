# pylay プロジェクトのMakefile
# Python 3.13+ 対応の型安全なドキュメント生成ツール

.PHONY: help setup format lint type-check test coverage quality-check analyze clean ci

# =============================================================================
# 開発環境セットアップ
# =============================================================================

help: ## このMakefileのヘルプを表示
	@echo "🚀 pylay プロジェクトのMakefile"
	@echo ""
	@echo "📦 開発環境セットアップ:"
	@echo "  setup              開発環境をセットアップ"
	@echo "  install            依存関係をインストール"
	@echo ""
	@echo "🎨 コード品質チェック:"
	@echo "  format             コードを自動フォーマット"
	@echo "  lint               リンターでコードチェック"
	@echo "  type-check         型チェック（mypy + pyright 一括実行）"
	@echo "  quality-check      品質チェック（型 + リンター + pylay品質）"
	@echo ""
	@echo "🧪 テスト実行:"
	@echo "  test               テスト実行 + カバレッジレポート"
	@echo "  test-fast          高速テスト実行（カバレッジなし）"
	@echo "  coverage           カバレッジレポートを開く"
	@echo ""
	@echo "🔍 プロジェクト解析:"
	@echo "  analyze            プロジェクト全体を解析"
	@echo "  check              品質チェック（型レベル + type-ignore + 品質）"
	@echo "  check-types        型定義レベルを分析"
	@echo "  check-ignore       type: ignore の原因を診断"
	@echo ""
	@echo "🧹 クリーンアップ:"
	@echo "  clean              キャッシュと一時ファイルを削除"
	@echo ""
	@echo "🚀 CI/CD:"
	@echo "  ci                 CIで実行する全チェック"
	@echo ""
	@echo "📦 リリース管理:"
	@echo "  release-prepare    リリース準備（タグ設定・ビルド）"
	@echo "  publish-test       テストPyPIに公開"
	@echo "  publish            本番PyPIに公開"
	@echo ""
	@echo "📚 詳細なヘルプ:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

setup: install ## 開発環境をセットアップ
	@echo "🔧 開発環境をセットアップ中..."
	uv run pre-commit install

install: ## 依存関係をインストール
	@echo "📦 依存関係をインストール中..."
	uv sync

# =============================================================================
# コード品質チェック
# =============================================================================

format: ## コードを自動フォーマット
	@echo "🎨 コードをフォーマット中..."
	uv run ruff format .

lint: ## リンターでコードチェック
	@echo "🔍 リンターでコードチェック中..."
	uv run ruff check . --fix

type-check: ## 型チェック（mypy + pyright）
	@echo "🔍 型チェック中（mypy + pyright）..."
	@echo "  - mypy..."
	@uv run mypy src/
	@echo "  - pyright..."
	@uv run pyright src/

quality-check: ## 品質チェック（型チェック + リンター + pylay品質チェック）
	@echo "🔍 コード品質チェック中..."
	$(MAKE) type-check
	$(MAKE) lint
	@echo "🔍 pylay品質チェック中（pyproject.toml の target_dirs を使用）..."
	uv run pylay check

# =============================================================================
# テスト実行
# =============================================================================

test: ## テスト実行 + カバレッジレポート
	@echo "🧪 テストを実行中..."
	uv run pytest --cov=. --cov-report=html --cov-report=xml --cov-report=term

test-fast: ## 高速テスト実行（カバレッジなし）
	@echo "⚡ 高速テストを実行中..."
	uv run pytest

coverage: test ## カバレッジレポートを開く
	@echo "📊 カバレッジレポートを開きます..."
	@if command -v open >/dev/null 2>&1; then \
		open htmlcov/index.html; \
	elif command -v xdg-open >/dev/null 2>&1; then \
		xdg-open htmlcov/index.html; \
	else \
		echo "📄 htmlcov/index.html をブラウザで開いてください"; \
	fi

# =============================================================================
# プロジェクト解析
# =============================================================================

analyze: ## プロジェクト全体を解析
	@echo "🔍 プロジェクトを解析中..."
	uv run pylay project-analyze

check: ## 品質チェック（型レベル + type-ignore + 品質）
	@echo "🔍 品質チェック中..."
	uv run pylay check

check-types: ## 型定義レベルを分析（デフォルト: src/）
	@echo "🔍 型定義レベルを分析中..."
	uv run pylay check --focus types src/

check-types-verbose: ## 詳細な型レベル分析（推奨事項含む）
	@echo "🔍 詳細な型定義レベル分析中..."
	uv run pylay check --focus types src/ -v

check-ignore: ## type: ignore の原因を診断（デフォルト: カレントディレクトリ）
	@echo "🔍 type: ignore の原因を診断中..."
	uv run pylay check --focus ignore

check-ignore-file: ## 特定ファイルの type: ignore を診断（FILE変数で指定）
	@if [ -z "$(FILE)" ]; then \
		echo "❌ エラー: FILE変数を指定してください"; \
		echo "使用例: make check-ignore-file FILE=src/cli/commands/check.py"; \
		exit 1; \
	fi; \
	echo "🔍 type: ignore の原因を診断中: $(FILE)"; \
	uv run pylay check --focus ignore $(FILE) -v

check-ignore-verbose: ## 解決策を含む詳細な type: ignore 診断
	@echo "🔍 詳細な type: ignore 診断中..."
	uv run pylay check --focus ignore -v

check-quality: ## 型定義品質チェック（デフォルト: カレントディレクトリ）
	@echo "🔍 型定義品質チェック中..."
	uv run pylay check --focus quality

# =============================================================================
# クリーンアップ
# =============================================================================

clean: ## キャッシュと一時ファイルを削除
	@echo "🧹 クリーンアップ中..."
	uv run ruff clean
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/ 2>/dev/null || true
	rm -rf dist/ build/ 2>/dev/null || true

# =============================================================================
# CI/CD パイプライン
# =============================================================================

ci: ## CIで実行する全チェック（format + quality-check + test + analyze）
	@echo "🚀 CIパイプラインを実行中..."
	$(MAKE) format
	$(MAKE) quality-check
	$(MAKE) test
	$(MAKE) analyze
	@echo "✅ CIチェック完了"

# =============================================================================
# 高度な機能（開発者向け）
# =============================================================================

safety-check: ## 依存関係のセキュリティチェック
	@echo "🔒 セキュリティチェック中..."
	uv run safety check --file pyproject.toml

radon-check: ## コード複雑度チェック
	@echo "📊 コード複雑度をチェック中..."
	uv run radon cc . -s --total-average

interrogate-check: ## docstringカバレッジチェック
	@echo "📝 docstringカバレッジをチェック中..."
	uv run interrogate .

infer-deps: ## 型推論と依存関係抽出を実行
	@echo "🔍 型推論と依存関係抽出を実行中..."
	@echo "使用例: make infer-deps FILE=src/core/converters/type_to_yaml.py"
	uv run python src/infer_deps.py $(FILE)

# =============================================================================
# リリース管理スクリプト（メンテナ向け）
# =============================================================================

release-prepare: ## リリース準備（バージョン更新・タグ設定・ビルド）
	@echo "🚀 リリース準備を開始します..."
	@echo "現在のバージョン: $$(grep '^version = ' pyproject.toml | head -1 | sed 's/version = \"\(.*\)\"/\1/')"
	@echo "📝 Gitタグを設定中..."
	@VERSION=$(shell grep '^version = ' pyproject.toml | head -1 | sed 's/version = "\(.*\)"/\1/'); \
	if git tag | grep -q "^v$$VERSION$$"; then \
		echo "⚠️  タグ v$$VERSION は既に存在します"; \
	else \
		echo "📝 Gitタグ v$$VERSION を作成中..."; \
		echo "タグメッセージを生成中..."; \
		TAG_MSG="リリースバージョン$$VERSION\n\n$$(awk '/^## \[$$VERSION\]/{f=1; next} /^---/{f=0} f{print}' CHANGELOG.md | head -20)"; \
		git tag -a "v$$VERSION" -m "$$TAG_MSG"; \
		git push origin "v$$VERSION"; \
		echo "✅ Gitタグ v$$VERSION を作成・プッシュしました"; \
	fi
	@echo "📦 パッケージをビルド中..."
	$(MAKE) build
	@echo "✅ リリース準備完了"

# =============================================================================
# PyPI公開（メンテナ向け）
# =============================================================================

build: ## パッケージをビルド
	@echo "📦 パッケージをビルド中..."
	uv build

test-install: build ## ビルドしてテストインストール
	@echo "🧪 テストインストールを実行中..."
	pip install dist/pylay-0.2.0-py3-none-any.whl --force-reinstall
	pylay --version

publish-test: build ## テストPyPIに公開
	@echo "🚀 テストPyPIに公開中..."
	@echo "⚠️  公開前に以下の確認をお願いします:"
	@echo "   1. UV_TEST_INDEX=1 または uv.tomlにテストPyPI設定があること"
	@echo "   2. バージョン番号が適切であること"
	@echo "   3. ビルドが正常に完了していること"
	@read -p "上記の確認が完了したらEnterを押してください..." || echo "続行します..."
	@echo "📝 Gitタグを設定中..."
	@VERSION=$(shell grep '^version = ' pyproject.toml | head -1 | sed 's/version = "\(.*\)"/\1/'); \
	echo "現在のバージョン: $$VERSION"; \
	if git tag | grep -q "^v$$VERSION$$"; then \
		echo "⚠️  タグ v$$VERSION は既に存在します"; \
	else \
		echo "📝 Gitタグ v$$VERSION を作成中..."; \
		echo "タグメッセージを生成中..."; \
		TAG_MSG="リリースバージョン$$VERSION\n\n$$(awk '/^## \[$$VERSION\]/{f=1; next} /^---/{f=0} f{print}' CHANGELOG.md | head -20)"; \
		git tag -a "v$$VERSION" -m "$$TAG_MSG"; \
		git push origin "v$$VERSION"; \
		echo "✅ Gitタグ v$$VERSION を作成・プッシュしました"; \
	fi
	uv publish --index testpypi

publish: build ## 本番PyPIに公開
	@echo "🚀 本番PyPIに公開中..."
	@echo "⚠️  公開前に以下の確認をお願いします:"
	@echo "   1. PyPIアカウントとAPIトークンが設定されていること"
	@echo "   2. バージョン番号が適切であること"
	@echo "   3. テストPyPIで動作確認済みであること"
	@echo "   4. CHANGELOG.mdが更新されていること"
	@echo "続行するにはEnterを押してください..."
	@read confirm || echo "続行します..."
	@echo "📝 Gitタグを設定中..."
	@VERSION=$(shell grep '^version = ' pyproject.toml | head -1 | sed 's/version = "\(.*\)"/\1/'); \
	echo "現在のバージョン: $$VERSION"; \
	if git tag | grep -q "^v$$VERSION$$"; then \
		echo "⚠️  タグ v$$VERSION は既に存在します"; \
	else \
		echo "📝 Gitタグ v$$VERSION を作成中..."; \
		echo "タグメッセージを生成中..."; \
		TAG_MSG="リリースバージョン$$VERSION\n\n$$(awk '/^## \[$$VERSION\]/{f=1; next} /^---/{f=0} f{print}' CHANGELOG.md | head -20)"; \
		git tag -a "v$$VERSION" -m "$$TAG_MSG"; \
		git push origin "v$$VERSION"; \
		echo "✅ Gitタグ v$$VERSION を作成・プッシュしました"; \
	fi
	uv publish

check-pypi: ## PyPIでの公開状況を確認
	@echo "🔍 PyPIの状況を確認中..."
	@curl -s https://pypi.org/pypi/pylay/json | python -c "import sys, json; data = json.load(sys.stdin); print(f'Version: {data.get(\"info\", {}).get(\"version\", \"Not found\")}'); print(f'Published: {len(data.get(\"releases\", {}))} versions')" 2>/dev/null || echo "Not published or error"

check-test-pypi: ## テストPyPIでの公開状況を確認
	@echo "🔍 テストPyPIの状況を確認中..."
	@curl -s https://test.pypi.org/pypi/pylay/json | python -c "import sys, json; data = json.load(sys.stdin); print(f'Version: {data.get(\"info\", {}).get(\"version\", \"Not found\")}'); print(f'Published: {len(data.get(\"releases\", {}))} versions')" 2>/dev/null || echo "Not published or error"
