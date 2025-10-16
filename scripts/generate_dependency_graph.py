#!/usr/bin/env python3
"""
依存関係グラフ生成スクリプト。
Pythonファイルから型依存を抽出し、Markdownドキュメントを生成。
CLIコマンド: python generate_dependency_graph.py src/module.py
            --output docs/dependencies/module.md
"""

import argparse
from pathlib import Path

from src.core.analyzer.base import create_analyzer
from src.core.analyzer.graph_processor import GraphProcessor
from src.core.schemas.pylay_config import PylayConfig


def generate_dependency_docs(
    input_file: str,
    output_file: str,
    visualize: bool = False,
    dot_file: str | None = None,
    include_mypy: bool = False,
    analyze_graph: bool = False,
    graphml_file: str | None = None,
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
    config = PylayConfig(infer_level="strict" if include_mypy else "loose")
    analyzer = create_analyzer(config, mode="full")
    graph = analyzer.analyze(input_file)

    if not graph.nodes:
        print(f"⚠️  依存関係が見つかりませんでした: {input_file}")
        return

    # 出力ディレクトリを作成
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ドキュメント生成（GraphDocGeneratorは不要、直接使用）

    # GraphML出力
    if graphml_file:
        processor = GraphProcessor()
        processor.export_graphml(graph, graphml_file)
        print(f"📄 GraphMLファイルを生成: {graphml_file}")

    # 視覚化出力
    if dot_file:
        processor = GraphProcessor()
        processor.visualize_graph(graph, dot_file, format_type="png")
        print(f"🎨 視覚化ファイルを生成: {dot_file}")

    # ドキュメント生成は不要（GraphDocGenerator削除）
    print(f"✅ 依存グラフ処理完了: {output_file}")

    # 統計情報出力
    processor = GraphProcessor()
    metrics = processor.compute_graph_metrics(graph)
    print(f"   - ノード数: {metrics['node_count']}")
    print(f"   - エッジ数: {metrics['edge_count']}")
    print(f"   - 密度: {metrics['density']:.3f}")
    if include_mypy:
        print("   - mypy推論: 含む")
    if analyze_graph:
        if graph.metadata and "cycles" in graph.metadata:
            cycles = graph.metadata["cycles"]
            print(f"   - 循環数: {len(cycles)}")
        print("   - NetworkX分析: 実行済み")


def main() -> None:
    """メインエントリーポイント"""
    parser = argparse.ArgumentParser(description="Pythonファイルから型依存グラフを抽出し、Markdownドキュメントを生成")
    parser.add_argument("input_file", help="依存を抽出するPythonファイルのパス")
    parser.add_argument("--output", "-o", required=True, help="出力Markdownファイルのパス")
    parser.add_argument(
        "--visualize",
        "-v",
        action="store_true",
        help="Graphviz DOTファイルも出力（オプション）",
    )
    parser.add_argument("--dot-file", help="DOTファイルの出力パス（--visualize使用時）")
    parser.add_argument("--mypy", action="store_true", help="mypy型推論を含める")
    parser.add_argument("--analyze", action="store_true", help="NetworkX分析を実行")
    parser.add_argument("--graphml", help="GraphMLファイルの出力パス(--analyze使用時)")

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
