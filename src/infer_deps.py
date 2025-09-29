#!/usr/bin/env python3
"""
型推論と依存関係抽出のエントリーポイントスクリプト

Usage:
    uv run python src/infer_deps.py <file_path>
"""

import sys
from pathlib import Path
from type_extractor.infer_types import (
    infer_types_from_file,
    extract_existing_annotations,
    merge_inferred_types,
)
from type_extractor.extract_deps import (
    extract_dependencies_from_file,
    convert_graph_to_yaml_spec,
    visualize_dependencies,
)
import yaml


def main() -> None:
    """
    メイン実行関数。
    """
    if len(sys.argv) != 2:
        print("Usage: uv run python src/infer_deps.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not Path(file_path).exists():
        print(f"Error: File {file_path} does not exist.")
        sys.exit(1)

    print(f"Processing {file_path}...")

    # analyzerを使用して解析
    from src.core.analyzer.base import create_analyzer
    from src.core.schemas.pylay_config import PylayConfig
    from src.core.analyzer.graph_processor import GraphProcessor

    config = PylayConfig()
    analyzer = create_analyzer(config, mode="full")
    graph = analyzer.analyze(file_path)

    # 型推論結果表示
    print("推論された型:")
    for node in graph.nodes:
        if node.attributes and "inferred_type" in node.attributes:
            print(f"  {node.name}: {node.attributes['inferred_type']}")

    # 依存関係YAML
    processor = GraphProcessor()
    yaml_spec = processor.convert_graph_to_yaml_spec(graph)

        # YAML出力
        output_yaml = f"{file_path}.deps.yaml"
        with open(output_yaml, "w", encoding="utf-8") as f:
            yaml.dump(yaml_spec, f, default_flow_style=False, allow_unicode=True)

        print(f"依存関係を {output_yaml} に保存しました。")

        # 視覚化（オプション）
        processor.visualize_graph(graph, f"{file_path}.deps.png")

    except Exception as e:
        print(f"依存関係抽出に失敗しました: {e}")


if __name__ == "__main__":
    main()
