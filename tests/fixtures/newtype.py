"""NewTypeのテストフィクスチャ"""

from typing import NewType

# 基本的なNewType
UserId = NewType("UserId", str)
Email = NewType("Email", str)

# 数値型のNewType
Count = NewType("Count", int)
Score = NewType("Score", float)
