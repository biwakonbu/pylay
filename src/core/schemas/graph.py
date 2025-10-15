"""
グラフ型定義
TypeDependencyGraph, GraphNode, GraphEdge の定義
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.core.schemas.types import (
    FilePath,
    GraphMetadata,
    LineNumber,
    NodeAttributes,
    NodeId,
    NodeType,
    QualifiedName,
    Weight,
)


class RelationType(str, Enum):
    """関係の種類を定義する列挙型"""

    DEPENDS_ON = "depends_on"
    INHERITS_FROM = "inherits_from"  # クラス継承（正規名）
    IMPLEMENTS = "implements"
    REFERENCES = "references"
    USES = "uses"
    RETURNS = "returns"  # 関数戻り値
    CALLS = "calls"  # 関数呼び出し
    ARGUMENT = "argument"  # 関数引数
    ASSIGNMENT = "assignment"  # 変数代入
    GENERIC = "generic"  # ジェネリック型


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

    id: NodeId | None = None
    name: str
    node_type: NodeType  # Literal["class", "function", "module", "unknown"]
    qualified_name: QualifiedName | None = None
    attributes: NodeAttributes | None = None
    source_file: FilePath | None = None  # ソースファイルパス
    line_number: LineNumber | None = None  # ソースコード行番号

    @field_validator("attributes", mode="before")
    @classmethod
    def convert_attributes(cls, v: Any) -> NodeAttributes | None:
        """dictをNodeAttributesに変換"""
        if v is None:
            return None
        if isinstance(v, dict):
            return NodeAttributes(custom_data=v)
        return v

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if self.id is None:
            self.id = self.name  # デフォルトで name を id に

    def is_external(self) -> bool:
        """外部モジュールかどうかを判定"""
        if self.qualified_name:
            return not self.qualified_name.startswith("__main__")
        return False

    def get_display_name(self) -> str:
        """表示用の名前を取得"""
        return self.qualified_name if self.qualified_name else self.name


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

    source: NodeId
    target: NodeId
    relation_type: RelationType
    weight: Weight = Field(default=Weight(1.0))  # 0.0から1.0の範囲
    attributes: NodeAttributes | None = None
    metadata: GraphMetadata | None = None

    @field_validator("attributes", mode="before")
    @classmethod
    def convert_attributes(cls, v: Any) -> NodeAttributes | None:
        """dictをNodeAttributesに変換"""
        if v is None:
            return None
        if isinstance(v, dict):
            return NodeAttributes(custom_data=v)
        return v

    @field_validator("metadata", mode="before")
    @classmethod
    def convert_metadata(cls, v: Any) -> GraphMetadata | None:
        """dictをGraphMetadataに変換"""
        if v is None:
            return None
        if isinstance(v, dict):
            from src.core.schemas.types import GraphMetadata

            known_fields = {
                "version",
                "created_at",
                "cycles",
                "statistics",
                "custom_fields",
            }
            metadata_kwargs: dict[str, Any] = {}
            custom_fields: dict[str, Any] = {}
            for key, value in v.items():
                if key in known_fields:
                    metadata_kwargs[key] = value
                else:
                    custom_fields[key] = value
            if custom_fields:
                existing_custom = metadata_kwargs.get("custom_fields", {})
                if isinstance(existing_custom, dict):
                    existing_custom.update(custom_fields)
                    metadata_kwargs["custom_fields"] = existing_custom
                else:
                    metadata_kwargs["custom_fields"] = custom_fields
            return GraphMetadata(**metadata_kwargs)
        return v

    def is_strong_dependency(self) -> bool:
        """強い依存関係かどうかを判定（weight >= 0.8）"""
        return self.weight >= 0.8

    def get_dependency_strength(self) -> str:
        """依存関係の強さを文字列で取得"""
        if self.weight >= 0.8:
            return "強"
        elif self.weight >= 0.5:
            return "中"
        else:
            return "弱"


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
    metadata: GraphMetadata | None = None
    inferred_nodes: list[GraphNode] | None = None  # 推論されたノード

    @field_validator("metadata", mode="before")
    @classmethod
    def convert_metadata(cls, v: Any) -> GraphMetadata | None:
        """dictをGraphMetadataに変換"""
        if v is None:
            return None
        if isinstance(v, dict):
            # GraphMetadataの既知フィールドを抽出
            known_fields = {
                "version",
                "created_at",
                "cycles",
                "statistics",
                "custom_fields",
            }
            metadata_kwargs: dict[str, Any] = {}
            custom_fields: dict[str, Any] = {}

            for key, value in v.items():
                if key in known_fields:
                    metadata_kwargs[key] = value
                else:
                    custom_fields[key] = value

            # custom_fieldsがある場合は、既存のcustom_fieldsにマージ
            if custom_fields:
                existing_custom = metadata_kwargs.get("custom_fields", {})
                if isinstance(existing_custom, dict):
                    existing_custom.update(custom_fields)
                    metadata_kwargs["custom_fields"] = existing_custom
                else:
                    metadata_kwargs["custom_fields"] = custom_fields

            return GraphMetadata(**metadata_kwargs)
        return v

    def add_node(self, node: GraphNode) -> None:
        """ノードを追加"""
        if not any(n.id == node.id for n in self.nodes):
            self.nodes.append(node)

    def add_edge(self, edge: GraphEdge) -> None:
        """エッジを追加"""
        if not any(e.source == edge.source and e.target == edge.target for e in self.edges):
            self.edges.append(edge)

    def get_node(self, node_id: NodeId) -> GraphNode | None:
        """IDでノードを取得"""
        return next((n for n in self.nodes if n.id == node_id), None)

    def get_edges_from(self, node_id: NodeId) -> list[GraphEdge]:
        """ノードからのエッジを取得"""
        return [e for e in self.edges if e.source == node_id]

    def get_edges_to(self, node_id: NodeId) -> list[GraphEdge]:
        """ノードへのエッジを取得"""
        return [e for e in self.edges if e.target == node_id]

    def get_dependency_summary(self) -> dict[str, Any]:
        """依存関係の統計情報を取得"""
        from collections import Counter

        node_types = Counter(node.node_type for node in self.nodes)
        relations = Counter(edge.relation_type.value for edge in self.edges)
        strong_deps = sum(1 for edge in self.edges if edge.is_strong_dependency())

        return {
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "strong_dependencies": strong_deps,
            "node_types": dict(node_types),
            "relations": dict(relations),
        }

    def to_networkx(self) -> "nx.DiGraph":  # type: ignore  # noqa: F821
        """NetworkX DiGraph に変換

        TypeDependencyGraphをNetworkX DiGraph形式に変換します。
        """
        try:
            import networkx as nx
        except ImportError:
            raise ImportError("networkx is required for to_networkx()")

        graph = nx.DiGraph()
        for node in self.nodes:
            attrs = node.attributes.custom_data if node.attributes else {}
            # NetworkXはNone値を扱えないので、Noneを除外
            node_attrs = {
                "node_type": node.node_type,
                **attrs,
            }
            if node.qualified_name is not None:
                node_attrs["qualified_name"] = node.qualified_name
            if node.source_file is not None:
                node_attrs["pylay_source_file"] = node.source_file
            if node.line_number is not None:
                node_attrs["line_number"] = node.line_number
            graph.add_node(node.id, **node_attrs)
        for edge in self.edges:
            attrs = edge.attributes.custom_data if edge.attributes else {}
            edge_data: dict[str, Any] = {
                "relation_type": edge.relation_type.value,
                "weight": edge.weight,
                **attrs,
            }
            # metadataもNetworkXエッジデータに含める
            if edge.metadata is not None:
                edge_data["metadata"] = edge.metadata.model_dump()  # GraphMetadata を dict に変換
            graph.add_edge(
                edge.source,
                edge.target,
                **edge_data,
            )
        return graph

    @classmethod
    def from_networkx(
        cls,
        graph: "nx.DiGraph",  # type: ignore[name-defined]  # noqa: F821
    ) -> "TypeDependencyGraph":
        """NetworkX DiGraph から構築

        NetworkX DiGraphからTypeDependencyGraphを構築します。
        """
        import networkx as nx  # noqa: F401  # pyright: ignore[reportUnusedImport]

        nodes = []
        edges = []

        for node_id, node_attrs in graph.nodes(data=True):
            node_attrs = dict(node_attrs)
            node_type = node_attrs.pop("node_type", "unknown")
            qualified_name = node_attrs.pop("qualified_name", None)
            source_file = node_attrs.pop("pylay_source_file", None)
            line_number = node_attrs.pop("line_number", None)
            attributes = NodeAttributes(custom_data=node_attrs) if node_attrs else None
            nodes.append(
                GraphNode(
                    id=node_id,
                    name=node_id,
                    node_type=node_type,
                    qualified_name=qualified_name,
                    source_file=source_file,
                    line_number=line_number,
                    attributes=attributes,
                )
            )

        for source, target, edge_attrs in graph.edges(data=True):
            edge_attrs = dict(edge_attrs)
            relation_type_value = edge_attrs.pop("relation_type", "depends_on")
            weight_value = edge_attrs.pop("weight", 1.0)

            # 文字列をRelationTypeに変換
            if isinstance(relation_type_value, str):
                try:
                    relation_type = RelationType(relation_type_value)
                except ValueError:
                    # 無効な値の場合はdepends_onにフォールバック
                    relation_type = RelationType.DEPENDS_ON
            else:
                relation_type = relation_type_value

            attributes = NodeAttributes(custom_data=edge_attrs) if edge_attrs else None
            edges.append(
                GraphEdge(
                    source=source,
                    target=target,
                    relation_type=relation_type,
                    weight=weight_value,
                    attributes=attributes,
                )
            )

        return cls(nodes=nodes, edges=edges)
