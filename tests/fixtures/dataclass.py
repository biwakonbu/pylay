"""dataclassのテストフィクスチャ"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Point:
    """2D座標点"""

    x: float
    y: float


@dataclass
class User:
    """ユーザー情報"""

    name: str
    age: int
    email: str


@dataclass
class Product:
    """商品情報"""

    name: str
    price: float
    stock: int = 0
