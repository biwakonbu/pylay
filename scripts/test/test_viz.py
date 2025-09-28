"""
Graphviz視覚化のテスト用コード
"""

# from typing import List, Dict  # Not needed with built-in types


class Sample:
    """サンプルクラス"""

    def __init__(self, items: list[str]) -> None:
        self.items = items

    def process(self, data: dict[str, int]) -> list[str]:
        """データを処理"""
        return self.items


# 使用例
sample = Sample(["a", "b", "c"])
result = sample.process({"key": 42})
