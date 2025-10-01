"""サンプルPythonモジュール"""

from pydantic import BaseModel


class User(BaseModel):
    """ユーザーモデル

    ユーザー情報を表すデータモデルです。
    """

    id: int
    name: str
    email: str | None = None
    age: int | None = None
    tags: list[str] = []


class Product(BaseModel):
    """商品モデル

    商品情報を表すデータモデルです。
    """

    id: int
    name: str
    price: float
    description: str | None = None
    category: str
