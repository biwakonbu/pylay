"""
グラフドキュメントジェネレーター。
TypeDependencyGraphからMarkdownドキュメントを生成。
ミニマム版：テキストベースの依存リストとテーブル形式。
"""

from pathlib import Path
from typing import Any, Optional

from .base import DocumentGenerator
from .markdown_builder import MarkdownBuilder

from src.core.schemas.graph_types import TypeDependencyGraph, GraphNode, GraphEdge


class GraphDocGenerator(DocumentGenerator):
    """
    型依存グラフからドキュメントを生成するクラス。
    テキストベースのMarkdown出力（テーブルとリスト形式）。
    """

    def generate(self, output_path: Path, **kwargs: Any) -> None:
        """
        依存グラフからMarkdownドキュメントを生成。

        Args:
            output_path: 出力ファイルパス
            graph: TypeDependencyGraphインスタンス
            **kwargs: 追加オプション（例: include_visualization）
        """
        graph = kwargs.get("graph")
        if not graph:
            raise ValueError("graph parameter is required")

        self.md.clear()
        self.md = MarkdownBuilder()

        # ヘッダー生成
        self._generate_header(graph)

        # 依存グラフの詳細生成
        self._generate_graph_details(graph)

        # ノード一覧テーブル
        self._generate_node_table(graph.nodes)

        # エッジ一覧テーブル
        self._generate_edge_table(graph.edges)

        # フッター生成
        self._generate_footer()

        # ファイル出力
        content = self.md.build()
        self._write_file(output_path, content)

    def _generate_header(self, graph: TypeDependencyGraph) -> None:
        """ヘッダーセクションを生成"""
        metadata = graph.metadata or {}
        source_file = metadata.get("source_file", "不明")
        node_count = metadata.get("node_count", 0)
        edge_count = metadata.get("edge_count", 0)

        self.md.heading(1, "型依存関係グラフ")
        self.md.paragraph(f"**ソースファイル**: {source_file}")
        self.md.paragraph(f"**ノード数**: {node_count}")
        self.md.paragraph(f"**エッジ数**: {edge_count}")
        self.md.paragraph(
            "このドキュメントはPython AST解析による型依存関係を自動生成したものです。"
        )

    def _generate_graph_details(self, graph: TypeDependencyGraph) -> None:
        """グラフの詳細セクションを生成"""
        self.md.heading(2, "依存関係の概要")

        # 依存関係の統計を取得
        summary = graph.get_dependency_summary()

        self.md.paragraph(f"**総ノード数**: {summary['node_count']}")
        self.md.paragraph(f"**総エッジ数**: {summary['edge_count']}")
        self.md.paragraph(f"**強い依存関係数**: {summary['strong_dependencies']}")

        # ノードタイプの分布
        self.md.paragraph("**ノードタイプ分布**:")
        for node_type, count in summary["node_types"].items():
            self.md.bullet_point(f"{node_type}: {count}個")

        # エッジタイプの分布
        self.md.paragraph("**エッジタイプ分布**:")
        for relation_type, count in summary["relations"].items():
            self.md.bullet_point(f"{relation_type}: {count}個")

        # 外部依存の検出
        external_nodes = [node for node in graph.nodes if node.is_external()]
        if external_nodes:
            self.md.paragraph(f"**外部依存**: {len(external_nodes)}個")
            external_names = [node.name for node in external_nodes]
            self.md.paragraph(f"外部型: {', '.join(external_names)}")

    def _generate_node_table(self, nodes: list[GraphNode]) -> None:
        """ノード一覧テーブルを生成"""
        if not nodes:
            self.md.paragraph("ノードはありません。")
            return

        self.md.heading(2, "ノード一覧")
        self.md.paragraph("| 名前 | タイプ | 位置 | 外部 |")
        self.md.paragraph("|------|--------|------|------|")

        for node in nodes:
            location = (
                f"{node.source_file}:{node.line_number}"
                if node.source_file and node.line_number
                else "不明"
            )
            is_external = "✓" if node.is_external() else ""
            self.md.paragraph(
                f"| {node.get_display_name()} | {node.node_type} | {location} | {is_external} |"
            )

    def _generate_edge_table(self, edges: list[GraphEdge]) -> None:
        """エッジ一覧テーブルを生成"""
        if not edges:
            self.md.paragraph("エッジはありません。")
            return

        self.md.heading(2, "エッジ一覧")
        self.md.paragraph("| 起点 | 終点 | 関係 | 重み | 強さ |")
        self.md.paragraph("|------|------|------|------|------|")

        for edge in edges:
            strength = edge.get_dependency_strength()
            is_strong = "✓" if edge.is_strong_dependency() else ""
            self.md.paragraph(
                f"| {edge.source} | {edge.target} | {edge.relation_type} | {edge.weight} | {strength} {is_strong} |"
            )

    def _generate_footer(self) -> None:
        """フッターセクションを生成"""
        self.md.paragraph("---")
        self.md.paragraph(
            "このドキュメントはpylayの依存関係抽出機能により自動生成されました。"
        )
        self.md.paragraph("更新日時: 自動生成")  # 実際にはdatetimeを使用

    def generate_with_visualization(
        self,
        output_path: Path,
        graph: TypeDependencyGraph,
        dot_file: Optional[Path] = None,
    ) -> None:
        """
        視覚化オプション付きで生成（Graphviz統合準備）。

        Args:
            output_path: Markdown出力パス
            graph: TypeDependencyGraphインスタンス
            dot_file: Graphviz DOTファイル出力パス（オプション）
        """
        # 基本生成
        self.generate(output_path, graph=graph)

        # Graphviz DOTファイル生成（オプション）
        if dot_file:
            self._generate_dot_file(dot_file, graph)

    def _generate_dot_file(self, dot_path: Path, graph: TypeDependencyGraph) -> None:
        """Graphviz DOTファイルを生成（ミニマム版）"""
        lines = ["digraph DependencyGraph {"]
        lines.append("  rankdir=TB;")  # 上から下へ

        # ノード定義
        for node in graph.nodes:
            node_type = node.node_type
            lines.append(
                f'  "{node.name}" [label="{node.name}\\n({node_type})", shape=box];'
            )

        # エッジ定義
        for edge in graph.edges:
            lines.append(
                f'  "{edge.source}" -> "{edge.target}" [label="{edge.relation_type}"];'
            )

        lines.append("}")

        # ファイル出力
        dot_content = "\n".join(lines)
        with open(dot_path, "w", encoding="utf-8") as f:
            f.write(dot_content)
