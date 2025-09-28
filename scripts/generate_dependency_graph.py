#!/usr/bin/env python3
"""
依存関係グラフ生成スクリプト。
Pythonファイルから型依存を抽出し、Markdownドキュメントを生成。
CLIコマンド: python generate_dependency_graph.py src/module.py --output docs/dependencies/module.md
"""

import argparse
from pathlib import Path
from typing import Optional

from src.core.converters.ast_dependency_extractor import ASTDependencyExtractor
from src.core.doc_generators.graph_doc_generator import GraphDocGenerator


def generate_dependency_docs(
    input_file: str,
    output_file: str,
    visualize: bool = False,
    dot_file: Optional[str] = None,
    include_mypy: bool = False,
    analyze_graph: bool = False,
    graphml_file: Optional[str] = None,
) -> None:
    """
    Pythonファイルから依存グラフを抽出し、ドキュメントを生成。

    Args:
        input_file: 入力Pythonファイルパス
        output_file: 出力Markdownファイルパス
        visualize: 視覚化（DOTファイル）を出力するかどうか
        dot_file: DOTファイル出力パス（オプション）
        include_mypy: mypy型推論を含めるかどうか
        analyze_graph: NetworkX分析を実行するかどうか
        graphml_file: GraphMLファイル出力パス（オプション）
    """
    # 依存関係を抽出
    extractor = ASTDependencyExtractor()
    graph = extractor.extract_dependencies(input_file, include_mypy=include_mypy)

    if not graph.nodes:
        print(f"⚠️  依存関係が見つかりませんでした: {input_file}")
        return

    # 出力ディレクトリを作成
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ドキュメント生成
    generator = GraphDocGenerator()

    # NetworkX分析（オプション）
    if analyze_graph:
        from utils.graph_networkx_adapter import NetworkXGraphAdapter

        nx_adapter = NetworkXGraphAdapter(graph)

        # グラフ統計
        stats = nx_adapter.get_graph_statistics()
        print("📊 グラフ統計:")
        for key, value in stats.items():
            print(f"   - {key}: {value}")

        # 循環検出
        cycles = nx_adapter.detect_cycles()
        if cycles:
            print(f"🔄 循環参照検出: {len(cycles)}個")
            for i, cycle in enumerate(cycles[:3]):  # 最初の3つを表示
                print(f"   - 循環 {i + 1}: {' -> '.join(cycle)}")
        else:
            print("✅ 循環参照なし")

        # GraphML出力
        if graphml_file:
            graphml_path = Path(graphml_file)
            nx_adapter.export_to_graphml(graphml_path)
            print(f"📄 GraphMLファイルを生成: {graphml_file}")

        # 視覚化出力
        if dot_file:
            dot_path = Path(dot_file)
            svg_file = (
                dot_file.replace(".dot", ".svg")
                if dot_file.endswith(".dot")
                else f"{dot_file}.svg"
            )
            svg_path = Path(svg_file)
            nx_adapter.export_visualization(
                dot_path, svg_path if svg_path != dot_path else None
            )
            print(f"🎨 視覚化ファイルを生成: {dot_file}")
            if svg_path != dot_path:
                print(f"   - DOT: {dot_file}")
                print(f"   - SVG: {svg_file}")

    # 視覚化オプション付きで生成
    if visualize and dot_file:
        dot_path = Path(dot_file)
        generator.generate_with_visualization(
            output_path, graph=graph, dot_file=dot_path
        )
        print(
            f"✅ 依存グラフドキュメントとDOTファイルを生成: {output_file}, {dot_file}"
        )
    else:
        generator.generate(output_path, graph=graph)
        print(f"✅ 依存グラフドキュメントを生成: {output_file}")

    # 統計情報出力
    metadata = graph.metadata or {}
    print(f"   - ノード数: {metadata.get('node_count', 0)}")
    print(f"   - エッジ数: {metadata.get('edge_count', 0)}")
    if include_mypy:
        print("   - mypy推論: 含む")
    if analyze_graph:
        print("   - NetworkX分析: 実行済み")


def main() -> None:
    """メインエントリーポイント"""
    parser = argparse.ArgumentParser(
        description="Pythonファイルから型依存グラフを抽出し、Markdownドキュメントを生成"
    )
    parser.add_argument("input_file", help="依存を抽出するPythonファイルのパス")
    parser.add_argument(
        "--output", "-o", required=True, help="出力Markdownファイルのパス"
    )
    parser.add_argument(
        "--visualize",
        "-v",
        action="store_true",
        help="Graphviz DOTファイルも出力（オプション）",
    )
    parser.add_argument("--dot-file", help="DOTファイルの出力パス（--visualize使用時）")
    parser.add_argument("--mypy", action="store_true", help="mypy型推論を含める")
    parser.add_argument("--analyze", action="store_true", help="NetworkX分析を実行")
    parser.add_argument(
        "--graphml", help="GraphMLファイルの出力パス（--analyze使用時）"
    )

    args = parser.parse_args()

    # 引数検証
    if args.visualize and not args.dot_file:
        parser.error("--visualizeを使用する場合は--dot-fileを指定してください")
    if args.analyze and not args.graphml:
        parser.error("--analyzeを使用する場合は--graphmlを指定してください")

    # 生成実行
    generate_dependency_docs(
        input_file=args.input_file,
        output_file=args.output,
        visualize=args.visualize,
        dot_file=args.dot_file,
        include_mypy=args.mypy,
        analyze_graph=args.analyze,
        graphml_file=args.graphml,
    )


if __name__ == "__main__":
    main()
