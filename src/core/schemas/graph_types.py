"""
グラフ型定義
TypeDependencyGraph, GraphNode, GraphEdge の定義
"""

from typing import Optional, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum


class RelationType(str, Enum):
    """関係の種類を定義する列挙型"""

    DEPENDS_ON = "depends_on"
    INHERITS_FROM = "inherits_from"
    INHERITS = "inherits"  # 互換性のために追加
    IMPLEMENTS = "implements"
    REFERENCES = "references"
    USES = "uses"
    RETURNS = "returns"  # 関数戻り値
    CALLS = "calls"  # 関数呼び出し


class GraphNode(BaseModel):
    """
    グラフのノードを表すクラス

    Attributes:
        id: ノードの一意の識別子 (自動生成可能)
        name: ノードの名前
        node_type: ノードの種類
        qualified_name: 完全修飾名
        attributes: ノードの追加属性
    """

    id: Optional[str] = None
    name: str
    node_type: Literal["class", "function", "module"] | str  # 拡張性を考慮
    qualified_name: Optional[str] = None
    attributes: Optional[dict[str, Any]] = None

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if self.id is None:
            self.id = self.name  # デフォルトで name を id に

    def is_external(self) -> bool:
        """外部モジュールかどうかを判定"""
        if self.qualified_name:
            return not self.qualified_name.startswith("__main__")
        return False


class GraphEdge(BaseModel):
    """
    グラフのエッジを表すクラス

    Attributes:
        source: 始点ノードのID
        target: 終点ノードのID
        relation_type: 関係の種類
        weight: エッジの重み
        attributes: エッジの追加属性
    """

    source: str
    target: str
    relation_type: RelationType
    weight: float = 1.0
    attributes: Optional[dict[str, Any]] = None
    metadata: Optional[dict[str, Any]] = None

    def is_strong_dependency(self) -> bool:
        """強い依存関係かどうかを判定（weight >= 0.8）"""
        return self.weight >= 0.8


class TypeDependencyGraph(BaseModel):
    """
    型依存関係グラフを表すクラス

    Attributes:
        nodes: グラフ内の全てのノード
        edges: グラフ内の全てのエッジ
        metadata: グラフのメタデータ
    """

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    metadata: Optional[dict[str, Any]] = None

    def add_node(self, node: GraphNode) -> None:
        """ノードを追加"""
        if not any(n.id == node.id for n in self.nodes):
            self.nodes.append(node)

    def add_edge(self, edge: GraphEdge) -> None:
        """エッジを追加"""
        if not any(
            e.source == edge.source and e.target == edge.target for e in self.edges
        ):
            self.edges.append(edge)

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """IDでノードを取得"""
        return next((n for n in self.nodes if n.id == node_id), None)

    def get_edges_from(self, node_id: str) -> list[GraphEdge]:
        """ノードからのエッジを取得"""
        return [e for e in self.edges if e.source == node_id]

    def get_edges_to(self, node_id: str) -> list[GraphEdge]:
        """ノードへのエッジを取得"""
        return [e for e in self.edges if e.target == node_id]

    def to_networkx(self) -> "nx.DiGraph":  # type: ignore
        """NetworkX DiGraph に変換"""
        try:
            import networkx as nx
        except ImportError:
            raise ImportError("networkx is required for to_networkx()")

        graph = nx.DiGraph()
        for node in self.nodes:
            graph.add_node(node.id, **(node.attributes or {}))
        for edge in self.edges:
            graph.add_edge(
                edge.source,
                edge.target,
                relation_type=edge.relation_type,
                **(edge.attributes or {}),
            )
        return graph

    @classmethod
    def from_networkx(cls, graph: "nx.DiGraph") -> "TypeDependencyGraph":  # type: ignore
        """NetworkX DiGraph から構築"""
        try:
            import networkx as nx
        except ImportError:
            raise ImportError("networkx is required for from_networkx()")

        nodes = []
        edges = []

        for node_id, node_attrs in graph.nodes(data=True):
            node_attrs = dict(node_attrs)
            node_type = node_attrs.pop("node_type", "unknown")
            nodes.append(
                GraphNode(
                    id=node_id, name=node_id, node_type=node_type, attributes=node_attrs
                )
            )

        for source, target, edge_attrs in graph.edges(data=True):
            edge_attrs = dict(edge_attrs)
            relation_type = edge_attrs.pop("relation_type", "depends_on")
            edges.append(
                GraphEdge(
                    source=source,
                    target=target,
                    relation_type=relation_type,
                    attributes=edge_attrs,
                )
            )

        return cls(nodes=nodes, edges=edges)
