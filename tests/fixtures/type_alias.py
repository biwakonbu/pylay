"""type文（型エイリアス）のテストフィクスチャ"""

# 単純な型エイリアス
type UserId = str
type ProductId = int

# 複合型の型エイリアス
type Point = tuple[float, float]
type Coordinate3D = tuple[float, float, float]

# ジェネリック型の型エイリアス
type StringList = list[str]
type IntDict = dict[str, int]
