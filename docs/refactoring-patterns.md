# type:ignore リファクタリングパターン集

このドキュメントでは、`type: ignore`を削除するための具体的なリファクタリングパターンを提供します。

## パターン1: Literal型のオーバーライド（Pyright reportIncompatibleVariableOverride）

### 問題のあるコード

```python
from typing import Literal
from pydantic import BaseModel, Field

class TypeSpec(BaseModel):
    type: str = Field(..., description="基本型")

class ListTypeSpec(TypeSpec):
    type: Literal["list"] = "list"  # type: ignore[assignment]  # ❌ LSP違反
```

### 問題点

- **リスコフの置換原則（LSP）違反**: サブクラスが基底クラスの契約を守っていない
- **型の不変性違反**: mutableなフィールドで共変なオーバーライドは不正
- **Pyright**: `reportIncompatibleVariableOverride` エラー

### 解決策A: 継承を使わない（推奨）

```python
from typing import Literal
from pydantic import BaseModel

class TypeSpecBase(BaseModel):
    """typeフィールドを持たない共通基底クラス"""
    name: str | None = None
    description: str | None = None
    required: bool = True

class ListTypeSpec(TypeSpecBase):
    """リスト型専用の仕様"""
    type: Literal["list"] = "list"  # ✅ オーバーライドではない
    items: str | None = None

class DictTypeSpec(TypeSpecBase):
    """辞書型専用の仕様"""
    type: Literal["dict"] = "dict"  # ✅ オーバーライドではない
    properties: dict[str, str] | None = None
```

**メリット**:
- ✅ 型理論的に正しい
- ✅ type:ignore不要
- ✅ LSP準拠

**デメリット**:
- 既存コードの書き換えが必要
- `TypeSpec`型で統一的に扱えない

### 解決策B: Tagged Union（判別共用体）

```python
from typing import Literal, Union
from pydantic import BaseModel

class ListSpec(BaseModel):
    kind: Literal["list"] = "list"
    items: str | None = None

class DictSpec(BaseModel):
    kind: Literal["dict"] = "dict"
    properties: dict[str, str] | None = None

# Union型で統一的に扱う
TypeSpec = Union[ListSpec, DictSpec]

def process_spec(spec: TypeSpec) -> str:
    match spec.kind:  # 型安全なパターンマッチング
        case "list":
            return f"リスト: {spec.items}"
        case "dict":
            return f"辞書: {spec.properties}"
```

**メリット**:
- ✅ 型安全なパターンマッチング
- ✅ type:ignore不要
- ✅ Rust/TypeScriptライクな設計

**デメリット**:
- 既存のコード構造を大きく変更する必要がある

### 解決策C: Immutable（frozen）フィールド

```python
from typing import Literal
from pydantic import BaseModel, Field

class TypeSpec(BaseModel):
    model_config = {'frozen': True}  # immutableにする
    type: str = Field(..., description="基本型")

class ListTypeSpec(TypeSpec):
    type: Literal["list"] = Field(default="list", frozen=True)  # ✅ immutableなのでOK
```

**メリット**:
- ✅ 最小限の変更
- ✅ immutableなら型の不変性違反ではない

**デメリット**:
- Pyrightは依然としてエラーを出す可能性がある
- 全体がimmutableになる

### 解決策D: Pyright設定の調整（非推奨）

```json
{
  "reportIncompatibleVariableOverride": "warning"  // または "none"
}
```

**メリット**:
- コード変更不要

**デメリット**:
- ❌ 他の正当なエラーも見逃す
- ❌ 型安全性の妥協

## パターン2: Pydantic Field制約とNewType

### 問題のあるコード

```python
from typing import NewType
from pydantic import BaseModel, Field

MaxDepth = NewType("MaxDepth", int)

class Config(BaseModel):
    max_depth: MaxDepth = Field(default=10)  # type: ignore[assignment]
```

### 解決策: NewTypeのキャスト

```python
from typing import NewType
from pydantic import BaseModel, Field

MaxDepth = NewType("MaxDepth", int)

class Config(BaseModel):
    max_depth: MaxDepth = Field(default=MaxDepth(10))  # ✅ 型キャスト
```

## パターン3: Pydantic動的属性（call-arg）

### 問題のあるコード

```python
class TypeSpec(BaseModel):
    type: str = Field(..., description="必須")

# サブクラスでデフォルト値を設定
class ListTypeSpec(TypeSpec):
    type: Literal["list"] = "list"

# 基底クラスを直接インスタンス化
TypeSpec(type="str")  # type: ignore[call-arg]  # ❌ typeが必須と認識される
```

### 解決策: パターン1の解決策を適用

継承を使わない、またはTagged Unionパターンを使用する。

## まとめ

| パターン | 推奨度 | 適用コスト | 型安全性 |
|---------|--------|-----------|---------|
| 継承を使わない | ⭐⭐⭐⭐⭐ | 中 | 高 |
| Tagged Union | ⭐⭐⭐⭐ | 高 | 最高 |
| Frozen | ⭐⭐⭐ | 低 | 中 |
| 設定変更 | ⭐ | 最低 | 低 |

### 一般原則

1. **設計変更を優先** - type:ignoreは最後の手段
2. **型理論に従う** - LSP、不変性を守る
3. **文書化** - やむを得ない場合は理由を明記
4. **定期的な見直し** - 型チェッカーのアップデートで削除可能になるか確認
