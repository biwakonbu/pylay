"""自動テストドキュメント生成用のテストカタログジェネレーター。"""

import inspect
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .base import DocumentGenerator
from .config import CatalogConfig


class CatalogGenerator(DocumentGenerator):
    """テストカタログドキュメントのジェネレーター。"""

    def __init__(
        self,
        config: CatalogConfig | None = None,
        **kwargs: object,
    ) -> None:
        """テストカタログジェネレーターを初期化する。

        Args:
            config: テストカタログ生成の設定
            **kwargs: 親コンストラクタに渡される追加引数
        """
        # Extract filesystem and markdown_builder from kwargs with proper typing
        from .filesystem import FileSystemInterface
        from .markdown_builder import MarkdownBuilder

        filesystem_raw = kwargs.pop("filesystem", None)
        markdown_builder_raw = kwargs.pop("markdown_builder", None)

        # 型キャストで型安全性を保証
        filesystem = (
            filesystem_raw if isinstance(filesystem_raw, FileSystemInterface) or filesystem_raw is None else None
        )
        markdown_builder = (
            markdown_builder_raw
            if isinstance(markdown_builder_raw, MarkdownBuilder) or markdown_builder_raw is None
            else None
        )

        super().__init__(filesystem=filesystem, markdown_builder=markdown_builder)
        self.config = config or CatalogConfig()

    def generate(self, output_path: Path | None = None, **kwargs: object) -> None:
        """テストカタログドキュメントを生成する。

        Args:
            output_path: 出力パスのオプション上書き
            **kwargs: 追加の設定パラメータ
        """
        final_output_path = output_path or self.config.output_path

        # Clear markdown builder
        self.md.clear()

        # Build document
        self._generate_header()
        self._generate_test_modules()
        self._generate_summary()

        # Write to file
        content = self.md.build()
        self._write_file(final_output_path, content)

        print(f"✅ Generated {final_output_path}: {self._count_test_modules()} modules")

    def _generate_header(self) -> None:
        """ドキュメントヘッダーを生成する。"""
        self.md.heading(1, "テストカタログ").line_break()
        timestamp_info = f"**生成日**: {self._format_timestamp()}"
        self.md.paragraph(timestamp_info).line_break()

    def _generate_test_modules(self) -> None:
        """すべてのテストモジュールのドキュメントを生成する。"""
        test_files = self._scan_test_modules()

        for test_file in test_files:
            self._generate_module_section(test_file)

    def _generate_module_section(self, test_file: Path) -> None:
        """単一のテストモジュールのドキュメントセクションを生成する。

        Args:
            test_file: テストファイルへのパス
        """
        self.md.heading(2, test_file.name).line_break()

        try:
            module = self._import_module(test_file)
            test_functions = self._extract_test_functions(module)

            for func_name, func in test_functions:
                self._generate_test_function_entry(func_name, func, test_file)

        except (ImportError, RecursionError, Exception) as e:
            error_type = type(e).__name__
            self.md.paragraph(f"⚠️ モジュールの処理に失敗 ({error_type}): {str(e)[:100]}...").line_break()

    def _generate_test_function_entry(
        self,
        func_name: str,
        func: Callable[..., Any] | type,
        test_file: Path,
    ) -> None:
        """単一のテスト関数またはクラスのエントリを生成する。

        Args:
            func_name: テスト関数またはクラスの名前
            func: テスト関数オブジェクトまたはクラス
            test_file: 関数を含むテストファイルへのパス
        """
        self.md.heading(3, func_name)

        # Get docstring or use default
        docstring = inspect.getdoc(func) or "説明なし"
        self.md.paragraph(f"**説明**: {docstring}").line_break()

        # Add pytest command
        if inspect.isclass(func):
            # For test classes, run all methods in the class
            pytest_cmd = f"pytest {test_file}::{func_name} -v"
        else:
            # For test functions
            pytest_cmd = f"pytest {test_file}::{func_name} -v"
        self.md.paragraph(f"**実行**: `{pytest_cmd}`").line_break()

    def _generate_summary(self) -> None:
        """要約統計情報を生成する。"""
        module_count = self._count_test_modules()
        self.md.paragraph(f"**総テストモジュール数**: {module_count}")

    def _scan_test_modules(self) -> list[Path]:
        """設定されたディレクトリ内のテストモジュールをスキャンする。

        Returns:
            テストモジュールパスのリスト
        """
        test_dir = self.config.test_directory

        if not test_dir.exists():
            return []

        test_files: list[Path] = []
        for pattern in self.config.include_patterns:
            test_files.extend(test_dir.glob(pattern))

        # Filter out excluded patterns
        filtered_files = []
        for test_file in test_files:
            if not any(pattern in str(test_file) for pattern in self.config.exclude_patterns):
                filtered_files.append(test_file)

        return sorted(filtered_files)

    def _extract_test_functions(self, module: object) -> list[tuple[str, Callable[..., Any]]]:
        """モジュールからテスト関数とメソッドを抽出する。

        Args:
            module: インポートされたテストモジュール

        Returns:
            (関数名, 関数)タプルのリスト
        """
        test_functions: list[tuple[str, Callable[..., Any]]] = []
        members: list[tuple[str, Any]] = inspect.getmembers(module)

        for member_name, member in members:
            # Direct test functions
            if inspect.isfunction(member) and member_name.startswith("test_"):
                test_functions.append((member_name, member))

            # Test methods in test classes
            elif inspect.isclass(member) and member_name.startswith("Test"):
                # Skip test classes - only extract test methods

                class_methods = inspect.getmembers(member, inspect.isfunction)
                for method_name, method in class_methods:
                    if method_name.startswith("test_"):
                        full_name = f"{member_name}.{method_name}"
                        test_functions.append((full_name, method))

        return test_functions

    def _import_module(self, test_file: Path) -> object:
        """テストモジュールを動的にインポートする。

        Args:
            test_file: テストファイルへのパス

        Returns:
            インポートされたモジュール

        Raises:
            ImportError: モジュールをインポートできない場合
        """
        # Convert file path to module name relative to test directory
        try:
            relative_path = test_file.relative_to(self.config.test_directory)
            # Build module path based on test directory structure
            if "schemas" in str(self.config.test_directory):
                module_path = f"tests.schemas.{relative_path.stem}"
            elif "scripts" in str(self.config.test_directory):
                module_path = f"tests.scripts.{relative_path.stem}"
            else:
                # Generic approach
                test_dir_parts = self.config.test_directory.parts
                if "tests" in test_dir_parts:
                    tests_index = test_dir_parts.index("tests")
                    remaining_parts = test_dir_parts[tests_index:]
                    module_path = ".".join(remaining_parts) + f".{relative_path.stem}"
                else:
                    module_path = f"tests.{relative_path.stem}"
        except ValueError:
            # Fallback: use the stem directly with tests prefix
            module_path = f"tests.{test_file.stem}"

        return __import__(module_path, fromlist=[""])

    def _count_test_modules(self) -> int:
        """テストモジュールの数をカウントする。

        Returns:
            見つかったテストモジュールの数
        """
        test_files = self._scan_test_modules()
        return len([f for f in test_files if f.stem.startswith("test_")])
