# pylay - グラフ理論と型依存抽出 (Core Documentation)

## 1. 概要

### 1.1 目的
pylayプロジェクトのPhase 4（型推論/依存抽出実装）で、グラフ理論を活用した型依存関係の抽出・分析機能を実装します。この機能は、PythonコードのAST（抽象構文木）とmypyの型推論を組み合わせ、型間の依存関係をグラフとしてモデル化します。主に、NetworkXライブラリを使用し、型参照の循環検知や視覚化を可能にします。

### 1.2 対象範囲
- **実装済み**: 最適化されたグラフ構造の型定義（`src/schemas/graph_types.py`）、AST依存抽出（`converters/ast_dependency_extractor.py`）、ドキュメント生成（`doc_generators/graph_doc_generator.py`）、YAML統合。
- **開発中**: NetworkX統合と高度な視覚化。
- **範囲外**: 高度なグラフアルゴリズム（最短経路など）の実装（本フェーズでは依存関係の基本抽出に限定）。

### 1.3 グラフの役割
- 型依存の視覚化: クラス間の継承、関数呼び出し、変数参照をエッジとして表現。
- 循環参照検知: 型定義の無限ループを防ぐ。
- ドキュメント生成: 依存グラフをMarkdownやGraphvizで出力。
- 拡張性: 将来的に型推論結果の統合やYAML型仕様の依存記述へ発展。

## 2. 型定義

### 2.1 最適化された構造
グラフはノード（型要素）とエッジ（依存関係）で構成されます。Pydantic BaseModelで定義し、YAMLシリアライズをサポートします。最適化版では、Literal型と厳密な型定義を使用しています。

#### 2.1.1 GraphNode
Python型要素（クラス、関数、変数）を表すノード。

- **name**: ノードの識別子（例: 'MyClass'）。
- **node_type**: ノードの種類（Literal型: 'class', 'function', 'variable', 'module', 'type_alias', 'method'）。
- **attributes**: メタデータ（型安全な辞書: `Dict[str, Union[str, int, bool, List[str], Dict[str, str]]]`）。
- **qualified_name**: 完全修飾名（オプション）。

```python
class GraphNode(BaseModel):
    name: str
    node_type: NodeType  # Literal['class', 'function', 'variable', 'module', 'type_alias', 'method']
    attributes: Optional[NodeAttributes] = None
    qualified_name: Optional[str] = None
```

**ユーティリティメソッド**:
- `get_display_name()`: 表示用の名前を取得
- `is_external()`: 外部（ビルトイン）型かどうかを判定
- `source_file`: ソースファイルパス（プロパティ）
- `line_number`: 行番号（プロパティ）
```

#### 2.1.2 GraphEdge
ノード間の依存関係を表すエッジ。

- **source**: 起点ノードの名前。
- **target**: 終点ノードの名前。
- **relation_type**: 関係の種類（Literal型: 'inherits', 'calls', 'references', 'imports', 'depends_on', 'returns', 'implements'）。
- **weight**: 関係の強さ（0.0-1.0の範囲）。
- **metadata**: エッジの追加情報。

```python
class GraphEdge(BaseModel):
    source: str
    target: str
    relation_type: RelationType
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = None
```

**ユーティリティメソッド**:
- `is_strong_dependency()`: 強い依存関係（重み0.7以上）かどうかを判定
- `get_dependency_strength()`: 依存の強さを文字列で取得
```

#### 2.1.3 TypeDependencyGraph
グラフ全体を表すモデル。

- **nodes**: ノードのリスト。
- **edges**: エッジのリスト。
- **metadata**: グラフの追加情報（型安全）。

```python
class TypeDependencyGraph(BaseModel):
    nodes: Sequence[GraphNode]
    edges: Sequence[GraphEdge]
    metadata: Optional[GraphMetadata] = {}
```

**ユーティリティメソッド**:
- `get_node_count()`: ノード数を取得
- `get_edge_count()`: エッジ数を取得
- `get_strong_dependencies()`: 強い依存関係のエッジを取得
- `get_node_by_name(name)`: 名前でノードを取得
- `get_edges_by_source(source_name)`: 起点ノードのエッジを取得
- `get_edges_by_target(target_name)`: 終点ノードのエッジを取得
- `get_dependency_summary()`: 依存関係の統計を取得
```

### 2.2 関係種別の定義
- **inherits**: クラス継承（例: `class A(B):` → AからBへのエッジ）。
- **calls**: 関数/メソッド呼び出し（例: `obj.method()` → 呼び出し元から呼び出し先へのエッジ）。
- **references**: 型参照（例: `List[User]` → ListからUserへのエッジ）。
- **imports**: モジュールインポート（例: `from module import X` → インポート元からXへのエッジ）。

## 3. 使用例

### 3.1 基本的なグラフ構築
```python
from src.schemas.graph_types import GraphNode, GraphEdge, TypeDependencyGraph

# ノード定義
node_a = GraphNode(name='User', node_type='class', attributes={'source_file': 'models.py'})
node_b = GraphNode(name='Address', node_type='class')
node_c = GraphNode(name='get_user', node_type='function')

# エッジ定義
edge1 = GraphEdge(source='User', target='Address', relation_type='references')
edge2 = GraphEdge(source='get_user', target='User', relation_type='references')

# グラフ作成
graph = TypeDependencyGraph(
    nodes=[node_a, node_b, node_c],
    edges=[edge1, edge2],
    metadata={'generated_by': 'AST_parser', 'timestamp': '2025-09-27'}
)

# YAML出力例（converters/type_to_yaml.pyで実装）
yaml_output = graph.model_dump()  # Pydanticでシリアライズ
```

### 3.2 NetworkX統合（拡張例）
```python
import networkx as nx

# PydanticグラフからNetworkXへ変換
nx_graph = nx.DiGraph()
for node in graph.nodes:
    nx_graph.add_node(node.name, **node.attributes or {})
for edge in graph.edges:
    nx_graph.add_edge(edge.source, edge.target, relation=edge.relation_type, weight=edge.weight)

# 循環検知
cycles = list(nx.simple_cycles(nx_graph))
# 視覚化（Graphviz）
nx.write_graphml(nx_graph, 'dependency_graph.graphml')
```

## 3. 実装の最適化

### 3.1 型定義の最適化
- **Literal型**: `node_type`と`relation_type`をLiteral型で厳密定義し、型安全性を向上
- **属性の型安全化**: `NodeAttributes`を`Dict[str, Union[str, int, bool, List[str], Dict[str, str]]]`で定義
- **ユーティリティメソッド**: 各クラスに便利なメソッドを追加（例: `is_external()`, `get_dependency_strength()`）
- **メタデータの型安全化**: `GraphMetadata`を`Dict[str, Union[str, int, float, bool, datetime]]`で定義

### 3.2 AST抽出の最適化
- **循環参照防止**: 処理スタックを使用して無限ループを防ぐ
- **キャッシュ機構**: ノードの重複作成を避ける
- **エラーハンドリング**: 構文エラーやエンコーディングエラーを適切に処理
- **依存の重み付け**: 継承（0.9）、戻り値（0.8）、引数（0.6）などの重みを設定

### 3.3 ドキュメント生成の最適化
- **統計情報の強化**: 強い依存関係数、外部依存の検出
- **テーブルの改善**: 位置情報と外部フラグの追加
- **フォーマットの向上**: より読みやすいMarkdown出力

## 4. 実装計画と拡張

### 4.1 フェーズ4の実装ステップ（最適化版）
1. **型定義の統合**: `src/schemas/graph_types.py`を実装・テスト（Literal型とユーティリティメソッド）。
2. **ASTパーサ開発**: `converters/ast_dependency_extractor.py`でASTからノード/エッジ抽出（循環参照防止、キャッシュ、重み付け）。
3. **mypy統合**: `mypy --infer`で型推論結果をグラフにマージ。
4. **ドキュメント生成**: `doc_generators/graph_doc_generator.py`でMarkdown/Graphviz出力（統計情報強化）。
5. **CLIコマンド**: `generate_dependency_graph.py`としてエントリーポイント追加。
6. **YAML統合**: `converters/type_to_yaml.py`に依存情報出力機能を追加。
7. **テスト**: ラウンドトリップテスト（AST -> グラフ -> YAML -> グラフ）。
8. **静的解析**: mypy/Ruffで型安全・コード品質確保。

### 4.2 リスクと対策
- **リスク**: 複雑なジェネリック型（Generic[T]）の依存抽出が難しい → ASTの`ast.Subscript`で段階的に対応。
- **対策**: ミニマム版で基本型（str, int, List[T]）から開始。拡張時はmypyの型分解機能（get_origin/get_args）活用。
- **依存**: NetworkXのGraphアルゴリズム。Python 3.13+のtypingモジュール。

### 4.3 拡張アイデア
- **視覚化**: Graphvizで.dotファイル生成（`nx.drawing.nx_pydot`）。
- **YAML統合**: 依存をTypeSpecの`dependencies`フィールドに追加。
- **性能最適化**: 大規模コードベースでの遅延ローディング。
- **高度アルゴリズム**: 依存のトポロジカルソートでインポート順序提案。

## 5. 参考資料
- [NetworkX Documentation](https://networkx.org/)
- [Python AST](https://docs.python.org/3/library/ast.html)
- [mypy Infer](https://mypy.readthedocs.io/en/stable/command_line.html#cmdoption-mypy-infer)
- [Pydantic BaseModel](https://docs.pydantic.dev/)
- プロジェクトPRD.md（Phase 4詳細）
- プロジェクトAGENTS.md（開発ガイドライン）

このドキュメントは実装進捗に応じて更新されます。グラフ構造の変更時は型定義と併せて修正してください。
