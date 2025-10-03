"""
グラフ基本型定義

docs/typing-rule.md の原則に従い、型定義のみを定義します。
"""

from enum import Enum

from src.core.schemas.types import NodeId


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


__all__ = [
    "RelationType",
    "NodeId",
]
