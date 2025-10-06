# pylay プロジェクト型定義ルール

本ドキュメントは、pylayプロジェクトにおける型定義の統一ルールを定めます。Pydanticを活用した厳密な型安全性と、型レベルでの値保証を実現することで、バグの早期発見とドキュメント自動生成の精度向上を目指します。

## 目次

1. [基本理念](#基本理念)
2. [型定義レベルの基本構造と理念](#型定義レベルの基本構造と理念)
3. [核心原則](#核心原則)
4. [ディレクトリ構造規約](#ディレクトリ構造規約)
5. [型定義パターン集](#型定義パターン集)
6. [バリデーション戦略](#バリデーション戦略)
7. [型参照ルール](#型参照ルール)
8. [既存コード移行ガイド](#既存コード移行ガイド)
9. [チェックリスト](#チェックリスト)

## 基本理念

### 型駆動開発（Type-Driven Development）
- **型は仕様である**: 型定義自体がドキュメントとして機能し、実装の制約となる
- **Pydantic First**: Pydantic BaseModelを基盤とした型安全なドメイン型を構築する
- **値の保証**: 型レベルでのバリデーションにより、不正な値の流入を防ぐ
- **自己文書化**: 型定義により、コードが自身を説明する

### pylayプロジェクトにおける型の役割
本プロジェクトは「Pythonの型情報を活用したドキュメント自動生成ツール」であるため、型定義の品質が直接的にプロダクトの品質に影響します。

**重要**: 型定義の厳密性 = ドキュメント生成の精度

### Python 3.13基準での型定義
本プロジェクトはPython 3.13を開発基準としています（pyproject.tomlでは互換性のため `>=3.12` を指定）。そのため、以下の新機能を積極的に活用します：

**注**: Python 3.12でも動作しますが、型定義はPython 3.13の機能を前提とします。3.12環境では一部の型構文（PEP 695の完全なサポートなど）が制限される場合があります。

#### Python 3.13の型システム新機能

1. **型パラメータ構文（PEP 695）**: `class Container[T]` でジェネリック型を簡潔に定義（Python 3.12+）
   ```python
   # ✅ Python 3.12+ / 3.13推奨
   class Stack[T]:
       def __init__(self) -> None:
           self._items: list[T] = []

   # ❌ 古い書き方（Python 3.11以前）
   from typing import TypeVar, Generic
   T = TypeVar('T')
   class Stack(Generic[T]):
       def __init__(self) -> None:
           self._items: list[T] = []
   ```

   **注**: Python 3.12でもPEP 695は利用可能ですが、3.13でより安定しています。

2. **type 文（PEP 695）**: 型エイリアスを明示的に定義
   ```python
   # ✅ Python 3.12+（3.13でも推奨）
   type Point = tuple[float, float]
   type Matrix = list[list[float]]
   type JSONValue = str | int | float | bool | None | dict[str, "JSONValue"] | list["JSONValue"]

   # ❌ 古い書き方
   from typing import TypeAlias
   Point: TypeAlias = tuple[float, float]
   ```

3. **組み込み型のジェネリクス（PEP 585）**: `list[str]`, `dict[str, int]` が標準（Python 3.9+、3.13では当然）
   ```python
   # ✅ Python 3.9+
   def process(items: list[str]) -> dict[str, int]:
       pass

   # ❌ 古い書き方（Python 3.8以前）
   from typing import List, Dict
   def process(items: List[str]) -> Dict[str, int]:
       pass
   ```

4. **Union型の簡潔表記（PEP 604）**: `X | Y` 形式（Python 3.10+、3.13では標準）
   ```python
   # ✅ Python 3.10+
   def func(x: str | int | None) -> bool:
       pass

   # ❌ 古い書き方
   from typing import Union, Optional
   def func(x: Optional[Union[str, int]]) -> bool:
       pass
   ```

5. **improved error messages**: 型エラーメッセージがより詳細で理解しやすく改善

#### typing モジュールからの脱却

Python 3.13では、以下のtypingモジュールの型は**使用禁止**とします：

| 禁止 | 代替（Python 3.13標準） | 備考 |
|------|------------------------|------|
| `Union[X, Y]` | `X \| Y` | Python 3.10+ |
| `Optional[X]` | `X \| None` | Python 3.10+ |
| `List[X]` | `list[X]` | Python 3.9+ |
| `Dict[K, V]` | `dict[K, V]` | Python 3.9+ |
| `Tuple[X, Y]` | `tuple[X, Y]` | Python 3.9+ |
| `Set[X]` | `set[X]` | Python 3.9+ |
| `TypeAlias` | `type` 文 | Python 3.12+ |
| `Generic[T]` | `class C[T]` | Python 3.12+ |
| `TypeVar('T')` | `class C[T]` | Python 3.12+ |

**例外**: `NewType`, `Protocol`, `TypedDict`, `TypeGuard`, `Callable`, `override` は引き続き使用可

## 型定義レベルの基本構造と理念

### なぜ3つのレベルに分けるのか

このプロジェクトでは、型定義を**責務と複雑度に応じて3つのレベル**に分類します。この分類により、以下のメリットが得られます：

1. **型の責務を明確化**: 単純な別名なのか、制約を持つのか、ビジネスロジックを持つのかが一目瞭然
2. **適切な抽象度の選択**: 過剰な実装を避け、必要十分な型定義を実現
3. **保守性の向上**: 型の複雑度が可視化され、リファクタリングの判断材料となる
4. **ドキュメント生成の精度向上**: 型のレベルに応じた適切なドキュメントが自動生成される
5. **段階的な型の成長**: Level 1から始めて、必要に応じてLevel 2/3へ昇格させる開発フローが可能

### 3つのレベルの定義と構造的違い

| レベル | 定義 | 構造 | 用途 | 実装方法 | 例 |
|--------|------|------|------|----------|-----|
| **Level 1** | 型エイリアス<br/>（制約なし） | 単純な別名定義 | - 意味的な型名を与える<br/>- 可読性向上<br/>- 一時的な型定義 | `type` 文 | `type UserId = str`<br/>`type Timestamp = float` |
| **Level 2** | 制約付き型<br/>（型レベル区別 + バリデーション） | NewType + Annotated + バリデータ | - プリミティブ型の代替（最頻出パターン）<br/>- 型レベルでの区別（mypy/pyright）<br/>- ランタイムバリデーション | `NewType` + `Annotated` + `Field` | `UserId = NewType('UserId', Annotated[str, Field(min_length=8)])`<br/>`Count = NewType('Count', Annotated[int, Field(ge=0)])` |
| **Level 3** | ドメインモデル<br/>（値オブジェクト・エンティティ） | dataclass + Pydantic | - 複雑なドメイン型<br/>- 値オブジェクト（不変）<br/>- エンティティ（状態 + ロジック） | `dataclass` + Pydantic | `@dataclass(frozen=True)`<br/>`class CodeLocation:`<br/>&nbsp;&nbsp;&nbsp;&nbsp;`file: str`<br/>&nbsp;&nbsp;&nbsp;&nbsp;`line: int = Field(ge=1)` |

### レベル間の関係性とライフサイクル

型定義は、以下のようなライフサイクルを持ちます：

```
[設計初期]
   ↓
Level 1: type UserId = str
   ↓ (型レベル区別 + バリデーションが必要になる)
Level 2: UserId = NewType('UserId', Annotated[str, Field(min_length=8)])
   ↓ (複数フィールド・ビジネスロジックが増える)
Level 3: @dataclass(frozen=True)
         class User:
             user_id: UserId
             name: str
             def is_admin(self) -> bool: ...
```

**重要**: このプロジェクトの設計思想として、**低レベル（Level 1）での長期放置は推奨されません**。Level 1は一時的な状態として許容されますが、以下を検討すべきです：

- 制約が必要なら → Level 2へ昇格
- ビジネスロジックが必要なら → Level 3へ昇格
- 本当に単純な別名だけでよいなら → docstringで `@keep-as-is: true` を明示

### レベル選択のフローチャート

型を定義する際は、以下のフローで適切なレベルを選択します：

```
┌─────────────────────────────────┐
│ 型を定義する必要がある          │
└─────────────┬───────────────────┘
              ↓
      ┌───────────────┐
      │ 制約・バリデーション│ NO → Level 1 (type文)
      │ が必要か？       │      ※一時的な状態として許容
      └───────┬───────┘      ※将来的にLevel 2/3への昇格を検討
              ↓ YES
      ┌───────────────┐
      │ 複数フィールドまたは │ NO → Level 2 (NewType + Annotated)
      │ ビジネスロジックが   │      ★プリミティブ型代替の最頻出パターン
      │ 必要か？           │      ※型レベル区別（mypy/pyright）
      └───────┬───────┘      ※ランタイムバリデーション
              ↓ YES
         Level 3 (dataclass + Pydantic)
         ※値オブジェクト: @dataclass(frozen=True)
         ※エンティティ: @dataclass
         ※複雑なロジック: class
```

### Level 2の設計方針：NewType + Annotated

**重要な設計方針**: Level 2は `NewType` + `Annotated` の組み合わせで実装します。これにより、**型レベルでの区別（mypy/pyright）**と**ランタイムバリデーション（Pydantic）**の両方を実現します。

#### なぜ NewType + Annotated なのか

1. **型安全性が最優先**: このプロジェクトの目的は、mypy/pyrightによる静的解析で問題を検出できる厳格な型管理です
2. **NewTypeの役割**: 型チェッカーでプリミティブ型を区別し、誤った代入を防止
3. **Annotatedの役割**: バリデーション制約を追加（ランタイム補助保証）

#### バリデーション方法の使い分け

Level 2では、バリデーションに `Field` または `AfterValidator` を使い分けます：

**Field（宣言的制約）**: 単純な制約に使用
```python
from typing import NewType, Annotated
from pydantic import Field

# 範囲制約、長さ制約、パターン制約など
Count = NewType('Count', Annotated[int, Field(ge=0)])
UserId = NewType('UserId', Annotated[str, Field(min_length=8, max_length=20)])
Email = NewType('Email', Annotated[str, Field(pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')])
```

**AfterValidator（カスタムロジック）**: 複雑なバリデーションに使用
```python
from typing import NewType, Annotated
from pydantic import AfterValidator

def validate_module_name(v: str) -> str:
    """モジュール名の複雑なバリデーション"""
    if not v.islower():
        raise ValueError("モジュール名は小文字のみで構成してください")
    if not v.replace("_", "").isalnum():
        raise ValueError("モジュール名は英数字とアンダースコアのみです")
    return v

ModuleName = NewType('ModuleName', Annotated[str, AfterValidator(validate_module_name)])
```

**Field + AfterValidator（併用）**: 宣言的制約 + カスタムロジック
```python
from typing import NewType, Annotated
from pydantic import Field, AfterValidator

def validate_port_range(v: int) -> int:
    """予約ポート範囲のチェック"""
    if 0 < v < 1024:
        raise ValueError(f"ポート {v} は予約されています（1-1023）")
    return v

Port = NewType('Port', Annotated[int, Field(ge=1, le=65535), AfterValidator(validate_port_range)])
```

#### 型チェッカーでの区別

```python
# 型チェッカーでの区別
user_id: UserId = UserId("user-12345")
another_id: str = "string-value"
# user_id = another_id  # ❌ mypyエラー: UserId型とstr型は互換性なし

# ランタイムバリデーション（Pydantic経由）
from pydantic import BaseModel

class User(BaseModel):
    user_id: UserId  # 自動的にmin_length=8がチェックされる
    count: Count     # 自動的にge=0がチェックされる
```

このプロジェクトでは、**型解析による安全性を高める**ことが最優先であり、バリデーションはそれをランタイムで保証するための補助機能です。

### 型定義レベルの自動判定とdocstringによる制御

このプロジェクトには、型定義レベルを自動分析し、適切なレベルへの昇格・降格を推奨する機能があります（`pylay analyze analyze-types`）。

#### 自動判定可能なケース
- **Level 3 → Level 2**: 単一フィールドのみでビジネスロジックメソッドがない → 過剰な実装、Level 2で十分
- **Level 2 → Level 3**: 複雑なバリデータ（10行以上）や複数の関連操作 → BaseModelでカプセル化すべき
- **Level 1 → Level 2**: パターンベース（Email、Path、Count等）や使用箇所が多い → 制約を追加すべき

#### docstringによる明示的制御

自動判定が難しいケースや、意図的に特定のレベルを維持したい場合は、docstringで制御できます：

```python
# Level 1を意図的に維持（軽量な型エイリアスが適切）
type RequestId = str
"""リクエストID型

単純な文字列エイリアス。UUID形式だが、バリデーション不要。

@target-level: level1
@keep-as-is: true
"""

# Level 2への昇格を予告（TODO）
type Email = str
"""メールアドレス型

現在はLevel 1だが、将来的にメール形式バリデーションを追加予定。

@target-level: level2
TODO: Annotated + AfterValidator でメール形式をバリデーション
"""

# 現状維持（将来的な拡張を考慮）
class Config(BaseModel):
    """設定型

    現在は単一フィールドだが、将来的に複数フィールドを追加予定。

    @keep-as-is: true
    """
    value: str
```

### まとめ：型定義レベルの基本方針

1. **Level 1は一時的な状態**: 設計初期や実装途中として許容、最終的にはLevel 2/3への昇格を検討
2. **Level 2が推奨**: 単一値に制約を持たせる場合は、`NewType('TypeName', Annotated[..., AfterValidator(...)])`パターンを使用して型安全性を確保
3. **Level 3は必要な場合のみ**: 複数フィールドやビジネスロジックがある場合のみBaseModelを使用
4. **自動判定 + docstring制御**: システムが推奨を提示、必要に応じてdocstringで制御
5. **段階的な成長**: Level 1から始めて、必要性に応じて昇格させる開発フローを推奨

## 核心原則

### 原則1: 個別型をちゃんと定義し、primitive型を直接使わない

**プロジェクトの設計思想**: このプロジェクトは、**型を軸にした依存関係の洗い出し**と**丁寧な型付けによる設計からの自動実装**を目指しています。そのため、個別型（ドメイン型）の定義を積極的に推奨しています。

#### 低レベル放置を好ましくないとする

**重要な方針**: Level 1（単純な型エイリアス）の状態で長期間放置されていることは推奨されません。

- **Level 1は一時的な状態**: 設計初期段階や実装途中の一時的な状態として許容されますが、最終的にはLevel 2/3への昇格を検討すべきです
- **自動判断可能なケース**:
  - Level 3 ↔ Level 2の判断は、フィールド数やビジネスロジックの有無から自動判断可能
  - 単一フィールドのBaseModel → Level 2へのダウングレード推奨
  - 複雑なバリデータや複数フィールド → Level 3へのアップグレード推奨
- **docstringで制御可能なケース**: Level 1やその他への判断が難しい場合は、docstringで明示的に制御
  - `@target-level: level1` - 意図的にLevel 1を維持（軽量な型エイリアスが適切な場合）
  - `@keep-as-is: true` - 現状維持（レベルアップ・ダウン推奨を無効化）

#### 被参照0の型の扱い

**重要**: 使用されていない型（被参照0の型）は、安易に削除せず、まず以下を確認してください：

1. **実装途中か？**: 開発中の機能で、まだ使用箇所が実装されていない可能性
   - **推奨アクション**: Level 2/3への昇格を検討し、制約やビジネスロジックを追加
2. **認知不足か？**: 型が存在することが知られておらず、既存のprimitive型使用箇所が置き換えられていない可能性
   - **推奨アクション**: primitive型使用箇所を探し、ドメイン型に置き換え
3. **設計意図を確認**: 将来の拡張性を考えた設計意図がある可能性
   - **推奨アクション**: docstringで設計意図を明記し、`@keep-as-is: true`で現状維持を宣言

#### docstringによるレベル制御の例

```python
# Level 1を意図的に維持する例
type UserId = str
"""ユーザーID型

単純な文字列エイリアス。制約は不要で、軽量な型定義が適切。

@target-level: level1
@keep-as-is: true
"""

# Level 2への昇格を明示する例
type Email = str
"""メールアドレス型

現在はLevel 1だが、メール形式バリデーションが必要。

@target-level: level2
TODO: Annotated + AfterValidator でメール形式をバリデーション
"""

# 現状維持（過剰な実装を避ける）
class SimpleConfig(BaseModel):
    """シンプルな設定型

    現在はBaseModelだが、単一フィールドのみで過剰な実装。
    ただし、将来的に複数フィールドを追加予定のため現状維持。

    @keep-as-is: true
    """
    value: str
```

#### ❌ 悪い例（primitive型の直接使用）
```python
def get_user_id(user_data: dict[str, Any]) -> str:
    """ユーザーIDを取得"""
    return user_data["id"]

def validate_age(age: int) -> bool:
    """年齢を検証"""
    return 0 <= age <= 150
```

**問題点**:
- `str` 型のユーザーIDは、どんな文字列も受け付けてしまう
- `int` 型の年齢は、負の値や異常な大きな値も許容してしまう
- 型から意味や制約が読み取れない

#### ✅ 良い例（ドメイン型の定義）
```python
from pydantic import BaseModel, Field, field_validator

class UserId(BaseModel):
    """ユーザーID型

    ユーザーを一意に識別するIDを表します。
    IDは英数字とハイフンのみを許可し、8文字以上である必要があります。
    """
    value: str = Field(..., min_length=8, pattern=r"^[a-zA-Z0-9\-]+$")

    def __str__(self) -> str:
        return self.value

    def __hash__(self) -> int:
        return hash(self.value)

class Age(BaseModel):
    """年齢型

    人間の年齢を表します。0歳以上150歳以下の整数値です。
    """
    value: int = Field(..., ge=0, le=150)

    def is_adult(self) -> bool:
        """成人かどうかを判定"""
        return self.value >= 18

class UserData(BaseModel):
    """ユーザーデータ

    システム内で扱うユーザー情報の基本構造です。
    """
    id: UserId
    name: str = Field(..., min_length=1, max_length=100)
    age: Age
    email: str = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

def get_user_id(user_data: UserData) -> UserId:
    """ユーザーIDを取得"""
    return user_data.id

def validate_age(age: Age) -> bool:
    """年齢を検証"""
    # Ageモデル自体が0-150の範囲を保証しているため、追加検証不要
    return True
```

**改善点**:
- `UserId` 型により、IDの形式が明確になり、不正な値を型レベルで排除
- `Age` 型により、年齢の範囲が保証され、ビジネスロジックメソッド（`is_adult()`）を追加可能
- 型定義自体がドキュメントとして機能し、使用者が制約を理解しやすい

### 原則2: Pydanticによる厳密な型定義でドメイン型を作成する

#### 型定義の3つのレベル

Pythonの型定義には、複雑さに応じて3つのレベルがあります。適切なレベルを選択することで、過剰なエンジニアリングを避け、保守性を高めます。

##### Level 1: 単純な型エイリアス（`type` 文）

**用途**: 制約やバリデーションが不要な、単純な型の別名

```python
# Python 3.12+ の type 文
type UserId = str
type NodeId = str
type Timestamp = float
type JSONData = dict[str, str | int | float | bool | None]

# 使用例
def get_user(user_id: UserId) -> User:
    """ユーザーIDでユーザーを取得"""
    pass
```

**利点**:
- シンプルで読みやすい
- パフォーマンスオーバーヘッドゼロ
- 型ヒントとして明確

**欠点**:
- バリデーションなし
- ランタイムでの型チェックなし

##### Level 2: `NewType` + `Annotated` + (`Field` | `AfterValidator`)（★推奨：プリミティブ型代替）

**用途**: 制約付き型、型レベル区別、再利用可能なバリデーション

```python
from typing import NewType, Annotated
from pydantic import AfterValidator, Field, BaseModel

# バリデータ関数の定義
def validate_module_name(v: str) -> str:
    """モジュール名のバリデーション"""
    if not v.islower():
        raise ValueError("モジュール名は小文字のみで構成してください")
    if not v.replace("_", "").isalnum():
        raise ValueError("モジュール名は英数字とアンダースコアのみです")
    return v

def validate_positive(v: int) -> int:
    """正の整数のバリデーション"""
    if v <= 0:
        raise ValueError(f"正の整数が必要です: {v}")
    return v

# NewType + Annotated型の定義（再利用可能）
ModuleName = NewType(
    'ModuleName',
    Annotated[
        str,
        AfterValidator(validate_module_name),
        Field(min_length=1, max_length=100, description="Pythonモジュール名")
    ]
)

PositiveInt = NewType(
    'PositiveInt',
    Annotated[int, AfterValidator(validate_positive), Field(description="正の整数")]
)

EmailAddress = NewType(
    'EmailAddress',
    Annotated[str, Field(pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")]
)

# Pydantic BaseModelで使用
class ModuleSpec(BaseModel):
    """モジュール仕様"""
    name: ModuleName  # 自動的にバリデーションされる
    version: str
    line_count: PositiveInt
    author_email: EmailAddress | None = None

# 使用例
spec = ModuleSpec(
    name=ModuleName("my_module"),  # validate_module_name が自動実行
    version="1.0.0",
    line_count=PositiveInt(100),    # validate_positive が自動実行
)
```

**利点**:
- **型レベル区別**: mypy/pyrightで異なる型として扱われる
- **再利用可能**: 同じバリデータを複数のモデルで使用
- **型ヒントとして明確**: フィールド定義を見ればバリデーションがわかる
- **パフォーマンス良好**: dataclass/BaseModelより軽量

**欠点**:
- バリデータ関数の定義が必要
- 複雑なビジネスロジックには不向き

##### Level 3: `dataclass` + Pydantic（値オブジェクト・ドメインモデル）

**用途**: 複数フィールド、ビジネスロジック、不変条件がある型

**パターンA: 値オブジェクト（dataclass frozen）**
```python
from dataclasses import dataclass
from pydantic import Field

@dataclass(frozen=True)  # 不変値オブジェクト
class CodeLocation:
    """コード位置を表す値オブジェクト

    ファイルパスと行番号の組み合わせ。
    不変オブジェクトとして扱う。
    """
    file: str = Field(min_length=1)
    line: int = Field(ge=1)
    column: int = Field(ge=0, default=0)

    def format_display(self) -> str:
        """表示用フォーマット"""
        return f"{self.file}:{self.line}:{self.column}"

@dataclass(frozen=True)
class TypeSpec:
    """型仕様の値オブジェクト"""
    name: str
    module: str
    qualified_name: str = Field(min_length=1)

    def to_import_string(self) -> str:
        """import文として出力"""
        return f"from {self.module} import {self.name}"
```

**パターンB: エンティティ（dataclass mutable）**
```python
from dataclasses import dataclass, field
from pydantic import Field

@dataclass  # 状態を持つエンティティ
class AnalysisSession:
    """解析セッション（状態管理）

    解析の進行状況を管理するエンティティ。
    状態の変更を許可する。
    """
    session_id: str = Field(min_length=1)
    start_time: float
    analyzed_files: list[str] = field(default_factory=list)
    error_count: int = Field(ge=0, default=0)

    def add_file(self, file_path: str) -> None:
        """解析済みファイルを追加"""
        if file_path not in self.analyzed_files:
            self.analyzed_files.append(file_path)

    def record_error(self) -> None:
        """エラーカウントを増加"""
        self.error_count += 1

    def is_completed(self) -> bool:
        """セッションが完了したか"""
        return len(self.analyzed_files) > 0
```

**パターンC: 複雑なドメインモデル（BaseModel）**
```python
from pydantic import BaseModel, Field, model_validator

class ModuleAnalysisResult(BaseModel):
    """モジュール解析結果（複雑なドメイン型）

    複数のフィールドと不変条件、ビジネスロジックを持つ。
    """
    module_name: ModuleName  # Level 2の型を活用
    total_lines: int = Field(ge=0)
    code_lines: int = Field(ge=0)
    comment_lines: int = Field(ge=0)
    complexity: float = Field(ge=0.0, le=100.0)

    @model_validator(mode="after")
    def validate_line_counts(self) -> "ModuleAnalysisResult":
        """不変条件: total_lines >= code_lines + comment_lines"""
        if self.total_lines < self.code_lines + self.comment_lines:
            raise ValueError(
                f"行数の整合性エラー: total={self.total_lines}, "
                f"code={self.code_lines}, comment={self.comment_lines}"
            )
        return self

    def complexity_grade(self) -> str:
        """複雑度のグレードを返す（ビジネスロジック）"""
        if self.complexity < 10:
            return "A"
        elif self.complexity < 20:
            return "B"
        elif self.complexity < 30:
            return "C"
        else:
            return "D"

    def is_well_documented(self) -> bool:
        """適切にドキュメント化されているか判定"""
        if self.code_lines == 0:
            return True
        doc_ratio = self.comment_lines / self.code_lines
        return doc_ratio >= 0.2  # コメント率20%以上
```

**利点**:
- **dataclass frozen**: 不変値オブジェクト、hashable、型安全
- **dataclass mutable**: 状態管理、エンティティパターン
- **BaseModel**: 複雑なバリデーション、model_validator、豊富な機能

**欠点**:
- オーバーヘッドあり（単純な型には過剰）
- 記述量が多い

#### 使い分けガイドライン

| レベル | パターン | 用途 | 例 | 型安全性 |
|--------|---------|------|-----|----------|
| 1 | `type` エイリアス | 制約なし型の別名 | `type UserId = str` | ❌ プリミティブと区別されない |
| 2 | `NewType` + `Annotated` | プリミティブ型代替（最頻出） | `UserId = NewType('UserId', Annotated[str, Field(...)])` | ✅ ★型レベル区別 + バリデーション |
| 3a | `dataclass(frozen=True)` | 不変値オブジェクト | `@dataclass(frozen=True)` `class CodeLocation: ...` | ✅ 値オブジェクト |
| 3b | `dataclass` | 状態管理エンティティ | `@dataclass` `class Session: ...` | ✅ エンティティ |
| 3c | `BaseModel` | 複雑なドメインモデル | `class AnalysisResult(BaseModel): ...` | ✅ 複雑なロジック |

**判断フロー**:
```
プリミティブ型の代替が必要？
  ↓ YES → Level 2 (NewType + Annotated) ★最頻出パターン
  ↓ NO
複数フィールドが必要？
  ↓ NO  → Level 1 (type エイリアス)
  ↓ YES
不変値オブジェクト？
  ↓ YES → Level 3a (dataclass frozen)
  ↓ NO
状態管理が必要？
  ↓ YES → Level 3b (dataclass)
  ↓ NO
複雑なバリデーション・ビジネスロジック？
  ↓ YES → Level 3c (BaseModel)
```

#### Pydantic BaseModelの活用パターン

##### パターンA: Value Objectパターン（Level 3の詳細）
複雑なビジネスロジックを持つ単一値のドメイン型

**注**: 単純な制約のみの場合は Level 2 の `Annotated` パターンを優先してください。

```python
from pydantic import BaseModel, Field

class FilePath(BaseModel):
    """ファイルパス型

    ファイルシステム上のパスを表します。
    相対パス・絶対パスの両方をサポートします。
    """
    model_config = ConfigDict(frozen=True)  # イミュータブル

    value: str = Field(..., min_length=1)

    def __str__(self) -> str:
        return self.value

    def is_absolute(self) -> bool:
        """絶対パスかどうかを判定"""
        from pathlib import Path
        return Path(self.value).is_absolute()

    def to_path(self) -> Path:
        """pathlib.Pathオブジェクトに変換"""
        from pathlib import Path
        return Path(self.value)
```

##### パターンB: Entityパターン
複数のフィールドを持つドメインエンティティ

```python
from pydantic import BaseModel, Field, field_validator
from typing import Literal

class NodeType(str, Enum):
    """ノードタイプの列挙型"""
    CLASS = "class"
    FUNCTION = "function"
    MODULE = "module"

class GraphNode(BaseModel):
    """グラフのノードを表すエンティティ

    Attributes:
        id: ノードの一意の識別子
        name: ノードの名前
        node_type: ノードの種類
        qualified_name: 完全修飾名
        attributes: ノードの追加属性
    """
    id: str | None = None
    name: str = Field(..., min_length=1)
    node_type: Literal["class", "function", "module"] | str
    qualified_name: str | None = None
    attributes: dict[str, str | int | float | bool] | None = None

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if self.id is None:
            self.id = self.name

    def is_external(self) -> bool:
        """外部モジュールかどうかを判定"""
        if self.qualified_name:
            return not self.qualified_name.startswith("__main__")
        return False
```

##### パターンC: Configurationパターン
設定情報を型安全に管理

```python
from pydantic import BaseModel, Field
from pathlib import Path
from typing import Literal

class InferenceConfig(BaseModel):
    """型推論設定の強い型定義

    Attributes:
        infer_level: 推論レベル
        max_depth: 最大探索深度
        enable_mypy: mypy統合を有効化
        timeout: タイムアウト（秒）
    """
    model_config = ConfigDict(frozen=True)  # 設定は不変

    infer_level: Literal["loose", "normal", "strict"] = "normal"
    max_depth: int = Field(default=10, ge=1, le=100)
    enable_mypy: bool = True
    timeout: int = Field(default=60, ge=1, le=600)

    def is_strict_mode(self) -> bool:
        """Strictモードか判定"""
        return self.infer_level == "strict"

    def should_use_mypy(self) -> bool:
        """mypy使用すべきか判定"""
        return self.enable_mypy and self.infer_level != "loose"
```

### 原則3: typing モジュールは必要最小限に留める

#### 使用優先順位（Python 3.13基準）

1. **最優先**: Python 3.13 標準の型構文
```python
# ✅ 推奨（Python 3.13標準）
def process(data: str | int | None) -> list[str]:
    pass

# ❌ 非推奨（Python 3.9以前の書き方）
from typing import Union, Optional, List
def process(data: Union[str, int, None]) -> List[str]:
    pass
```

2. **次点**: Python 3.13 のジェネリック型構文とPydantic
```python
from pydantic import BaseModel

# Python 3.13のジェネリック型パラメータ構文（PEP 695）
class Container[T](BaseModel):
    """ジェネリックコンテナ（Python 3.13+）"""
    items: list[T]

    def add(self, item: T) -> None:
        """要素を追加"""
        self.items.append(item)

    def get_first(self) -> T | None:
        """最初の要素を取得"""
        return self.items[0] if self.items else None

# 型エイリアス（Python 3.12+ の type 文）
type Point = tuple[float, float]
type Matrix = list[list[float]]
type JSONValue = str | int | float | bool | None | dict[str, "JSONValue"] | list["JSONValue"]

# 複雑な型エイリアス
type NodeId = str
type EdgeWeight = float
type Graph = dict[NodeId, list[tuple[NodeId, EdgeWeight]]]
```

3. **最終手段**: typing モジュール（以下の場合のみ許可）
   - `Protocol`: インターフェース定義
   - `TypedDict`: 辞書型の構造定義（軽量な型定義が必要な場合）
   - `TypeGuard`: 型ガード関数の戻り値
   - `Callable`: 関数型（複雑な引数パターンを明示する場合）
   - `override`: メソッドのオーバーライドを明示（Python 3.12+）

#### typing使用が許可される例（Python 3.13基準）

```python
from typing import Protocol, TypedDict, TypeGuard, Callable, override
from collections.abc import Sequence

# ✅ Protocol: インターフェース定義
class AnalyzerProtocol(Protocol):
    """解析エンジンのプロトコル定義"""

    def analyze(self, input_path: Path) -> TypeDependencyGraph:
        ...

# ✅ TypedDict: 軽量な構造定義（外部APIレスポンスなど）
class ApiResponse(TypedDict):
    """外部API応答の型定義"""
    status: int
    data: dict[str, Any]
    errors: list[str]

# ✅ TypeGuard: 型ガード関数
def is_valid_infer_level(value: str) -> TypeGuard[Literal["loose", "normal", "strict"]]:
    """infer_levelが有効な値かチェック"""
    return value in ("loose", "normal", "strict")

# ✅ Callable: 複雑な関数型（引数が多い場合など）
type ProcessFunc = Callable[[str, int, bool], tuple[bool, str]]

# ✅ override: メソッドオーバーライドの明示（Python 3.12+）
class ConcreteAnalyzer:
    @override
    def analyze(self, input_path: Path) -> TypeDependencyGraph:
        """Protocolメソッドのオーバーライド"""
        ...
```

#### typing使用が禁止される例（Python 3.13では不要）

```python
# ❌ Union, Optional は Python 3.10+ で不要（3.13では完全に非推奨）
from typing import Union, Optional
def func(x: Union[str, int]) -> Optional[str]:
    pass

# ✅ 代わりに以下を使用（Python 3.13標準）
def func(x: str | int) -> str | None:
    pass

# ❌ List, Dict, Tuple, Set は Python 3.9+ で不要
from typing import List, Dict, Tuple, Set
def func(items: List[str]) -> Dict[str, Tuple[int, int]]:
    pass

# ✅ 代わりに以下を使用（組み込み型で十分）
def func(items: list[str]) -> dict[str, tuple[int, int]]:
    pass

# ✅ NewType は Level 2 の実装に使用（型レベル区別が最優先）
from typing import NewType, Annotated
from pydantic import Field

UserId = NewType('UserId', Annotated[str, Field(min_length=8)])

# 複雑なビジネスロジックが必要な場合は dataclass または BaseModel
from dataclasses import dataclass

@dataclass(frozen=True)  # 値オブジェクト
class User:
    user_id: UserId
    name: str
    created_at: float

    def is_new_user(self) -> bool:
        """新規ユーザーか判定（ビジネスロジック）"""
        import time
        return time.time() - self.created_at < 86400  # 24時間以内

# ❌ TypeAlias は Python 3.12+ の type 文を使用
from typing import TypeAlias
Point: TypeAlias = tuple[float, float]

# ✅ 代わりに以下を使用（Python 3.12+）
type Point = tuple[float, float]
```

### 原則4: 型と実装を分離し、循環参照を防ぐ

#### ディレクトリ構造の基本パターン

```
module_name/
├── types.py          # 型定義のみ（Pydanticモデル、Enum、TypedDict）
├── protocols.py      # Protocolインターフェース定義
├── models.py         # ドメインモデル（型と軽いロジック）
├── services.py       # ビジネスロジック（実装）
└── __init__.py       # 公開APIの定義
```

#### 依存関係の方向

```
services.py  →  models.py  →  types.py
                         ↘
                        protocols.py
```

**重要**: 依存は常に一方向（下位レイヤーから上位レイヤーへの依存は禁止）

#### 実践例: analyzer モジュール

```python
# src/core/analyzer/types.py
"""型定義のみ（依存なし）"""
from pydantic import BaseModel, Field
from typing import Literal

class InferResult(BaseModel):
    """型推論結果を表すモデル"""
    variable_name: str = Field(..., min_length=1)
    inferred_type: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)

    def is_high_confidence(self) -> bool:
        """信頼度が高いか判定"""
        return self.confidence >= 0.8


# src/core/analyzer/protocols.py
"""Protocolインターフェース定義"""
from typing import Protocol
from pathlib import Path
from .types import InferResult  # 型定義のみをインポート

class AnalyzerProtocol(Protocol):
    """解析エンジンのプロトコル定義"""

    def analyze(self, input_path: Path) -> list[InferResult]:
        ...


# src/core/analyzer/models.py
"""ドメインモデル（型 + 軽いロジック）"""
from pydantic import BaseModel, Field
from .types import InferResult

class AnalyzerState(BaseModel):
    """Analyzerの内部状態を管理するモデル"""
    results: list[InferResult] = Field(default_factory=list)
    visited_nodes: set[str] = Field(default_factory=set)

    def add_result(self, result: InferResult) -> None:
        """結果を追加"""
        self.results.append(result)

    def reset(self) -> None:
        """状態をリセット"""
        self.results.clear()
        self.visited_nodes.clear()


# src/core/analyzer/services.py
"""ビジネスロジック実装"""
from pathlib import Path
from .types import InferResult
from .models import AnalyzerState
from .protocols import AnalyzerProtocol

class Analyzer:
    """解析エンジンの実装"""

    def __init__(self) -> None:
        self.state = AnalyzerState()

    def analyze(self, input_path: Path) -> list[InferResult]:
        """解析を実行"""
        # 実装...
        pass
```

## ディレクトリ構造規約

### 型定義の配置場所

#### プロジェクト全体で共有する型
```
src/core/schemas/
├── __init__.py
├── yaml_type_spec.py      # YAML型仕様（プロジェクトの中核）
├── graph_types.py         # グラフ構造の型定義
├── analyzer_types.py      # アナライザー関連の型
└── pylay_config.py        # 設定型定義
```

#### モジュール固有の型
```
src/core/analyzer/
├── __init__.py
├── types.py              # 型定義専用
├── protocols.py          # Protocol定義
├── models.py             # ドメインモデル
├── services.py           # 実装
└── exceptions.py         # 例外クラス
```

### ファイル命名規則

| ファイル名 | 内容 | 依存関係 |
|-----------|------|---------|
| `types.py` | 型定義のみ（BaseModel, Enum, TypedDict） | なし（または最小限） |
| `protocols.py` | Protocol定義 | `types.py` のみ |
| `models.py` | ドメインモデル（型+軽いロジック） | `types.py`, `protocols.py` |
| `services.py` | ビジネスロジック実装 | `types.py`, `protocols.py`, `models.py` |
| `exceptions.py` | 例外クラス | なし（または `types.py`） |

## 型定義パターン集

### パターン1: Value Object（値オブジェクト）

#### 用途
- 単一の値を持つドメイン型
- 不変オブジェクト
- NewTypeの代替

#### テンプレート
```python
from pydantic import BaseModel, Field, ConfigDict

class DomainValue(BaseModel):
    """ドメイン値型

    説明をここに記述します。
    制約や不変条件を明記してください。
    """
    model_config = ConfigDict(frozen=True)  # イミュータブル

    value: str = Field(..., min_length=1, description="値の説明")

    def __str__(self) -> str:
        return self.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, DomainValue):
            return self.value == other.value
        return False

    # ドメインロジックメソッド
    def is_valid_format(self) -> bool:
        """フォーマット検証"""
        pass
```

#### 実例: ModuleName
```python
from pydantic import BaseModel, Field, ConfigDict, field_validator

class ModuleName(BaseModel):
    """Pythonモジュール名型

    Pythonの命名規則に準拠したモジュール名を表します。
    小文字、数字、アンダースコアのみを許可します。
    """
    model_config = ConfigDict(frozen=True)

    value: str = Field(
        ...,
        min_length=1,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="モジュール名（小文字、数字、アンダースコアのみ）"
    )

    @field_validator("value")
    @classmethod
    def validate_not_reserved(cls, v: str) -> str:
        """予約語チェック"""
        reserved = {"import", "class", "def", "return"}
        if v in reserved:
            raise ValueError(f"予約語 '{v}' はモジュール名として使用できません")
        return v

    def __str__(self) -> str:
        return self.value

    def to_path_component(self) -> str:
        """ファイルパス要素に変換"""
        return self.value.replace(".", "/")
```

### パターン2: Entity（エンティティ）

#### 用途
- 識別子を持つドメインオブジェクト
- 複数のフィールドを持つ
- ビジネスロジックを含む

#### テンプレート
```python
from pydantic import BaseModel, Field
from typing import Any

class Entity(BaseModel):
    """エンティティ型

    説明をここに記述します。
    エンティティの責務を明記してください。
    """
    id: str | None = None
    name: str = Field(..., min_length=1)
    # その他のフィールド

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if self.id is None:
            self.id = self._generate_id()

    def _generate_id(self) -> str:
        """IDを自動生成"""
        return self.name

    # ドメインロジックメソッド
    def is_valid(self) -> bool:
        """エンティティの整合性検証"""
        pass
```

#### 実例: GraphNode（既存コード、Python 3.13対応）
```python
from pydantic import BaseModel, Field
from typing import Literal, Any

# Python 3.13の型エイリアス
type NodeId = str
type QualifiedName = str
type NodeAttributes = dict[str, str | int | float | bool]

class GraphNode(BaseModel):
    """グラフのノードを表すエンティティ

    Attributes:
        id: ノードの一意の識別子
        name: ノードの名前
        node_type: ノードの種類
        qualified_name: 完全修飾名
        attributes: ノードの追加属性
    """
    id: NodeId | None = None
    name: str = Field(..., min_length=1)
    node_type: Literal["class", "function", "module"] | str
    qualified_name: QualifiedName | None = None
    attributes: NodeAttributes | None = None

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if self.id is None:
            self.id = self.name

    def is_external(self) -> bool:
        """外部モジュールかどうかを判定"""
        if self.qualified_name:
            return not self.qualified_name.startswith("__main__")
        return False

    def get_display_name(self) -> str:
        """表示用の名前を取得"""
        return self.qualified_name if self.qualified_name else self.name
```

### パターン3: Configuration（設定）

#### 用途
- アプリケーション設定
- 不変な設定オブジェクト
- 環境依存の値

#### テンプレート
```python
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal

class AppConfig(BaseModel):
    """アプリケーション設定

    説明をここに記述します。
    設定項目の意味と制約を明記してください。
    """
    model_config = ConfigDict(frozen=True)  # 設定は不変

    mode: Literal["development", "production"] = "development"
    max_workers: int = Field(default=4, ge=1, le=32)
    timeout: int = Field(default=60, ge=1, le=600)

    def is_production(self) -> bool:
        """本番環境かどうかを判定"""
        return self.mode == "production"

    @classmethod
    def from_env(cls) -> "AppConfig":
        """環境変数から設定を読み込み"""
        import os
        return cls(
            mode=os.getenv("APP_MODE", "development"),
            max_workers=int(os.getenv("MAX_WORKERS", "4")),
        )
```

#### 実例: InferenceConfig（既存コード）
```python
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal

class InferenceConfig(BaseModel):
    """型推論設定の強い型定義

    Attributes:
        infer_level: 推論レベル（loose, normal, strict）
        max_depth: 最大探索深度
        enable_mypy: mypy統合を有効化
        timeout: タイムアウト（秒）
    """
    model_config = ConfigDict(frozen=True)

    infer_level: Literal["loose", "normal", "strict"] = "normal"
    max_depth: int = Field(default=10, ge=1, le=100)
    enable_mypy: bool = True
    timeout: int = Field(default=60, ge=1, le=600)

    def is_strict_mode(self) -> bool:
        """Strictモードか判定"""
        return self.infer_level == "strict"

    def should_use_mypy(self) -> bool:
        """mypy使用すべきか判定"""
        return self.enable_mypy and self.infer_level != "loose"
```

### パターン4: Enum（列挙型）

#### 用途
- 固定された選択肢
- 状態やフラグ
- 定数のグループ化

#### テンプレート
```python
from enum import Enum

class Status(str, Enum):
    """ステータス列挙型

    説明をここに記述します。
    各値の意味を明記してください。
    """
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

    def is_terminal(self) -> bool:
        """終了状態かどうかを判定"""
        return self in (Status.COMPLETED, Status.FAILED)
```

#### 実例: RelationType（既存コード）
```python
from enum import Enum

class RelationType(str, Enum):
    """関係の種類を定義する列挙型"""

    DEPENDS_ON = "depends_on"
    INHERITS_FROM = "inherits_from"
    IMPLEMENTS = "implements"
    REFERENCES = "references"
    USES = "uses"
    RETURNS = "returns"
    CALLS = "calls"
    ARGUMENT = "argument"
    ASSIGNMENT = "assignment"
    GENERIC = "generic"
```

### パターン5: TypedDict（軽量型定義）

#### 用途
- 外部APIレスポンス
- 辞書型の構造定義
- Pydanticのオーバーヘッドが不要な場合

#### テンプレート
```python
from typing import TypedDict

class ResponseData(TypedDict):
    """API応答データの型定義

    説明をここに記述します。
    各フィールドの意味を明記してください。
    """
    status: int
    message: str
    data: dict[str, Any]
    errors: list[str]
```

#### 実例: CheckSummary（既存コード）
```python
from typing import TypedDict

class CheckSummary(TypedDict):
    """analyze_issues.pyのサマリー型"""

    total_checks: int
    successful_checks: int
    failed_checks: int
    checks_with_issues: int
    results: list[dict[str, object]]
```

### パターン6: Protocol（インターフェース）

#### 用途
- 構造的部分型（Structural Subtyping）
- 循環インポート回避
- インターフェース定義

#### テンプレート
```python
from typing import Protocol

class ServiceProtocol(Protocol):
    """サービスのプロトコル定義

    説明をここに記述します。
    インターフェースの責務を明記してください。
    """

    def process(self, data: str) -> bool:
        """処理を実行

        Args:
            data: 処理対象データ

        Returns:
            処理成功の場合True
        """
        ...
```

#### 実例: AnalyzerProtocol（既存コード）
```python
from typing import Protocol
from pathlib import Path
from src.core.schemas.graph_types import TypeDependencyGraph

class AnalyzerProtocol(Protocol):
    """解析エンジンのプロトコル定義

    型推論と依存関係抽出を統一的に扱うインターフェース。
    """

    def analyze(self, input_path: Path | str) -> TypeDependencyGraph:
        """指定された入力から型依存グラフを生成

        Args:
            input_path: 解析対象のファイルパスまたはコード文字列

        Returns:
            生成された型依存グラフ

        Raises:
            ValueError: 入力が無効な場合
            RuntimeError: 解析に失敗した場合
        """
        ...
```

## バリデーション戦略

### Pydantic Fieldによる値保証

#### 基本的なバリデーション

```python
from pydantic import BaseModel, Field

class UserProfile(BaseModel):
    """ユーザープロフィール"""

    # 文字列長の制約
    username: str = Field(..., min_length=3, max_length=20)

    # 数値範囲の制約
    age: int = Field(..., ge=0, le=150)

    # 正規表現パターンの制約
    email: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )

    # デフォルト値の指定
    is_active: bool = Field(default=True)

    # 説明の追加
    bio: str | None = Field(
        default=None,
        max_length=500,
        description="ユーザーの自己紹介文"
    )
```

#### カスタムバリデーター

```python
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Any

class Password(BaseModel):
    """パスワード型"""

    value: str = Field(..., min_length=8)

    @field_validator("value")
    @classmethod
    def validate_complexity(cls, v: str) -> str:
        """パスワード複雑性を検証"""
        if not any(c.isupper() for c in v):
            raise ValueError("大文字を少なくとも1文字含む必要があります")
        if not any(c.islower() for c in v):
            raise ValueError("小文字を少なくとも1文字含む必要があります")
        if not any(c.isdigit() for c in v):
            raise ValueError("数字を少なくとも1文字含む必要があります")
        return v

class DateRange(BaseModel):
    """日付範囲型"""

    start_date: str
    end_date: str

    @model_validator(mode="after")
    def validate_date_order(self) -> "DateRange":
        """開始日が終了日より前であることを検証"""
        from datetime import datetime

        start = datetime.fromisoformat(self.start_date)
        end = datetime.fromisoformat(self.end_date)

        if start >= end:
            raise ValueError("開始日は終了日より前である必要があります")

        return self
```

#### バリデーションモード

```python
from pydantic import BaseModel, Field, ValidationError

class StrictModel(BaseModel):
    """厳格なバリデーション"""

    # 厳密な型チェック（文字列→整数の自動変換を禁止）
    count: int = Field(..., strict=True)

    # カスタムバリデーター
    @field_validator("count")
    @classmethod
    def check_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("正の整数である必要があります")
        return v

# 使用例
try:
    model = StrictModel(count="10")  # ValidationError: 文字列→整数の変換禁止
except ValidationError as e:
    print(e)

model = StrictModel(count=10)  # OK
```

### バリデーション戦略のベストプラクティス

1. **可能な限りFieldで制約を定義する**
   - `min_length`, `max_length`, `ge`, `le`, `pattern` を活用
   - 宣言的で読みやすい

2. **複雑な条件は field_validator を使用**
   - ビジネスルールのバリデーション
   - 複数フィールドの相互依存チェック

3. **model_validator はモデル全体の整合性チェックに使用**
   - フィールド間の関係性検証
   - 複合的な制約

4. **エラーメッセージは具体的に**
   - 何が問題なのかを明確に伝える
   - ユーザーがどう修正すべきかを示す

## 型参照ルール

### 前方参照（Forward Reference）

#### 問題: クラス定義前の型参照

```python
# ❌ エラー: User が定義される前に参照
class Post(BaseModel):
    author: User  # NameError
    content: str

class User(BaseModel):
    name: str
```

#### 解決策1: 文字列による前方参照

```python
from __future__ import annotations  # Python 3.7+

class Post(BaseModel):
    author: "User"  # 文字列として参照
    content: str

class User(BaseModel):
    name: str

# モデル再構築（必須）
Post.model_rebuild()
```

#### 解決策2: 型定義の分離

```python
# types.py
from pydantic import BaseModel

class User(BaseModel):
    name: str

class Post(BaseModel):
    author: User  # User は既に定義済み
    content: str
```

### 循環参照（Circular Reference）

#### 問題: 相互参照する型

```python
# ❌ 循環参照
class Node(BaseModel):
    value: str
    children: list[Node]  # 自己参照

class Tree(BaseModel):
    root: Node
```

#### 解決策1: model_rebuild による解決

```python
from __future__ import annotations
from pydantic import BaseModel

class Node(BaseModel):
    value: str
    children: list[Node] = []  # 自己参照

# モデル再構築
Node.model_rebuild()

class Tree(BaseModel):
    root: Node

# 使用例
root = Node(value="root", children=[
    Node(value="child1"),
    Node(value="child2", children=[
        Node(value="grandchild")
    ])
])
```

#### 解決策2: 参照プレースホルダーの使用（プロジェクト独自パターン）

```python
from pydantic import BaseModel, Field
from typing import Any

class RefPlaceholder(BaseModel):
    """参照文字列を保持するプレースホルダー"""

    type: Literal["ref"] = "ref"
    ref_name: str

    def __str__(self) -> str:
        return self.ref_name

class TypeSpec(BaseModel):
    """型仕様の基底モデル"""
    name: str | None = None
    type: str

class ListTypeSpec(TypeSpec):
    """リスト型の仕様"""
    type: Literal["list"] = "list"
    items: Any  # str（参照）または TypeSpec

    @field_validator("items", mode="before")
    @classmethod
    def validate_items(cls, v: Any) -> Any:
        """参照文字列の処理"""
        if isinstance(v, str):
            return v  # 参照文字列として保持
        if isinstance(v, dict):
            return TypeSpec(**v)
        return v

# 使用例
list_spec = ListTypeSpec(
    name="StringList",
    type="list",
    items="str"  # 参照文字列
)
```

### モジュール間の型参照

#### パターン: 型定義の集約

```python
# src/core/schemas/__init__.py
"""共通型定義の公開API"""

from .graph_types import GraphNode, GraphEdge, TypeDependencyGraph
from .yaml_type_spec import TypeSpec, TypeRoot
from .analyzer_types import InferResult, MypyResult

__all__ = [
    "GraphNode",
    "GraphEdge",
    "TypeDependencyGraph",
    "TypeSpec",
    "TypeRoot",
    "InferResult",
    "MypyResult",
]
```

```python
# 他のモジュールからの参照
from src.core.schemas import GraphNode, TypeDependencyGraph

def process_graph(graph: TypeDependencyGraph) -> list[GraphNode]:
    return graph.nodes
```

## 既存コード移行ガイド

### 段階的リファクタリング手順

#### Step 1: 型定義の抽出

**Before:**
```python
# service.py
def get_user(user_id: str) -> dict[str, Any]:
    """ユーザー情報を取得"""
    return {
        "id": user_id,
        "name": "John Doe",
        "age": 30
    }
```

**After:**
```python
# types.py
from pydantic import BaseModel, Field

class UserId(BaseModel):
    """ユーザーID型"""
    value: str = Field(..., min_length=8)

    def __str__(self) -> str:
        return self.value

class User(BaseModel):
    """ユーザー情報"""
    id: UserId
    name: str = Field(..., min_length=1)
    age: int = Field(..., ge=0, le=150)

# service.py
from .types import UserId, User

def get_user(user_id: UserId) -> User:
    """ユーザー情報を取得"""
    return User(
        id=user_id,
        name="John Doe",
        age=30
    )
```

#### Step 2: バリデーションの追加

**Before:**
```python
def set_age(user: User, age: int) -> None:
    if age < 0 or age > 150:
        raise ValueError("Invalid age")
    user.age = age
```

**After:**
```python
# types.py に Age 型を追加
class Age(BaseModel):
    """年齢型"""
    value: int = Field(..., ge=0, le=150)

    def is_adult(self) -> bool:
        return self.value >= 18

class User(BaseModel):
    """ユーザー情報"""
    id: UserId
    name: str = Field(..., min_length=1)
    age: Age

# service.py
def set_age(user: User, age: Age) -> None:
    """年齢を設定（バリデーションは Age 型で保証）"""
    user.age = age
```

#### Step 3: ドメインロジックの移行

**Before:**
```python
# service.py
def is_adult(user: User) -> bool:
    """成人判定"""
    return user.age >= 18

def format_user_display(user: User) -> str:
    """表示用フォーマット"""
    return f"{user.name} (ID: {user.id})"
```

**After:**
```python
# types.py の User クラスにメソッドを追加
class User(BaseModel):
    """ユーザー情報"""
    id: UserId
    name: str = Field(..., min_length=1)
    age: Age

    def is_adult(self) -> bool:
        """成人判定"""
        return self.age.is_adult()

    def format_display(self) -> str:
        """表示用フォーマット"""
        return f"{self.name} (ID: {self.id})"

# service.py
def process_user(user: User) -> None:
    """ユーザー処理"""
    if user.is_adult():
        print(user.format_display())
```

### 移行時の注意点

1. **後方互換性を保つ**
   - 既存のインターフェースを維持
   - 型変換用のヘルパーメソッドを提供

```python
class UserId(BaseModel):
    value: str

    @classmethod
    def from_string(cls, s: str) -> "UserId":
        """文字列から変換"""
        return cls(value=s)

    def to_string(self) -> str:
        """文字列へ変換"""
        return self.value
```

2. **テストの更新**
   - 型定義の変更に合わせてテストを更新
   - バリデーションのテストを追加

```python
import pytest
from pydantic import ValidationError

def test_user_id_validation():
    """UserId型のバリデーション"""
    # 正常ケース
    user_id = UserId(value="user-12345")
    assert str(user_id) == "user-12345"

    # 異常ケース
    with pytest.raises(ValidationError):
        UserId(value="abc")  # 長さが不足
```

3. **段階的な移行**
   - 一度にすべてを変更しない
   - モジュール単位で段階的に移行

## チェックリスト

### コードレビュー時の確認項目

#### 型定義の品質
- [ ] primitive型を直接使用していないか？
- [ ] Pydantic BaseModelで適切にドメイン型を定義しているか？
- [ ] Field制約でバリデーションを宣言的に記述しているか？
- [ ] docstringで型の意味と制約を説明しているか？

#### 型参照の整理
- [ ] typing モジュールの使用が必要最小限か？
- [ ] Python 3.13+ の標準型構文を使用しているか？
- [ ] 前方参照や循環参照が適切に処理されているか？
- [ ] model_rebuild() が必要な箇所で呼ばれているか？

#### ディレクトリ構造
- [ ] 型定義が適切なファイルに配置されているか？（types.py, protocols.py, models.py）
- [ ] 依存関係が一方向になっているか？（循環依存がないか）
- [ ] 公開APIが __init__.py で明示されているか？

#### バリデーション
- [ ] Field制約が適切に設定されているか？
- [ ] カスタムバリデーターが必要な箇所に実装されているか？
- [ ] エラーメッセージが具体的で分かりやすいか？

#### ドメインロジック
- [ ] 型定義にドメインロジックメソッドが適切に配置されているか？
- [ ] Value Objectは不変（frozen=True）になっているか？
- [ ] Entityには識別子（id）が定義されているか？

### 新規実装時のチェックリスト

#### 設計フェーズ
- [ ] ドメイン型を洗い出したか？
- [ ] 型の責務を明確にしたか？
- [ ] 型間の関係性を整理したか？
- [ ] バリデーションルールを定義したか？

#### 実装フェーズ
- [ ] types.py に型定義を記述したか？
- [ ] Pydantic Fieldで制約を宣言したか？
- [ ] docstringを日本語で記述したか？
- [ ] ドメインロジックメソッドを実装したか？
- [ ] 型変換ヘルパーメソッドを実装したか？

#### テストフェーズ
- [ ] 正常系のテストを書いたか？
- [ ] バリデーションエラーのテストを書いたか？
- [ ] エッジケースのテストを書いたか？

#### ドキュメントフェーズ
- [ ] 型定義のdocstringが完全か？
- [ ] 使用例を記述したか？
- [ ] 制約や不変条件を明記したか？

## まとめ

### 型定義の原則（再掲）

1. **個別型をちゃんと定義し、primitive型を直接使わない**
2. **Pydanticによる厳密な型定義でドメイン型を作成する**
3. **typing モジュールは必要最小限に留める（Python 3.13標準を優先）**
4. **型と実装を分離し、循環参照を防ぐ**

### Python 3.13における型定義のベストプラクティス

#### DO（推奨）
- ✅ `str | int | None` を使用（Union型の簡潔表記）
- ✅ `list[str]`, `dict[str, int]` を使用（組み込み型ジェネリクス）
- ✅ `class Container[T]` を使用（型パラメータ構文）
- ✅ `type Point = tuple[float, float]` を使用（type文）
- ✅ `NewType` + `Annotated` + `Field` で Level 2 型を定義（★最頻出パターン）
- ✅ `dataclass(frozen=True)` で不変値オブジェクトを定義
- ✅ `dataclass` でエンティティを定義
- ✅ Pydantic BaseModel で複雑なドメイン型を定義
- ✅ Field制約でバリデーションを宣言的に記述
- ✅ 型定義を types.py に集約

#### DON'T（非推奨・禁止）
- ❌ `Union[str, int]` を使用（Python 3.10+では不要）
- ❌ `Optional[str]` を使用（`str | None` を使用）
- ❌ `List[str]`, `Dict[str, int]` を使用（Python 3.9+では不要）
- ❌ `TypeVar('T')` と `Generic[T]` を使用（Python 3.12+では不要）
- ❌ `TypeAlias` を使用（`type` 文を使用）
- ❌ primitive型を直接使用（Level 2: NewType + Annotated を使用）
- ❌ 単純な制約のために BaseModel を使用（Level 2 または dataclass で十分）

### プロジェクトへの影響

このルールを遵守することで、以下の効果が期待できます：

- **型安全性の向上**: 不正な値の流入を型レベルで防止
- **バグの早期発見**: 型チェッカー（mypy, Pyright）による静的解析
- **ドキュメントの自己生成**: 型定義がそのままドキュメントとして機能
- **コードの可読性向上**: 型名から意味が明確に伝わる
- **保守性の向上**: 型を変更すれば影響箇所が自動的に検出される

### 継続的な改善

このルールは固定されたものではなく、プロジェクトの成長に合わせて更新されます。

- 新しいパターンの発見
- ベストプラクティスの追加
- アンチパターンの事例追加

---

## 付録: Python 3.13型システムの参考資料

### 公式PEP（Python Enhancement Proposals）
- **PEP 585**: Type Hinting Generics In Standard Collections（Python 3.9+）
  - `list[str]`, `dict[str, int]` などの組み込み型ジェネリクス
- **PEP 604**: Allow writing union types as X | Y（Python 3.10+）
  - Union型の簡潔表記
- **PEP 695**: Type Parameter Syntax（Python 3.12+）
  - `class Container[T]` および `type` 文
- **PEP 692**: TypedDict and Required/NotRequired（Python 3.11+）
  - TypedDictの柔軟な型定義

### 推奨リソース
- [Pydantic公式ドキュメント](https://docs.pydantic.dev/)
- [Python公式型ヒントドキュメント](https://docs.python.org/3/library/typing.html)
- [mypy公式ドキュメント](https://mypy.readthedocs.io/)

### プロジェクト固有の型定義例
- [src/core/schemas/graph_types.py](src/core/schemas/graph_types.py): グラフ構造の型定義
- [src/core/schemas/yaml_type_spec.py](src/core/schemas/yaml_type_spec.py): YAML型仕様
- [src/core/analyzer/models.py](src/core/analyzer/models.py): アナライザーモデル

---

**更新履歴**:
- 2025-10-01: 初版作成（Python 3.13基準）
