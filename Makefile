# pylay プロジェクトのMakefile
# uvを使ったPythonプロジェクト管理

.PHONY: help install sync clean format lint type-check test quality-check all-check coverage

# デフォルトターゲット
help: ## このMakefileのヘルプを表示
	@echo "pylay プロジェクトのMakefile"
	@echo "使用可能なコマンド:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## 依存関係をインストール
	uv sync

sync: install ## 依存関係を同期（エイリアス）

format: ## コードをフォーマット（Ruff）
	uv run ruff format .

lint: ## リンターでコードチェック（Ruff）
	uv run ruff check . --fix

type-check: ## 型チェック（mypy）
	uv run mypy src/core/converters/type_to_yaml.py src/core/converters/yaml_to_type.py src/core/doc_generators/yaml_doc_generator.py src/core/doc_generators/base.py src/core/doc_generators/config.py src/core/schemas/yaml_type_spec.py src/core/schemas/type_index.py src/core/converters/mypy_type_extractor.py src/core/converters/ast_dependency_extractor.py src/core/converters/infer_types.py src/core/converters/extract_deps.py src/infer_deps.py tests/test_type_inference.py tests/test_dependency_extraction.py

test: ## テストを実行
	uv run pytest --cov=. --cov-report=html --cov-report=xml --cov-report=term

test-fast: ## 高速テスト実行（カバレッジなし）
	uv run pytest

coverage: test ## カバレッジレポートを開く
	@echo "Coverage report generated in htmlcov/index.html"
	@if command -v open >/dev/null 2>&1; then \
		open htmlcov/index.html; \
	elif command -v xdg-open >/dev/null 2>&1; then \
		xdg-open htmlcov/index.html; \
	else \
		echo "Open htmlcov/index.html in your browser"; \
	fi

quality-check: ## 品質チェック（型チェック + リンター）
	uv run mypy src/core/converters/type_to_yaml.py src/core/converters/yaml_to_type.py src/core/doc_generators/yaml_doc_generator.py src/core/doc_generators/base.py src/core/doc_generators/config.py src/core/schemas/yaml_type_spec.py src/core/schemas/type_index.py src/core/schemas/graph_types.py src/core/converters/infer_types.py src/core/converters/extract_deps.py tests/test_graph_types.py tests/test_type_inference.py tests/test_dependency_extraction.py
	uv run ruff check .

pre-commit-install: ## pre-commitフックをインストール
	uv run pre-commit install

pre-commit-run: ## pre-commitチェックを実行
	uv run pre-commit run --all-files

safety-check: ## 依存関係のセキュリティチェック
	uv run safety check --file pyproject.toml

radon-check: ## コード複雑度チェック
	uv run radon cc . -s --total-average

interrogate-check: ## docstringカバレッジチェック
	uv run interrogate .

infer-deps: ## 型推論と依存関係抽出を実行（例: make infer-deps FILE=src/example.py）
	uv run python src/infer_deps.py $(FILE)

tui-run: ## TUI アプリを起動
	uv run python -m src.tui.main

tui-test: ## TUI 関連テストを実行
	uv run pytest tests/test_tui/

all-check: format type-check test quality-check ## すべてのチェックを実行（フォーマット → 型チェック → テスト → 品質チェック）

clean: ## キャッシュと一時ファイルをクリーンアップ
	uv run ruff clean
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/ 2>/dev/null || true
	rm -rf dist/ build/ 2>/dev/null || true

dev: ## 開発環境をセットアップ（インストール + pre-commitインストール）
	$(MAKE) install
	$(MAKE) pre-commit-install

ci: ## CIで実行する全チェック
	$(MAKE) all-check
	$(MAKE) safety-check
	$(MAKE) radon-check
	$(MAKE) interrogate-check
