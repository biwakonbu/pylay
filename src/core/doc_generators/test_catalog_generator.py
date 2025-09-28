"""Test catalog generator for automated test documentation."""

import inspect
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .base import DocumentGenerator
from .config import CatalogConfig


class CatalogGenerator(DocumentGenerator):
    """Generator for test catalog documentation."""

    def __init__(
        self,
        config: CatalogConfig | None = None,
        **kwargs: object,
    ) -> None:
        """Initialize test catalog generator.

        Args:
            config: Configuration for test catalog generation
            **kwargs: Additional arguments passed to parent constructor
        """
        # Extract filesystem and markdown_builder from kwargs with proper typing
        from .filesystem import FileSystemInterface
        from .markdown_builder import MarkdownBuilder

        filesystem = kwargs.pop("filesystem", None)
        markdown_builder = kwargs.pop("markdown_builder", None)

        # Type assertions for dependency injection
        fs_typed = (
            filesystem
            if isinstance(filesystem, FileSystemInterface) or filesystem is None
            else None
        )
        md_typed = (
            markdown_builder
            if isinstance(markdown_builder, MarkdownBuilder) or markdown_builder is None
            else None
        )

        super().__init__(filesystem=fs_typed, markdown_builder=md_typed)
        self.config = config or CatalogConfig()

    def generate(self, output_path: Path | None = None, **kwargs: object) -> None:
        """Generate test catalog documentation.

        Args:
            output_path: Optional override for output path
            **kwargs: Additional configuration parameters
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
        """Generate document header."""
        self.md.heading(1, "テストカタログ").line_break()
        timestamp_info = f"**生成日**: {self._format_timestamp()}"
        self.md.paragraph(timestamp_info).line_break()

    def _generate_test_modules(self) -> None:
        """Generate documentation for all test modules."""
        test_files = self._scan_test_modules()

        for test_file in test_files:
            self._generate_module_section(test_file)

    def _generate_module_section(self, test_file: Path) -> None:
        """Generate documentation section for a single test module.

        Args:
            test_file: Path to the test file
        """
        self.md.heading(2, test_file.name).line_break()

        try:
            module = self._import_module(test_file)
            test_functions = self._extract_test_functions(module)

            for func_name, func in test_functions:
                self._generate_test_function_entry(func_name, func, test_file)

        except (ImportError, RecursionError, Exception) as e:
            error_type = type(e).__name__
            self.md.paragraph(
                f"⚠️ モジュールの処理に失敗 ({error_type}): {str(e)[:100]}..."
            ).line_break()

    def _generate_test_function_entry(
        self,
        func_name: str,
        func: Callable[..., Any] | type,
        test_file: Path,
    ) -> None:
        """Generate entry for a single test function or class.

        Args:
            func_name: Name of the test function or class
            func: The test function object or class
            test_file: Path to the test file containing the function
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
        """Generate summary statistics."""
        module_count = self._count_test_modules()
        self.md.paragraph(f"**総テストモジュール数**: {module_count}")

    def _scan_test_modules(self) -> list[Path]:
        """Scan for test modules in the configured directory.

        Returns:
            List of test module paths
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
            if not any(
                pattern in str(test_file) for pattern in self.config.exclude_patterns
            ):
                filtered_files.append(test_file)

        return sorted(filtered_files)

    def _extract_test_functions(
        self, module: object
    ) -> list[tuple[str, Callable[..., Any]]]:
        """Extract test functions and methods from a module.

        Args:
            module: The imported test module

        Returns:
            List of (function_name, function) tuples
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
        """Import a test module dynamically.

        Args:
            test_file: Path to the test file

        Returns:
            The imported module

        Raises:
            ImportError: If module cannot be imported
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
        """Count the number of test modules.

        Returns:
            Number of test modules found
        """
        test_files = self._scan_test_modules()
        return len([f for f in test_files if f.stem.startswith("test_")])
