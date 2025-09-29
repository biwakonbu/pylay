# scripts/generate_type_docs.py - 静的型から完全自動成長ドキュメント生成
"""
Refactored type documentation generator.

This script maintains backward compatibility while using the new
modular architecture for better testability and maintainability.
"""

from pathlib import Path
from typing import Any

from src.core.doc_generators.config import TypeDocConfig
from src.core.doc_generators.type_doc_generator import (
    IndexDocGenerator,
    LayerDocGenerator,
)
from src.core.schemas.type_index import TYPE_REGISTRY, build_registry


def generate_layer_docs(
    layer: str, types: dict[str, type[Any]], output_dir: str | None = None
) -> None:
    """レイヤー別型ドキュメント生成（完全自動成長対応）

    Args:
        layer: Layer name
        types: Dictionary of types in the layer
        output_dir: Output directory path（デフォルト: 設定ファイルに基づく）
    """
    if output_dir is None:
        try:
            from src.core.schemas.pylay_config import PylayConfig
            from src.core.output_manager import OutputPathManager

            config_pylay = PylayConfig.from_pyproject_toml()
            output_manager = OutputPathManager(config_pylay)
            output_dir = str(output_manager.get_output_structure()["markdown"])
        except Exception:
            output_dir = "docs/pylay-types/documents"

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    config = TypeDocConfig(output_directory=Path(output_dir))

    generator = LayerDocGenerator(config=config)
    output_path = Path(output_dir) / f"{layer}.md"
    generator.generate(output_path, layer=layer, types=types)


def generate_index_docs(output_path: str | None = None) -> None:
    """インデックスファイル生成: レイヤー別リンクと統一利用方法

    Args:
        output_path: Output path（デフォルト: 設定ファイルに基づく）
    """
    if output_path is None:
        try:
            from src.core.schemas.pylay_config import PylayConfig
            from src.core.output_manager import OutputPathManager

            config_pylay = PylayConfig.from_pyproject_toml()
            output_manager = OutputPathManager(config_pylay)
            output_path = str(
                output_manager.get_markdown_path(filename="type_index.md")
            )
        except Exception:
            output_path = "docs/pylay-types/documents/type_index.md"

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # 既存の docstring は上にあるので、ここは不要
    config = TypeDocConfig()

    generator = IndexDocGenerator(config=config)
    generator.generate(Path(output_path), type_registry=TYPE_REGISTRY)


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
