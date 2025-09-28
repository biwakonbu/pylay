"""
サンプルPythonコード for 型推論と依存関係抽出テスト
"""

# from typing import List  # Not needed with built-in list


def process_data(items: list[str]) -> int:
    """文字列リストの長さを返します。"""
    return len(items)


x: int = 42
y = "hello"  # 未アノテーション
z = True  # 未アノテーション


class SampleClass:
    """サンプルクラス"""

    def __init__(self, name: str) -> None:
        self.name = name

    def get_name(self) -> str:
        return self.name
