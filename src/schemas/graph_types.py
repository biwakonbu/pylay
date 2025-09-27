"""
グラフ理論関連の型定義モジュール。
pylayの依存関係抽出機能で使用。NetworkXのDiGraphを基盤とし、型依存を表現。
最適化版：Literal型と厳密な型定義を使用。
"""

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator
from collections.abc import Mapping, Sequence
from datetime import datetime


# ノードタイプの定義
NodeType = Literal['class', 'function', 'variable', 'module', 'type_alias', 'method', 'function_call', 'method_call', 'attribute_access', 'imported_symbol']

# 関係タイプの定義
RelationType = Literal['inherits', 'calls', 'references', 'imports', 'depends_on', 'returns', 'implements']

# 属性の定義（より具体的に）
NodeAttributes = Dict[str, Union[str, int, bool, List[str], Dict[str, str]]]


class GraphNode(BaseModel):
    """
    グラフのノードを表すモデル。Python型（クラス、関数など）の基本情報を保持。

    Attributes:
        name: ノードの識別子（例: 'MyClass'）。
        node_type: ノードの種類（厳密なLiteral型）。
        attributes: 追加属性（型安全な辞書）。
        qualified_name: 完全修飾名（オプション）。
    """
    name: str = Field(..., description="ノードの識別子（例: 'MyClass'）")
    node_type: NodeType = Field(..., description="ノードの種類")
    attributes: Optional[NodeAttributes] = Field(
        default=None,
        description="ノードのメタデータ（型安全）"
    )
    qualified_name: Optional[str] = Field(
        default=None,
        description="完全修飾名（例: 'module.submodule.Class'）"
    )

    def get_display_name(self) -> str:
        """表示用の名前を取得"""
        return self.qualified_name or self.name

    def is_external(self) -> bool:
        """外部（ビルトイン）型かどうかを判定"""
        return self.node_type in ('type_alias',) and self.name in ('str', 'int', 'float', 'bool', 'Any', 'None')

    @property
    def source_file(self) -> Optional[str]:
        """ソースファイルパスを取得"""
        if self.attributes and isinstance(self.attributes, dict):
            file_path = self.attributes.get('source_file')
            return str(file_path) if file_path is not None else None
        return None

    @property
    def line_number(self) -> Optional[int]:
        """行番号を取得"""
        if self.attributes and isinstance(self.attributes, dict):
            line = self.attributes.get('line')
            if line is not None and isinstance(line, (int, str)):
                try:
                    return int(line)
                except (ValueError, TypeError):
                    return None
        return None


class GraphEdge(BaseModel):
    """
    グラフのエッジを表すモデル。ノード間の依存関係を表現。

    Attributes:
        source: 起点ノードの名前。
        target: 終点ノードの名前。
        relation_type: 関係の種類（厳密なLiteral型）。
        weight: 関係の強さ（0.0-1.0の範囲）。
        metadata: エッジの追加情報。
    """
    source: str = Field(..., description="起点ノードの名前")
    target: str = Field(..., description="終点ノードの名前")
    relation_type: RelationType = Field(..., description="関係の種類")
    weight: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="エッジの重み（0.0-1.0、依存の強さを示す）"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="エッジの追加メタデータ"
    )

    def is_strong_dependency(self) -> bool:
        """強い依存関係かどうかを判定（重み0.7以上）"""
        return self.weight >= 0.7

    def get_dependency_strength(self) -> str:
        """依存の強さを文字列で取得"""
        if self.weight >= 0.8:
            return "強い"
        elif self.weight >= 0.5:
            return "中程度"
        else:
            return "弱い"


# メタデータの定義
GraphMetadata = Dict[str, Union[str, int, float, bool, datetime]]


class TypeDependencyGraph(BaseModel):
    """
    型依存グラフ全体を表すモデル。ノードとエッジの集合。

    Attributes:
        nodes: ノードのリスト。
        edges: エッジのリスト。
        metadata: グラフ全体のメタデータ（型安全）。
    """
    nodes: Sequence[GraphNode] = Field(..., description="グラフのノード集合")
    edges: Sequence[GraphEdge] = Field(..., description="グラフのエッジ集合")
    metadata: Optional[GraphMetadata] = Field(
        default_factory=dict,
        description="グラフの追加情報"
    )

    def model_post_init(self, __context: Any) -> None:
        """
        ポストイニットフック。将来的にNetworkXグラフの構築をここで初期化可能。
        """
        # ミニマム版では空実装。拡張時に import networkx as nx; self.nx_graph = nx.DiGraph() を追加
        pass

    def get_node_count(self) -> int:
        """ノード数を取得"""
        return len(self.nodes)

    def get_edge_count(self) -> int:
        """エッジ数を取得"""
        return len(self.edges)

    def get_strong_dependencies(self) -> List[GraphEdge]:
        """強い依存関係のエッジを取得"""
        return [edge for edge in self.edges if edge.is_strong_dependency()]

    def get_node_by_name(self, name: str) -> Optional[GraphNode]:
        """名前でノードを取得"""
        for node in self.nodes:
            if node.name == name:
                return node
        return None

    def get_edges_by_source(self, source_name: str) -> List[GraphEdge]:
        """起点ノードのエッジを取得"""
        return [edge for edge in self.edges if edge.source == source_name]

    def get_edges_by_target(self, target_name: str) -> List[GraphEdge]:
        """終点ノードのエッジを取得"""
        return [edge for edge in self.edges if edge.target == target_name]

    def get_dependency_summary(self) -> Dict[str, Any]:
        """依存関係の統計を取得"""
        node_types: Dict[str, int] = {}
        relations: Dict[str, int] = {}

        for node in self.nodes:
            node_types[node.node_type] = node_types.get(node.node_type, 0) + 1

        for edge in self.edges:
            relations[edge.relation_type] = relations.get(edge.relation_type, 0) + 1

        return {
            'node_count': self.get_node_count(),
            'edge_count': self.get_edge_count(),
            'node_types': node_types,
            'relations': relations,
            'strong_dependencies': len(self.get_strong_dependencies())
        }
