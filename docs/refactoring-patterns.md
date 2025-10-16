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
from typing import Literal
from pydantic import BaseModel

class ListSpec(BaseModel):
    kind: Literal["list"] = "list"
    items: str | None = None

class DictSpec(BaseModel):
    kind: Literal["dict"] = "dict"
    properties: dict[str, str] | None = None

# Union型で統一的に扱う
TypeSpec = ListSpec | DictSpec

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

## パターン3: Pydantic BaseModel動的属性（call-arg）

### 問題の概要

Pydantic BaseModelを継承したクラスで、デフォルト値を持つフィールドに対して値を明示的に渡す際、型チェッカー（特にPyright）が `reportCallIssue` エラーを発生させることがあります。

### 問題のあるコード例1: 継承による型変更

```python
from typing import Literal
from pydantic import BaseModel, Field

class TypeSpec(BaseModel):
    type: str = Field(..., description="基本型（必須）")
    required: bool = Field(True, description="必須かどうか（デフォルト: True）")

class ListTypeSpec(TypeSpec):
    type: Literal["list"] = "list"  # サブクラスでデフォルト値を設定

# 基底クラスを直接インスタンス化
spec = TypeSpec(name="test", type="str")  # type: ignore[call-arg]
# ❌ Pyright: 「requiredパラメータが必要」と誤認識
```

### 問題のあるコード例2: 動的生成

```python
from pydantic import BaseModel, Field

class TypeSpec(BaseModel):
    name: str | None = Field(None)
    type: str = Field(...)
    description: str | None = Field(None)
    required: bool = Field(True)  # デフォルト値あり

# 変数から動的に生成
type_name = "UserId"
type_str = "str"
description = "ユーザーID型"

result = TypeSpec(  # type: ignore[call-arg]
    name=type_name, type=type_str, description=description
)
# ❌ Pyright: 「requiredパラメータが必要」と誤認識
```

### 原因分析

1. **Pyrightの厳格なチェック**: `reportCallIssue: true` 設定により、Pydantic BaseModelの `__init__` シグネチャが厳密にチェックされる
2. **継承による型変更**: サブクラスでフィールドにデフォルト値を追加すると、基底クラスのインスタンス化時に型チェッカーが混乱する
3. **Pydantic内部実装**: BaseModelは実際にはすべてのフィールドを受け取れるが、型チェッカーはこれを認識できない

### 解決策A: 明示的にすべての引数を渡す（推奨度: ⭐⭐）

```python
result = TypeSpec(
    name=type_name,
    type=type_str,
    description=description,
    required=True,  # ✅ デフォルト値を持つフィールドも明示
)
```

**メリット**:
- ✅ type:ignore不要
- ✅ コードの意図が明確

**デメリット**:
- 冗長なコード（デフォルト値を毎回指定）
- デフォルト値変更時の修正漏れリスク

### 解決策B: model_construct()を使用（推奨度: ⭐⭐⭐）

```python
result = TypeSpec.model_construct(  # ✅ バリデーションスキップ
    name=type_name, type=type_str, description=description
)
```

**メリット**:
- ✅ type:ignore不要
- ✅ Pydantic v2公式のバリデーション回避方法
- ✅ パフォーマンス向上（バリデーションスキップ）

**デメリット**:
- ⚠️ バリデーションが実行されない（既に信頼できるデータの場合のみ使用）
- コードレビューアがバリデーションスキップの意図を理解する必要がある

### 解決策C: 継承を使わない（推奨度: ⭐⭐⭐⭐⭐）

```python
class TypeSpecBase(BaseModel):
    """typeフィールドを持たない共通基底クラス"""
    name: str | None = None
    description: str | None = None
    required: bool = True

class TypeSpec(TypeSpecBase):
    """汎用型仕様"""
    type: str  # ✅ デフォルト値なし

class ListTypeSpec(TypeSpecBase):
    """リスト型専用の仕様"""
    type: Literal["list"] = "list"  # ✅ オーバーライドではない

# インスタンス化
result = TypeSpec(name=type_name, type=type_str, description=description)  # ✅ エラーなし
```

**メリット**:
- ✅ 型理論的に正しい
- ✅ type:ignore不要
- ✅ LSP準拠

**デメリット**:
- 既存コードの大幅な書き換えが必要
- クラス階層が増える

### 解決策D: Tagged Union（推奨度: ⭐⭐⭐⭐）

パターン1の「Tagged Union」を参照してください。

### 解決策E: type:ignoreを維持し、理由を明記（推奨度: ⭐）

```python
result = TypeSpec(  # type: ignore[call-arg]  # Pyright reportCallIssue: 継承によるデフォルト値の型推論の限界
    name=type_name, type=type_str, description=description
)
```

**適用条件**:
- リファクタリングコストが高すぎる
- 一時的な回避策として
- 将来的な改善計画がある

**メリット**:
- コード変更最小

**デメリット**:
- ❌ 型安全性の妥協
- 他の正当なエラーを見逃すリスク

### 推奨アプローチ

1. **新規コード**: 解決策C（継承を使わない）または解決策D（Tagged Union）
2. **既存コード（リファクタリング可能）**: 解決策B（model_construct）
3. **既存コード（大規模変更困難）**: 解決策E（type:ignore維持）+ Issue登録

## パターン4: 型ナローイング（Union型からの型ガード）

### 問題の概要

Union型（複数の型の共用体）から特定の型にナローイングする際、assertによる型ガードでは型チェッカーが型の絞り込みを認識できません。

### 問題のあるコード

```python
from typing import TypedDict, Union, NotRequired

class TypeAliasEntry(TypedDict):
    kind: str  # "type_alias"
    target: str
    docstring: NotRequired[str | None]

class NewTypeEntry(TypedDict):
    kind: str  # "newtype"
    base_type: str
    docstring: NotRequired[str | None]

class DataclassEntry(TypedDict):
    kind: str  # "dataclass"
    frozen: bool
    fields: dict[str, dict]
    docstring: NotRequired[str | None]

ASTEntry = TypeAliasEntry | NewTypeEntry | DataclassEntry

def process_entry(typ: ASTEntry) -> None:
    kind = typ.get("kind")

    if kind == "type_alias":
        # 型ガード: TypeAliasEntry
        assert "target" in typ
        type_alias_entry: TypeAliasEntry = typ  # type: ignore[assignment]
        # ❌ mypyもPyrightもassertでは型を絞り込めない

        target = type_alias_entry["target"]  # 使用
```

### 原因分析

1. **assertの限界**: `assert "target" in typ` は実行時チェックであり、型チェッカーには型情報を提供しない
2. **Union型の複雑性**: 複数のTypedDictを持つUnion型は、型チェッカーが自動的に絞り込めない
3. **TypedDictの制約**: TypedDictは構造的部分型（structural subtyping）を使うため、kindフィールドだけでは判別できない

### 解決策A: TypeGuard を使った型ガード関数（推奨度: ⭐⭐⭐⭐⭐、Python 3.10+）

```python
from typing import TypedDict, Union, NotRequired, TypeGuard

class TypeAliasEntry(TypedDict):
    kind: str
    target: str
    docstring: NotRequired[str | None]

class NewTypeEntry(TypedDict):
    kind: str
    base_type: str
    docstring: NotRequired[str | None]

class DataclassEntry(TypedDict):
    kind: str
    frozen: bool
    fields: dict[str, dict]
    docstring: NotRequired[str | None]

ASTEntry = TypeAliasEntry | NewTypeEntry | DataclassEntry

# ✅ TypeGuard型ガード関数
def is_type_alias_entry(entry: ASTEntry) -> TypeGuard[TypeAliasEntry]:
    """型エイリアスエントリかどうかを判定"""
    return entry.get("kind") == "type_alias" and "target" in entry

def is_newtype_entry(entry: ASTEntry) -> TypeGuard[NewTypeEntry]:
    """NewTypeエントリかどうかを判定"""
    return entry.get("kind") == "newtype" and "base_type" in entry

def is_dataclass_entry(entry: ASTEntry) -> TypeGuard[DataclassEntry]:
    """dataclassエントリかどうかを判定"""
    return (
        entry.get("kind") == "dataclass"
        and "frozen" in entry
        and "fields" in entry
    )

def process_entry(typ: ASTEntry) -> None:
    if is_type_alias_entry(typ):
        # ✅ 型が TypeAliasEntry に絞り込まれている
        target = typ["target"]  # type:ignore不要
        print(f"Type alias: {target}")
    elif is_newtype_entry(typ):
        # ✅ 型が NewTypeEntry に絞り込まれている
        base_type = typ["base_type"]  # type:ignore不要
        print(f"NewType: {base_type}")
    elif is_dataclass_entry(typ):
        # ✅ 型が DataclassEntry に絞り込まれている
        frozen = typ["frozen"]  # type:ignore不要
        print(f"Dataclass (frozen={frozen})")
```

**メリット**:
- ✅ type:ignore不要
- ✅ 型安全性が高い
- ✅ 再利用可能な型ガード関数
- ✅ PEP 647準拠（Python 3.10+標準）

**デメリット**:
- Python 3.10以上が必要（本プロジェクトはPython 3.13なので問題なし）
- 型ガード関数の追加実装が必要

### 解決策B: TypeIs を使った型ガード関数（推奨度: ⭐⭐⭐⭐⭐、Python 3.13+）

```python
from typing import TypedDict, Union, NotRequired, TypeIs

# ... TypedDict定義は同じ ...

# ✅ TypeIs型ガード関数（Python 3.13+、より強力）
def is_type_alias_entry(entry: ASTEntry) -> TypeIs[TypeAliasEntry]:
    """型エイリアスエントリかどうかを判定（TypeIs版）"""
    return entry.get("kind") == "type_alias" and "target" in entry

# TypeIsの利点: else節でも型が絞り込まれる
def process_entry(typ: ASTEntry) -> None:
    if is_type_alias_entry(typ):
        # ✅ 型が TypeAliasEntry に絞り込まれている
        target = typ["target"]
    else:
        # ✅ 型が NewTypeEntry | DataclassEntry に絞り込まれている（TypeGuardではできない）
        pass
```

**メリット**:
- ✅ TypeGuardのすべてのメリット
- ✅ else節でも型が絞り込まれる（より強力）
- ✅ PEP 742準拠（Python 3.13+標準）

**デメリット**:
- Python 3.13以上が必要（本プロジェクトは対応済み）

### 解決策C: Literal型のkindフィールド（推奨度: ⭐⭐⭐⭐）

```python
from typing import TypedDict, Union, NotRequired, Literal

class TypeAliasEntry(TypedDict):
    kind: Literal["type_alias"]  # ✅ Literal型で判別
    target: str
    docstring: NotRequired[str | None]

class NewTypeEntry(TypedDict):
    kind: Literal["newtype"]  # ✅ Literal型で判別
    base_type: str
    docstring: NotRequired[str | None]

class DataclassEntry(TypedDict):
    kind: Literal["dataclass"]  # ✅ Literal型で判別
    frozen: bool
    fields: dict[str, dict]
    docstring: NotRequired[str | None]

ASTEntry = TypeAliasEntry | NewTypeEntry | DataclassEntry

def process_entry(typ: ASTEntry) -> None:
    if typ["kind"] == "type_alias":
        # ✅ 型が TypeAliasEntry に自動的に絞り込まれる
        target = typ["target"]  # type:ignore不要
    elif typ["kind"] == "newtype":
        # ✅ 型が NewTypeEntry に自動的に絞り込まれる
        base_type = typ["base_type"]  # type:ignore不要
    elif typ["kind"] == "dataclass":
        # ✅ 型が DataclassEntry に自動的に絞り込まれる
        frozen = typ["frozen"]  # type:ignore不要
```

**メリット**:
- ✅ type:ignore不要
- ✅ 型ガード関数不要（型チェッカーが自動判別）
- ✅ Tagged Unionパターン（Rust/TypeScript風）

**デメリット**:
- 既存のTypeDict定義の修正が必要
- kindフィールドの値が固定される

### 推奨アプローチ

1. **新規コード**: 解決策C（Literal型のkindフィールド）
2. **既存コード（小規模修正）**: 解決策B（TypeIs、Python 3.13+）
3. **既存コード（Python 3.10-3.12）**: 解決策A（TypeGuard）

## まとめ

### パターン別推奨度一覧

| パターン | 問題種別 | 推奨度 | 適用コスト | 型安全性 | Python要件 |
|---------|---------|--------|-----------|---------|-----------|
| **パターン1: Literal型オーバーライド** | | | | | |
| 継承を使わない | LSP違反 | ⭐⭐⭐⭐⭐ | 中 | 高 | 3.10+ |
| Tagged Union | LSP違反 | ⭐⭐⭐⭐ | 高 | 最高 | 3.10+ |
| Frozen | LSP違反 | ⭐⭐⭐ | 低 | 中 | 3.10+ |
| 設定変更 | LSP違反 | ⭐ | 最低 | 低 | - |
| **パターン3: Pydantic動的属性** | | | | | |
| 明示的引数 | call-arg | ⭐⭐ | 低 | 高 | 3.10+ |
| model_construct | call-arg | ⭐⭐⭐ | 低 | 中 | 3.10+ |
| 継承を使わない | call-arg | ⭐⭐⭐⭐⭐ | 高 | 高 | 3.10+ |
| Tagged Union | call-arg | ⭐⭐⭐⭐ | 高 | 最高 | 3.10+ |
| type:ignore維持 | call-arg | ⭐ | 最低 | 低 | - |
| **パターン4: 型ナローイング** | | | | | |
| TypeGuard | assignment | ⭐⭐⭐⭐⭐ | 低 | 高 | 3.10+ |
| TypeIs | assignment | ⭐⭐⭐⭐⭐ | 低 | 最高 | 3.13+ |
| Literal kind | assignment | ⭐⭐⭐⭐ | 中 | 最高 | 3.10+ |

### 一般原則

1. **設計変更を優先** - type:ignoreは最後の手段
2. **型理論に従う** - LSP、不変性を守る
3. **Python 3.13の機能を活用** - TypeIs、Literal型など最新機能を使用
4. **文書化** - やむを得ない場合は理由を明記（Issue登録推奨）
5. **定期的な見直し** - 型チェッカーのアップデートで削除可能になるか確認

### 実装優先順位の判断基準

1. **新規コード**: 型理論的に正しい設計を最初から適用（継承を使わない、Tagged Union、TypeIs）
2. **既存コード（リファクタリング可能）**: 低コストで高効果な解決策（TypeIs、model_construct）
3. **既存コード（大規模変更困難）**: type:ignore維持 + Issue登録 + 将来的な改善計画

### pylayツールへの組み込み計画

これらのパターンは、Issue #88で計画されている「type:ignore診断機能の拡張」において、以下のように活用されます：

1. **パターン検出**: コード内のtype:ignoreを自動分類
2. **リファクタリング提案**: 各パターンに応じた具体的な解決策を提示
3. **優先度判定**: 適用コストと型安全性から自動的に優先度を算出
4. **Auto-fix**: 機械的に修正可能なパターン（TypeGuard追加など）の自動修正

詳細は [docs/features/type-ignore-enhancements.md](features/type-ignore-enhancements.md) を参照してください。
