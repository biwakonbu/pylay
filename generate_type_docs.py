# scripts/generate_type_docs.py - 静的型から完全自動成長ドキュメント生成
"""
Refactored type documentation generator.

This script maintains backward compatibility while using the new
modular architecture for better testability and maintainability.
"""

from pathlib import Path
from typing import Any

from doc_generators.config import TypeDocConfig
from doc_generators.type_doc_generator import IndexDocGenerator, LayerDocGenerator
from schemas.type_index import TYPE_REGISTRY, build_registry


def generate_layer_docs(layer: str, types: dict[str, type[Any]], output_dir: str = "docs/types") -> None:
    """レイヤー別型ドキュメント生成（完全自動成長対応）

    Args:
        layer: Layer name
        types: Dictionary of types in the layer
        output_dir: Output directory path
    """
    config = TypeDocConfig(
        output_directory=Path(output_dir)
    )

    generator = LayerDocGenerator(config=config)
    output_path = Path(output_dir) / f"{layer}.md"
    generator.generate(layer, types, output_path)


def generate_index_docs(output_path: str = "docs/type_index.md") -> None:
    """インデックスファイル生成: レイヤー別リンクと統一利用方法

    Args:
        output_path: Output file path
    """
    config = TypeDocConfig()

    generator = IndexDocGenerator(config=config)
    generator.generate(TYPE_REGISTRY, Path(output_path))


def generate_docs(output_dir: str = "docs/types") -> None:
    """静的型からレイヤー別typeカタログを生成

    Args:
        output_dir: Output directory path
    """
    build_registry()  # 静的リビルド

    for layer, layer_types in TYPE_REGISTRY.items():
        if layer_types:  # 空でないレイヤーのみ処理
            generate_layer_docs(layer, list(layer_types.values()), output_dir)

    generate_index_docs(f"{output_dir}/README.md")

    total_types = sum(len(layer_types) for layer_types in TYPE_REGISTRY.values())
    print(f"✅ Generated layer docs in {output_dir}: {total_types} types")


if __name__ == "__main__":
    generate_docs()
