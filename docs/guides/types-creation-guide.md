# types.py 作成ガイドライン

このガイドでは、pylayプロジェクトにおける `types.py` の作成方法とベストプラクティスを説明します。

## 目次

- [types.pyの役割](#typespyの役割)
- [配置する型の判断基準](#配置する型の判断基準)
- [Level 2パターン（最頻出）](#level-2パターン最頻出)
- [実装パターン集](#実装パターン集)
- [チェックリスト](#チェックリスト)
- [よくある質問](#よくある質問)

## types.pyの役割

`types.py` は、モジュール固有の型定義を集約し、**プリミティブ型の直接使用を防ぐ**ための中心的なファイルです。

**目的**:
- プリミティブ型（`str`, `int`, `float`等）の直接使用を避ける
- ドメイン型を明確にする（`UserId`, `FilePath`等）
- 型安全性を向上させる

**配置する型のレベル**:
- **Level 1**: `type` エイリアス（制約なし）— 一時的な状態
- **Level 2**: `NewType` + ファクトリ関数 + `TypeAdapter`（★プリミティブ型代替、最頻出パターン）
- Level 3は `models.py` に配置（`dataclass`, `BaseModel`）

## 配置する型の判断基準

新しい型を定義する際は、以下のフローチャートに従って配置先を決定します:

```
型定義が必要
    ↓
【質問1】複数モジュールで使用される？
    YES → src/core/schemas/types.py
    NO  → 続ける
    ↓
【質問2】複雑なビジネスロジックを持つ？
    YES → models.py (Level 3: BaseModel/dataclass)
    NO  → 続ける
    ↓
【質問3】制約やバリデーションが必要？
    YES → types.py (Level 2: NewType + ファクトリ)
    NO  → types.py (Level 1: type エイリアス)
```

**例**:

| 型名 | 配置先 | 理由 |
|------|--------|------|
| `UserId` | types.py (Level 2) | プリミティブ型代替、制約あり |
| `Timestamp` | types.py (Level 1) | 単純なエイリアス |
| `User` | models.py (Level 3) | 複雑なドメインモデル |
| `FilePath` | schemas/types.py | 複数モジュールで使用 |

## Level 2パターン（最頻出）

Level 2は、**プリミティブ型の代替**として最も頻繁に使用されるパターンです。

### 基本構文

```python
from typing import NewType, Annotated
from pydantic import Field, TypeAdapter

# 1. NewType定義
UserId = NewType('UserId', str)

# 2. バリデーター定義
UserIdValidator = TypeAdapter(Annotated[str, Field(min_length=8, max_length=32)])

# 3. ファクトリ関数定義
def create_user_id(value: str) -> UserId:
    """ユーザーIDを作成する

    Args:
        value: ユーザーID文字列（8-32文字）

    Returns:
        検証済みのUserId

    Raises:
        ValidationError: バリデーションに失敗した場合
    """
    validated = UserIdValidator.validate_python(value)
    return UserId(validated)
```

### @validate_call パターン

関数デコレーターを使用するパターンもあります:

```python
from pydantic import validate_call

Count = NewType('Count', int)

@validate_call
def Count(value: Annotated[int, Field(ge=0)]) -> Count:  # type: ignore[no-redef]
    """非負整数のカウント型を作成する"""
    return NewType('Count', int)(value)

# 使用例
count = Count(10)  # OK
count = Count(-1)  # ValidationError
```

**どちらを選ぶか？**

| パターン | 推奨ケース |
|----------|-----------|
| ファクトリ関数 | 明示的な型変換が必要な場合（推奨） |
| @validate_call | 関数呼び出し構文を好む場合 |

## 実装パターン集

### パターン1: 文字列型の制約

```python
from typing import NewType, Annotated
from pydantic import Field, TypeAdapter

# Email
Email = NewType('Email', str)
EmailValidator = TypeAdapter(
    Annotated[str, Field(pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')]
)

def create_email(value: str) -> Email:
    """メールアドレスを作成する"""
    validated = EmailValidator.validate_python(value)
    return Email(validated)

# FilePath
FilePath = NewType('FilePath', str)
FilePathValidator = TypeAdapter(Annotated[str, Field(min_length=1)])

def create_file_path(value: str) -> FilePath:
    """ファイルパスを作成する"""
    validated = FilePathValidator.validate_python(value)
    return FilePath(validated)

# ModuleName
ModuleName = NewType('ModuleName', str)
ModuleNameValidator = TypeAdapter(
    Annotated[str, Field(pattern=r'^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*$')]
)

def create_module_name(value: str) -> ModuleName:
    """Pythonモジュール名を作成する"""
    validated = ModuleNameValidator.validate_python(value)
    return ModuleName(validated)
```

### パターン2: 数値型の制約

```python
from typing import NewType, Annotated
from pydantic import Field, TypeAdapter

# Count (非負整数)
Count = NewType('Count', int)
CountValidator = TypeAdapter(Annotated[int, Field(ge=0)])

def create_count(value: int) -> Count:
    """非負整数のカウントを作成する"""
    validated = CountValidator.validate_python(value)
    return Count(validated)

# Score (0-100)
Score = NewType('Score', int)
ScoreValidator = TypeAdapter(Annotated[int, Field(ge=0, le=100)])

def create_score(value: int) -> Score:
    """0-100のスコアを作成する"""
    validated = ScoreValidator.validate_python(value)
    return Score(validated)

# ConfidenceScore (0.0-1.0)
ConfidenceScore = NewType('ConfidenceScore', float)
ConfidenceScoreValidator = TypeAdapter(
    Annotated[float, Field(ge=0.0, le=1.0)]
)

def create_confidence_score(value: float) -> ConfidenceScore:
    """0.0-1.0の信頼度スコアを作成する"""
    validated = ConfidenceScoreValidator.validate_python(value)
    return ConfidenceScore(validated)
```

### パターン3: Path型の制約

```python
from typing import NewType, Annotated
from pathlib import Path
from pydantic import Field, TypeAdapter

# SourcePath
SourcePath = NewType('SourcePath', Path)
SourcePathValidator = TypeAdapter(Annotated[Path, Field()])

def create_source_path(value: Path | str) -> SourcePath:
    """ソースファイルパスを作成する"""
    if isinstance(value, str):
        value = Path(value)
    validated = SourcePathValidator.validate_python(value)
    return SourcePath(validated)

# OutputPath
OutputPath = NewType('OutputPath', Path)
OutputPathValidator = TypeAdapter(Annotated[Path, Field()])

def create_output_path(value: Path | str) -> OutputPath:
    """出力ファイルパスを作成する"""
    if isinstance(value, str):
        value = Path(value)
    validated = OutputPathValidator.validate_python(value)
    return OutputPath(validated)
```

### パターン4: 列挙型を使ったドメイン型

```python
from typing import NewType, Literal, Annotated
from pydantic import Field, TypeAdapter

# TypeLevel (Level 1/2/3のいずれか)
TypeLevel = NewType('TypeLevel', Literal['level1', 'level2', 'level3'])
TypeLevelValidator = TypeAdapter(
    Annotated[Literal['level1', 'level2', 'level3'], Field()]
)

def create_type_level(value: str) -> TypeLevel:
    """型レベルを作成する"""
    validated = TypeLevelValidator.validate_python(value)
    return TypeLevel(validated)

# Priority (high/medium/low)
Priority = NewType('Priority', Literal['high', 'medium', 'low'])
PriorityValidator = TypeAdapter(
    Annotated[Literal['high', 'medium', 'low'], Field()]
)

def create_priority(value: str) -> Priority:
    """優先度を作成する"""
    validated = PriorityValidator.validate_python(value)
    return Priority(validated)
```

### パターン5: Level 1（型エイリアス）

Level 1は一時的な状態であり、将来Level 2への昇格を検討してください。

```python
# 単純な型エイリアス（制約なし）
type Timestamp = float
type YamlString = str
type JsonString = str

# docstringで設計意図を明記
type Timestamp = float
"""
UNIXタイムスタンプ

**注意**: 現在はLevel 1（単純なエイリアス）ですが、
将来的にISO 8601形式への変換機能を持つLevel 2への昇格を検討。

**使用例**:
    timestamp: Timestamp = time.time()
"""
```

## チェックリスト

新しい `types.py` を作成する際の確認事項:

### 必須項目

- [ ] モジュール名に `types.py` を使用している
- [ ] Level 1/2の型定義のみを配置している（Level 3は `models.py`）
- [ ] すべての型にdocstringを記述している
- [ ] NewType定義にはファクトリ関数を提供している
- [ ] バリデーターは `TypeAdapter` + `Annotated` を使用している

### 推奨項目

- [ ] プリミティブ型の直接使用を避けている
- [ ] 型名がドメイン概念を明確に表現している
- [ ] ファクトリ関数名は `create_*` パターンを使用している
- [ ] docstringに使用例を含めている
- [ ] 型の設計意図を明記している

### 禁止項目

- [ ] ❌ `models.py` や他のファイルからのimport（循環import防止）
- [ ] ❌ Level 3型（BaseModel, dataclass）の配置
- [ ] ❌ ビジネスロジックの実装
- [ ] ❌ グローバル状態の保持

## よくある質問

### Q1: Level 1とLevel 2のどちらを使うべきか？

**A**: 原則として **Level 2を優先** してください。Level 1は一時的な状態です。

```python
# ❌ Level 1（一時的）
type UserId = str

# ✅ Level 2（推奨）
UserId = NewType('UserId', str)
UserIdValidator = TypeAdapter(Annotated[str, Field(min_length=8)])

def create_user_id(value: str) -> UserId:
    validated = UserIdValidator.validate_python(value)
    return UserId(validated)
```

### Q2: ファクトリ関数は必須か？

**A**: Level 2では **必須** です。NewType単体では型安全性が不十分です。

```python
# ❌ NewType単体（バリデーションなし）
UserId = NewType('UserId', str)
user_id = UserId("")  # 空文字列でもOK（危険）

# ✅ ファクトリ関数（バリデーションあり）
def create_user_id(value: str) -> UserId:
    if len(value) < 8:
        raise ValueError("UserId must be at least 8 characters")
    return UserId(value)

user_id = create_user_id("")  # ValueError（安全）
```

### Q3: 複数モジュールで使う型はどこに配置する？

**A**: `src/core/schemas/types.py` に配置してください。

```python
# src/core/schemas/types.py
FilePath = NewType('FilePath', str)
# ... (ファクトリ関数等)

# src/core/converters/types.py
from ..schemas.types import FilePath  # ✅ OK

# src/core/analyzer/types.py
from ..schemas.types import FilePath  # ✅ OK
```

### Q4: TypeAdapterとvalidate_callの使い分けは？

**A**: **TypeAdapterを推奨** します（明示的なバリデーション）。

| パターン | メリット | デメリット |
|----------|---------|-----------|
| TypeAdapter | 明示的、再利用可能 | 少し冗長 |
| @validate_call | 簡潔 | 関数デコレーター必要 |

```python
# ✅ TypeAdapter（推奨）
UserId = NewType('UserId', str)
UserIdValidator = TypeAdapter(Annotated[str, Field(min_length=8)])

def create_user_id(value: str) -> UserId:
    validated = UserIdValidator.validate_python(value)
    return UserId(validated)

# ⚠️ @validate_call（簡潔だがデコレーター必要）
@validate_call
def UserId(value: Annotated[str, Field(min_length=8)]) -> UserId:  # type: ignore[no-redef]
    return NewType('UserId', str)(value)
```

### Q5: docstringには何を書くべきか？

**A**: 以下の情報を含めてください:

```python
UserId = NewType('UserId', str)
"""
ユーザー識別子

**制約**:
- 8-32文字
- 英数字とアンダースコアのみ

**設計意図**:
- ユーザーIDと他の文字列を型レベルで区別
- データベース主キーとして使用

**使用例**:
    user_id = create_user_id("user_12345678")
    # user_id: UserId

**関連型**:
- GroupId: グループ識別子
- SessionId: セッション識別子
"""
```

### Q6: 既存のプリミティブ型をどう置き換える？

**A**: 段階的に置き換えます（詳細は[移行ガイド](./migration-guide.md)参照）。

```python
# Step 1: types.pyに型定義を追加
UserId = NewType('UserId', str)
# ... (バリデーター、ファクトリ関数)

# Step 2: 新規コードで使用
def get_user(user_id: UserId) -> User:
    ...

# Step 3: 既存コードを段階的に置き換え
def get_user(user_id: str) -> User:  # 旧
    ...
↓
def get_user(user_id: UserId) -> User:  # 新
    ...
```

## 実践例

完全な `types.py` の例:

```python
"""converters モジュールの型定義

このモジュールは、型変換機能で使用される基本的な型定義を提供します。
全ての型はLevel 1またはLevel 2として定義されています。
"""

from typing import NewType, Annotated, Literal
from pathlib import Path
from pydantic import Field, TypeAdapter, validate_call

# =============================================================================
# Level 1: 型エイリアス（制約なし）
# =============================================================================

type YamlString = str
"""YAML形式の文字列"""

type Timestamp = float
"""UNIXタイムスタンプ"""

# =============================================================================
# Level 2: NewType + ファクトリ関数（プリミティブ型代替）
# =============================================================================

# --- Path型 ---

SourcePath = NewType('SourcePath', Path)
"""ソースファイルのパス"""

SourcePathValidator = TypeAdapter(Annotated[Path, Field()])

def create_source_path(value: Path | str) -> SourcePath:
    """ソースファイルパスを作成する

    Args:
        value: ファイルパス

    Returns:
        検証済みのSourcePath
    """
    if isinstance(value, str):
        value = Path(value)
    validated = SourcePathValidator.validate_python(value)
    return SourcePath(validated)


OutputPath = NewType('OutputPath', Path)
"""出力ファイルのパス"""

OutputPathValidator = TypeAdapter(Annotated[Path, Field()])

def create_output_path(value: Path | str) -> OutputPath:
    """出力ファイルパスを作成する

    Args:
        value: パス（PathまたはString）

    Returns:
        検証済みの出力パス
    """
    if isinstance(value, str):
        value = Path(value)
    validated = OutputPathValidator.validate_python(value)
    return OutputPath(validated)

# --- Count型 ---

ConversionCount = NewType('ConversionCount', int)
"""変換した型の数"""

ConversionCountValidator = TypeAdapter(Annotated[int, Field(ge=0)])

def create_conversion_count(value: int) -> ConversionCount:
    """変換カウントを作成する

    Args:
        value: カウント値（非負整数）

    Returns:
        検証済みのConversionCount
    """
    validated = ConversionCountValidator.validate_python(value)
    return ConversionCount(validated)

# --- Literal型 ---

ConversionStatus = NewType('ConversionStatus', Literal['success', 'error', 'skipped'])
"""変換ステータス"""

ConversionStatusValidator = TypeAdapter(
    Annotated[Literal['success', 'error', 'skipped'], Field()]
)

def create_conversion_status(value: str) -> ConversionStatus:
    """変換ステータスを作成する

    Args:
        value: ステータス文字列（success/error/skipped）

    Returns:
        検証済みのConversionStatus
    """
    validated = ConversionStatusValidator.validate_python(value)
    return ConversionStatus(validated)
```

## 関連ガイド

- [Django風パッケージ構造ガイド](./django-style-structure.md)
- [既存モジュールの移行手順](./migration-guide.md)
- [型定義ルール](../typing-rule.md)

## 参考資料

- [PEP 484 – Type Hints](https://peps.python.org/pep-0484/)
- [PEP 695 – Type Parameter Syntax](https://peps.python.org/pep-0695/)
- [Pydantic TypeAdapter](https://docs.pydantic.dev/latest/concepts/type_adapter/)
