# 型インデックス（完全自動成長対応）

## 🚀 統一的な型取得方法

すべての型に対して統一的な方法で取得可能です。型を追加するだけで自動的に利用可能になります。

```python
from schemas.core_types import TypeFactory

# 完全自動成長（レイヤー自動検知）
UserIdType = TypeFactory.get_auto('UserId')
HeroContentType = TypeFactory.get_auto('HeroContent')
APIRequestType = TypeFactory.get_auto('LPGenerationRequest')

# インスタンス化
user_id = UserIdType("user123")
hero_data = HeroContentType(headline="Hello", subheadline="World")
request = APIRequestType(service_name="MyService")
```

## 📁 レイヤー別詳細

### PRIMITIVES レイヤー
- **型数**: 6
- [詳細を見る](types/primitives.md)

- **主な型**: str, int, float, bool, bytes
- **他**: +1 型

### CONTAINERS レイヤー
- **型数**: 5
- [詳細を見る](types/containers.md)

- **主な型**: list, tuple, set, dict, frozenset

## 📊 統計情報

- **総型数**: 11
- **全レイヤー型一覧**: NoneType, bool, bytes, dict, float, frozenset, int, list, set, str, tuple
**生成日**: 2025-09-27T17:16:10.290952
