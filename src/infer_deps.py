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

    # 型推論
    try:
        existing_annotations = extract_existing_annotations(file_path)
        inferred_types = infer_types_from_file(file_path)
        merged_types = merge_inferred_types(existing_annotations, inferred_types)

        print("推論された型:")
        for var, typ in merged_types.items():
            print(f"  {var}: {typ}")

    except Exception as e:
        print(f"型推論に失敗しました: {e}")

    # 依存関係抽出
    try:
        deps_graph = extract_dependencies_from_file(file_path)
        yaml_spec = convert_graph_to_yaml_spec(deps_graph)

        # YAML出力
        output_yaml = f"{file_path}.deps.yaml"
        with open(output_yaml, "w", encoding="utf-8") as f:
            yaml.dump(yaml_spec, f, default_flow_style=False, allow_unicode=True)

        print(f"依存関係を {output_yaml} に保存しました。")

        # 視覚化（オプション）
        visualize_dependencies(deps_graph, f"{file_path}.deps.png")

    except Exception as e:
        print(f"依存関係抽出に失敗しました: {e}")


if __name__ == "__main__":
    main()
