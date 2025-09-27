#!/usr/bin/env python3
"""
依存関係グラフ生成スクリプト。
Pythonファイルから型依存を抽出し、Markdownドキュメントを生成。
CLIコマンド: python generate_dependency_graph.py src/module.py --output docs/dependencies/module.md
"""

import argparse
from pathlib import Path
from typing import Optional

from converters.ast_dependency_extractor import ASTDependencyExtractor
from doc_generators.config import TypeDocConfig
from doc_generators.graph_doc_generator import GraphDocGenerator


def generate_dependency_docs(
    input_file: str,
    output_file: str,
    visualize: bool = False,
    dot_file: Optional[str] = None
) -> None:
    """
    Pythonファイルから依存グラフを抽出し、ドキュメントを生成。

    Args:
        input_file: 入力Pythonファイルパス
        output_file: 出力Markdownファイルパス
        visualize: 視覚化（DOTファイル）を出力するかどうか
        dot_file: DOTファイル出力パス（オプション）
    """
    # 依存関係を抽出
    extractor = ASTDependencyExtractor()
    graph = extractor.extract_dependencies(input_file)

    if not graph.nodes:
        print(f"⚠️  依存関係が見つかりませんでした: {input_file}")
        return

    # 出力ディレクトリを作成
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ドキュメント生成
    generator = GraphDocGenerator()

    # 視覚化オプション付きで生成
    if visualize and dot_file:
        dot_path = Path(dot_file)
        generator.generate_with_visualization(output_path, graph=graph, dot_file=dot_path)
        print(f"✅ 依存グラフドキュメントとDOTファイルを生成: {output_file}, {dot_file}")
    else:
        generator.generate(output_path, graph=graph)
        print(f"✅ 依存グラフドキュメントを生成: {output_file}")

    # 統計情報出力
    metadata = graph.metadata or {}
    print(f"   - ノード数: {metadata.get('node_count', 0)}")
    print(f"   - エッジ数: {metadata.get('edge_count', 0)}")


def main() -> None:
    """メインエントリーポイント"""
    parser = argparse.ArgumentParser(
        description="Pythonファイルから型依存グラフを抽出し、Markdownドキュメントを生成"
    )
    parser.add_argument(
        "input_file",
        help="依存を抽出するPythonファイルのパス"
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="出力Markdownファイルのパス"
    )
    parser.add_argument(
        "--visualize", "-v",
        action="store_true",
        help="Graphviz DOTファイルも出力（オプション）"
    )
    parser.add_argument(
        "--dot-file",
        help="DOTファイルの出力パス（--visualize使用時）"
    )

    args = parser.parse_args()

    # 引数検証
    if args.visualize and not args.dot_file:
        parser.error("--visualizeを使用する場合は--dot-fileを指定してください")

    # 生成実行
    generate_dependency_docs(
        input_file=args.input_file,
        output_file=args.output,
        visualize=args.visualize,
        dot_file=args.dot_file
    )


if __name__ == "__main__":
    main()
