"""
複雑なジェネリック型のテスト用コード
"""

from typing import Union, Optional
from collections.abc import Mapping


class GenericClass:
    """ジェネリッククラス"""

    def __init__(self, data: dict[str, list[int]]) -> None:
        self.data = data

    def process(self, items: list[str | int]) -> Optional[dict[str, str]]:
        """複雑な型を処理"""
        return None


# ネストされたジェネリック型
nested_dict: dict[str, list[dict[str, int | str]]] = {}


def complex_function(
    arg1: dict[str, list[int]], arg2: list[Optional[str]]
) -> list[str] | dict[str, int]:
    """複雑な関数"""
    return []
