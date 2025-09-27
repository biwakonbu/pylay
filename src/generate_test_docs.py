# scripts/generate_test_docs.py - テスト関数からドキュメント自動生成
"""
Refactored test documentation generator.

This script maintains backward compatibility while using the new
modular architecture for better testability and maintainability.
"""

from pathlib import Path

from scripts.doc_generators.config import CatalogConfig
from scripts.doc_generators.test_catalog_generator import CatalogGenerator


def generate_test_docs(output_path: str = "docs/types/test_catalog.md") -> None:
    """テストファイルからテストカタログを生成

    Args:
        output_path: Path where the test catalog should be written
    """
    # Create configuration
    config = CatalogConfig(
        output_path=Path(output_path)
    )

    # Generate documentation using new architecture
    generator = CatalogGenerator(config=config)
    generator.generate()

if __name__ == "__main__":
    generate_test_docs()
