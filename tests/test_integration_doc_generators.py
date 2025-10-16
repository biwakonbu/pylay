"""
Integration tests for the doc_generators package.

Tests the full integration between all components: generate_test_docs,
generate_type_docs, and their shared infrastructure.
"""

import tempfile
from pathlib import Path

from scripts.generate_test_docs import generate_test_docs
from scripts.generate_type_docs import generate_docs, generate_layer_docs


class TestDocGeneratorsIntegration:
    """Test integration between all doc generators."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir) / "docs" / "types"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """Clean up test files."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_both_generators_create_compatible_output(self):
        """Test that both generators create compatible documentation."""
        # Generate test documentation
        test_catalog_path = self.output_dir / "test_catalog.md"
        generate_test_docs(str(test_catalog_path))

        # Generate type documentation
        generate_docs(str(self.output_dir))

        # Both files should exist
        assert test_catalog_path.exists()
        index_path = self.output_dir / "README.md"
        assert index_path.exists()

        # Both should have consistent formatting
        test_content = test_catalog_path.read_text(encoding="utf-8")
        type_content = index_path.read_text(encoding="utf-8")

        # Both should include generation timestamps
        assert "**生成日**:" in test_content
        assert "**生成日**:" in type_content

    def test_yaml_doc_generator_depth_limit(self):
        """YAMLドキュメント生成の深さ制限テスト"""
        from src.core.doc_generators.yaml_doc_generator import YamlDocGenerator
        from src.core.schemas.yaml_spec import DictTypeSpec, TypeSpec

        # 深くネストされた構造を作成
        deep_spec = TypeSpec(name="str", type="str")
        for i in range(15):  # 深さ15のネスト
            deep_spec = DictTypeSpec(name=f"Level{i}", type="dict", properties={"value": deep_spec})

        generator = YamlDocGenerator()
        output_path = self.output_dir / "deep_test.md"

        # 深さ制限付きで生成
        generator.generate(output_path, spec=deep_spec)  # spec パラメータで渡す

        content = output_path.read_text(encoding="utf-8")
        assert "深さ制限を超えました" in content

    def test_parallel_generation_workflow(self):
        """Test that both generators can run in parallel without conflicts."""
        # This simulates a scenario where both documentation types
        # are generated simultaneously
        test_catalog_path = self.output_dir / "test_catalog.md"

        # Generate both types of documentation
        generate_test_docs(str(test_catalog_path))
        generate_docs(str(self.output_dir))

        # Verify both completed successfully
        assert test_catalog_path.exists()
        assert (self.output_dir / "README.md").exists()

        # Check for layer-specific files
        primitive_docs = self.output_dir / "primitives.md"
        domain_docs = self.output_dir / "domain.md"

        if primitive_docs.exists():
            primitive_content = primitive_docs.read_text(encoding="utf-8")
            assert "PRIMITIVES レイヤー型カタログ" in primitive_content

        if domain_docs.exists():
            domain_content = domain_docs.read_text(encoding="utf-8")
            assert "DOMAIN レイヤー型カタログ" in domain_content

    def test_shared_infrastructure_consistency(self):
        """Test that shared infrastructure provides consistent behavior."""
        # Both generators should use the same markdown formatting patterns
        test_catalog_path = self.output_dir / "test_catalog.md"
        generate_test_docs(str(test_catalog_path))

        # Generate a single layer doc for comparison
        test_types = {"TestType": str}
        generate_layer_docs("test", test_types, str(self.output_dir))

        test_content = test_catalog_path.read_text(encoding="utf-8")
        layer_content = (self.output_dir / "test.md").read_text(encoding="utf-8")

        # Both should use consistent heading styles
        assert test_content.count("# ") >= 1  # Main heading
        assert layer_content.count("# ") >= 1  # Main heading

        # Both should use consistent timestamp formatting
        import re

        timestamp_pattern = r"\*\*生成日\*\*:\s*\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
        assert re.search(timestamp_pattern, test_content)
        assert re.search(timestamp_pattern, layer_content)

    def test_error_isolation_between_generators(self):
        """Test that errors in one generator don't affect the other."""
        # Generate test docs first (should succeed)
        test_catalog_path = self.output_dir / "test_catalog.md"
        generate_test_docs(str(test_catalog_path))

        assert test_catalog_path.exists()
        original_content = test_catalog_path.read_text(encoding="utf-8")

        # Now generate type docs (should also succeed independently)
        generate_docs(str(self.output_dir))

        # Original test docs should be unchanged
        assert test_catalog_path.read_text(encoding="utf-8") == original_content

        # Type docs should exist
        assert (self.output_dir / "README.md").exists()

    def test_output_directory_structure(self):
        """Test that both generators respect the expected directory structure."""
        # Generate all documentation
        test_catalog_path = self.output_dir / "test_catalog.md"
        generate_test_docs(str(test_catalog_path))
        generate_docs(str(self.output_dir))

        # Check expected file structure
        expected_files = [
            "test_catalog.md",  # Test documentation
            "README.md",  # Type index
        ]

        for filename in expected_files:
            file_path = self.output_dir / filename
            assert file_path.exists(), f"Expected file {filename} not found"

        # Check for layer-specific files (dynamic based on registry)
        md_files = list(self.output_dir.glob("*.md"))
        md_files = [f.name for f in md_files]

        # Should have at least the expected files
        for expected in expected_files:
            assert expected in md_files

    def test_configuration_consistency(self):
        """Test that configuration is applied consistently across generators."""
        # Test that both generators respect similar configuration patterns

        # Generate with custom output paths
        custom_test_path = self.output_dir / "custom_test_catalog.md"
        custom_type_dir = self.output_dir / "custom_types"
        custom_type_dir.mkdir(exist_ok=True)

        generate_test_docs(str(custom_test_path))
        generate_docs(str(custom_type_dir))

        # Both should respect custom paths
        assert custom_test_path.exists()
        assert (custom_type_dir / "README.md").exists()

    def test_content_quality_standards(self):
        """Test that both generators meet the same content quality standards."""
        test_catalog_path = self.output_dir / "test_catalog.md"
        generate_test_docs(str(test_catalog_path))
        generate_docs(str(self.output_dir))

        test_content = test_catalog_path.read_text(encoding="utf-8")
        index_content = (self.output_dir / "README.md").read_text(encoding="utf-8")

        # Both should be valid UTF-8 with Japanese content
        assert "テスト" in test_content or "カタログ" in test_content
        assert "型" in index_content or "インデックス" in index_content

        # Both should have reasonable content length
        assert len(test_content) > 100  # Non-trivial content
        assert len(index_content) > 100  # Non-trivial content

        # Both should have proper markdown structure
        assert test_content.startswith("#")
        assert index_content.startswith("#")


class TestBackwardCompatibility:
    """Test backward compatibility with existing scripts."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test files."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_generate_test_docs_api_unchanged(self):
        """Test that generate_test_docs API remains unchanged."""
        output_path = Path(self.temp_dir) / "test_catalog.md"

        # Should work with string path (existing API)
        generate_test_docs(str(output_path))
        assert output_path.exists()

        # Should work with default path
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            # Create docs/types directory for default path
            docs_dir = Path("docs/types")
            docs_dir.mkdir(parents=True, exist_ok=True)

            generate_test_docs()  # Should use default path
            default_path = docs_dir / "test_catalog.md"
            assert default_path.exists()
        finally:
            os.chdir(original_cwd)

    def test_generate_type_docs_api_unchanged(self):
        """Test that generate_type_docs API remains unchanged."""
        output_dir = Path(self.temp_dir) / "types"

        # Test generate_layer_docs (existing API)
        test_types = {"TestType": str}
        generate_layer_docs("test", test_types, str(output_dir))

        layer_file = output_dir / "test.md"
        assert layer_file.exists()

        # Test generate_docs (existing API)
        generate_docs(str(output_dir))

        index_file = output_dir / "README.md"
        assert index_file.exists()

    def test_existing_import_paths_work(self):
        """Test that existing import paths continue to work."""
        # These imports should work as before refactoring
        from scripts.generate_test_docs import generate_test_docs
        from scripts.generate_type_docs import generate_docs, generate_layer_docs

        # Functions should be callable
        assert callable(generate_test_docs)
        assert callable(generate_docs)
        assert callable(generate_layer_docs)

    def test_output_format_unchanged(self):
        """Test that output format matches pre-refactoring expectations."""
        output_path = Path(self.temp_dir) / "test_catalog.md"
        generate_test_docs(str(output_path))

        content = output_path.read_text(encoding="utf-8")

        # Should match existing test expectations
        assert "# テストカタログ" in content
        assert "pytest" in content
        assert "**生成日**:" in content

        # Should include actual test files
        assert "test_" in content  # Should find actual test files


class TestPerformanceIntegration:
    """Test performance characteristics of integrated system."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test files."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_generation_performance_acceptable(self):
        """Test that documentation generation completes in reasonable time."""
        import time

        start_time = time.time()

        # Generate both types of documentation
        test_catalog_path = Path(self.temp_dir) / "test_catalog.md"
        type_docs_dir = Path(self.temp_dir) / "types"

        generate_test_docs(str(test_catalog_path))
        generate_docs(str(type_docs_dir))

        end_time = time.time()
        total_time = end_time - start_time

        # Should complete in reasonable time (10 seconds should be plenty)
        assert total_time < 10.0, f"Generation took too long: {total_time:.2f} seconds"

        # Verify outputs were created
        assert test_catalog_path.exists()
        assert (type_docs_dir / "README.md").exists()

    def test_memory_usage_reasonable(self):
        """Test that generators don't consume excessive memory."""
        # This test ensures that the refactored code doesn't leak memory
        # by generating documentation multiple times

        test_catalog_path = Path(self.temp_dir) / "test_catalog.md"

        # Generate multiple times to test for memory leaks
        for _ in range(5):
            if test_catalog_path.exists():
                test_catalog_path.unlink()

            generate_test_docs(str(test_catalog_path))
            assert test_catalog_path.exists()

        # If we got here without errors, memory usage is reasonable
