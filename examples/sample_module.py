"""サンプルPythonモジュール"""

from typing import Optional
from pydantic import BaseModel


class User(BaseModel):
    """ユーザーモデル

    ユーザー情報を表すデータモデルです。
    """

    id: int
    name: str
    email: Optional[str] = None
    age: int | None = None
    tags: list[str] = []


class Product(BaseModel):
    """商品モデル

    商品情報を表すデータモデルです。
    """

    id: int
    name: str
    price: float
    description: Optional[str] = None
    category: str
