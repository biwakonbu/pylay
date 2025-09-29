"""
ForwardRefと循環参照のテスト用コード
"""

from __future__ import annotations


class Node:
    """循環参照を持つノードクラス"""

    def __init__(self, value: int, next_node: Node | None = None) -> None:
        self.value = value
        self.next = next_node

    def add_child(self, child: Node) -> None:
        """子ノードを追加"""
        self.child = child

    def get_parent(self) -> Node | None:
        """親ノードを取得"""
        return self.parent


# 循環参照の例
root = Node(0)
child = Node(1)
root.add_child(child)
child.parent = root  # 循環参照


class Tree:
    """木構造のクラス"""

    def __init__(self, root: Node) -> None:
        self.root = root


# ForwardRefの使用例
def create_node(value: int) -> Node:
    """ノードを作成"""
    return Node(value)
