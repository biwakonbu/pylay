"""複数種類の型定義が混在するテストフィクスチャ"""

from dataclasses import dataclass
from typing import NewType

# type文
type UserId = str
type Point = tuple[float, float]

# NewType
Email = NewType("Email", str)
Count = NewType("Count", int)


# dataclass
@dataclass(frozen=True)
class User:
    """ユーザー情報"""

    id: str
    name: str
    email: str


@dataclass
class Product:
    """商品情報"""

    name: str
    price: float
    stock: int = 0
