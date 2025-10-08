# 型定義検出ロジックのルール

このドキュメントは、pylayの型定義検出ロジック（`TypeClassifier`）がどのように動作するかを説明します。

## 目次

1. [概要](#概要)
2. [検出パターン](#検出パターン)
3. [分類ルール](#分類ルール)
4. [優先順位と重複除去](#優先順位と重複除去)
5. [エッジケース](#エッジケース)
6. [実装詳細](#実装詳細)

---

## 概要

`TypeClassifier`は、Pythonソースコードから型定義を抽出し、3つのレベル（Level 1/2/3）に分類します。

### 検出方法

2つの手法を併用します：

1. **AST解析** (`_classify_with_ast`)
   - 構文木を解析して型定義を抽出
   - ClassDef、TypeAlias、Assignノードを処理

2. **正規表現パターンマッチング** (`_classify_with_regex`)
   - テキストベースで型定義を検出
   - AST解析で取得できないパターンを補完

### 型レベル

| レベル | 説明 | 例 |
|--------|------|-----|
| Level 1 | type エイリアス（制約なし） | `type UserId = str` |
| Level 2 | NewType + ファクトリ関数（PEP 484準拠） | `UserId = NewType('UserId', str)` + `create_user_id()` |
| Level 3 | BaseModel（複雑なドメインモデル） | `class User(BaseModel): ...` |
| other | dataclass、TypedDict、その他のクラス | `@dataclass class Config: ...` |

---

## 検出パターン

### 1. Level 1: type エイリアス

#### パターン1-1: type文（Python 3.12+）

```python
type UserId = str
type Point = tuple[float, float]
```

**検出方法**: AST (`ast.TypeAlias`) + 正規表現

**正規表現**:
```python
LEVEL1_PATTERN = re.compile(r"^\s*type\s+(\w+)\s*=\s*(.+)$", re.MULTILINE)
```

**分類条件**:
- `ast.TypeAlias`ノードとして検出される
- または正規表現でマッチ（AST解析失敗時のフォールバック）

#### パターン1-2: NewType（ファクトリ関数なし）

```python
StatusCode = NewType('StatusCode', int)
```

**検出方法**: 正規表現 + ファクトリ関数チェック

**正規表現**:
```python
NEWTYPE_PATTERN = re.compile(
    r"^\s*(\w+)\s*=\s*NewType\(['\"](\w+)['\"]\s*,\s*(\w+)\)", re.MULTILINE
)
```

**分類条件**:
- `NewType`定義が検出される
- **かつ** 対応するファクトリ関数が存在しない
- 変数名と型名が一致する（例: `UserId = NewType('UserId', str)`）

---

### 2. Level 2: NewType + ファクトリ関数（PEP 484準拠）

#### パターン2-1: NewType + create_*ファクトリ関数

```python
UserId = NewType('UserId', str)

def create_user_id(value: str) -> UserId:
    if len(value) < 8:
        raise ValueError("UserId must be at least 8 characters")
    return UserId(value)
```

**検出方法**: 正規表現によるペアリング

**NewType定義の正規表現**:
```python
NEWTYPE_PATTERN = re.compile(
    r"^\s*(\w+)\s*=\s*NewType\(['\"](\w+)['\"]\s*,\s*(\w+)\)", re.MULTILINE
)
```

**ファクトリ関数の正規表現**:
```python
FACTORY_PATTERN = re.compile(
    r"^\s*def\s+(create_(\w+)|(\w+))\s*\([^)]*\)\s*->\s*(\w+):", re.MULTILINE
)
```

**分類条件**:
1. `NewType`定義が検出される
2. **かつ** `create_*` 関数が検出される
3. **かつ** 関数の返り値型がNewType名と一致する
4. 関数名のsnake_caseをPascalCaseに変換して型名と照合
   - 例: `create_user_id` → `UserId`

#### パターン2-2: NewType + @validate_callファクトリ関数

```python
Email = NewType('Email', str)

@validate_call
def Email(value: Annotated[str, Field(pattern=r'^[^@]+@[^@]+$')]) -> Email:
    return NewType('Email', str)(value)
```

**検出方法**: 正規表現によるペアリング

**@validate_call検出の正規表現**:
```python
VALIDATE_CALL_PATTERN = re.compile(
    r"@validate_call\s*\n\s*def\s+(\w+)\s*\(.*?\)\s*->\s*(\w+):",
    re.MULTILINE | re.DOTALL,
)
```

**分類条件**:
1. `NewType`定義が検出される
2. **かつ** `@validate_call`デコレータ付き関数が検出される
3. **かつ** 関数名と返り値型がNewType名と一致する
4. 関数パラメータは`.*?`で非貪欲マッチ（複雑なAnnotated型に対応）

**注意点**:
- `@validate_call`と`def`の間に改行が必要
- 同じ行にある場合（`@validate_call; def ...`）は検出されない

---

### 3. Level 3: BaseModel

```python
class User(BaseModel):
    id: UserId
    email: Email
    age: int
```

**検出方法**: AST (`ast.ClassDef`)

**分類条件**:
- `ast.ClassDef`ノードとして検出される
- **かつ** `BaseModel`を継承している
- `pydantic.BaseModel`または`BaseModel`をインポート

---

### 4. other: その他の型定義

#### パターン4-1: dataclass

```python
@dataclass
class Config:
    timeout: int
    retries: int
```

**検出方法**: AST (`ast.ClassDef` + デコレータチェック)

**分類条件**:
- `@dataclass`デコレータが付いている
- `dataclasses.dataclass`または`dataclass`をインポート

#### パターン4-2: TypedDict

```python
class UserDict(TypedDict):
    name: str
    age: int
```

**検出方法**: AST (`ast.ClassDef` + 基底クラスチェック)

**分類条件**:
- `TypedDict`を継承している
- `typing.TypedDict`または`TypedDict`をインポート

---

## 分類ルール

### ルール1: NewType定義の判定

#### AST解析での除外

`_classify_assign_alias`メソッドで、`ast.Assign`ノードがNewType呼び出しの場合はスキップします：

```python
# NewType定義はスキップ（_detect_newtype_with_factoryで処理）
if isinstance(node.value, ast.Call):
    if isinstance(node.value.func, ast.Name) and node.value.func.id == "NewType":
        return None
```

これにより、NewType定義がLevel 1として誤検出されることを防ぎます。

#### 正規表現での検出

`_detect_newtype_with_factory`メソッドで、以下の手順でNewType + ファクトリ関数をペアリングします：

1. **NewType定義を収集**
   ```python
   newtype_defs: dict[str, tuple[int, str, str]] = {}
   # {type_name: (line_number, definition, base_type)}
   ```

2. **ファクトリ関数を収集**
   ```python
   factory_funcs: dict[str, int] = {}
   # {type_name: line_number}
   ```

3. **ペアリング**
   - NewType名がfactory_funcsに存在 → **Level 2**
   - NewType名がfactory_funcsに存在しない → **Level 1**

### ルール2: 変数名と型名の一致

NewType定義で、変数名と型名が一致しない場合は検出しません：

```python
# ✅ 検出される
UserId = NewType('UserId', str)

# ❌ 検出されない（変数名と型名が不一致）
user_id_type = NewType('UserId', str)
```

**理由**: 慣習的に`UserId = NewType('UserId', ...)`パターンが推奨されるため。

### ルール3: snake_case → PascalCase変換

ファクトリ関数名（snake_case）を型名（PascalCase）に変換して照合します：

```python
# create_user_profile_id → UserProfileId
type_name = "".join(word.capitalize() for word in type_name_snake.split("_"))
```

**例**:
- `create_user_id` → `UserId` ✅
- `create_userid` → `Userid` (UserIdとは不一致) ❌
- `create_user_profile_id` → `UserProfileId` ✅

---

## 優先順位と重複除去

### 検出順序

1. **AST解析** (`_classify_with_ast`)
   - ClassDef（BaseModel、dataclass、TypedDict、その他）
   - TypeAlias（type文）
   - Assign（旧パターン、NewType定義はスキップ）

2. **正規表現** (`_classify_with_regex`)
   - NewType + ファクトリ関数（新パターン）
   - Level 2: Annotated + AfterValidator（旧パターン）
   - Level 1: type エイリアス（フォールバック）

### 重複除去

`classify_file`メソッドで、同じ名前・ファイル・行番号の型定義を除去します：

```python
seen = set()
unique_types = []
for td in type_definitions:
    key = (td.name, td.file_path, td.line_number)
    if key not in seen:
        seen.add(key)
        unique_types.append(td)
```

**注意**: 同じファイルで同じ名前の型定義が複数回検出された場合、最初に検出されたものが優先されます。

---

## エッジケース

### エッジケース1: 空ファイル

```python
# 空ファイル
```

**動作**: 空のリストを返す（エラーにならない）

### エッジケース2: 構文エラー

```python
UserId = NewType('UserId' str)  # カンマ忘れ
```

**動作**:
- AST解析は失敗（SyntaxError）
- 正規表現でのマッチも失敗
- 空のリストを返す（エラーにならない）

### エッジケース3: インポートなし

```python
# NewTypeのインポートなし
UserId = NewType('UserId', str)
```

**動作**:
- 正規表現パターンマッチングで検出される
- インポートの有無は検証しない

### エッジケース4: 同じ型に対して複数のファクトリ関数

```python
UserId = NewType('UserId', str)

def create_user_id(value: str) -> UserId:
    return UserId(value)

def create_user_id_from_int(value: int) -> UserId:
    return UserId(str(value))
```

**動作**:
- UserIdは1回のみ検出される（重複除去）
- 最初に検出されたファクトリ関数とペアリング
- Level 2として分類

### エッジケース5: ファクトリ関数のみ（NewTypeなし）

```python
def create_user_id(value: str) -> str:
    return value
```

**動作**:
- ファクトリ関数として検出されない（返り値型がstrのため）
- 型定義として検出されない

### エッジケース6: クラス内NewType

```python
class UserModule:
    UserId = NewType('UserId', str)

    @staticmethod
    def create_user_id(value: str) -> UserId:
        return UserModule.UserId(value)
```

**動作**:
- 現在の実装ではクラス内NewTypeは検出されない
- モジュールレベルの定義のみを対象

**理由**: 正規表現パターンが行頭（`^\s*`）からマッチするため、インデントされたクラス内定義は検出されない

### エッジケース7: Unicode文字を含む型名

```python
ユーザーID = NewType('ユーザーID', str)
```

**動作**:
- 正規表現パターン（`\w`）ではUnicodeはマッチしない可能性
- Python 3.13のデフォルト動作に依存

### エッジケース8: ジェネリック型をベースとするNewType

```python
UserList = NewType('UserList', list[str])
```

**動作**:
- 正規表現パターンが単純な型名（`\w+`）のみをマッチ
- `list[str]`は`\w+`にマッチしないため検出されない

### エッジケース9: 同じ行にコメント

```python
UserId = NewType('UserId', str)  # ユーザー識別子

def create_user_id(value: str) -> UserId:  # ファクトリ関数
    return UserId(value)
```

**動作**:
- 正常に検出される（コメントは無視される）

### エッジケース10: @validate_callとdefが同じ行

```python
@validate_call; def Email(value: str) -> Email: return Email(value)
```

**動作**:
- `VALIDATE_CALL_PATTERN`は改行（`\n`）を期待するためマッチしない
- EmailはLevel 1として検出される

### エッジケース11: 複数ファイルの独立性

```python
# file1.py
UserId = NewType('UserId', str)
def create_user_id(value: str) -> UserId: ...

# file2.py
Email = NewType('Email', str)
```

**動作**:
- file1.pyのUserIdはLevel 2
- file2.pyのEmailはLevel 1
- ファイル間で状態は共有されない（独立）

### エッジケース12: type: ignoreコメント

```python
Email = NewType('Email', str)

@validate_call
def Email(value: Annotated[str, Field(...)]) -> Email:  # type: ignore[no-redef]
    return NewType('Email', str)(value)  # type: ignore[misc]
```

**動作**:
- 正常に検出される（type: ignoreコメントは無視される）

### エッジケース13: 大文字小文字の不一致

```python
UserId = NewType('UserId', str)

# create_userid → Userid (UserIdと不一致)
def create_userid(value: str) -> UserId:
    return UserId(value)
```

**動作**:
- snake_case → PascalCase変換で`Userid`になる
- `Userid != UserId`のため、ペアリング失敗
- UserIdはLevel 1として検出される

---

## 実装詳細

### 主要クラス

```python
class TypeClassifier:
    """型定義を分類するクラス"""

    def classify_file(self, file_path: Path) -> list[TypeDefinition]:
        """ファイル内の型定義を検出・分類"""

    def _classify_with_ast(self, tree: ast.AST, ...) -> list[TypeDefinition]:
        """AST解析による分類"""

    def _classify_with_regex(self, source_code: str, ...) -> list[TypeDefinition]:
        """正規表現による分類"""

    def _detect_newtype_with_factory(self, source_code: str, ...) -> list[TypeDefinition]:
        """NewType + ファクトリ関数パターンを検出"""
```

### 正規表現パターン

```python
# Level 1: type エイリアス
LEVEL1_PATTERN = re.compile(r"^\s*type\s+(\w+)\s*=\s*(.+)$", re.MULTILINE)

# Level 2: Annotated + AfterValidator（旧パターン）
LEVEL2_PATTERN = re.compile(
    r"^\s*type\s+(\w+)\s*=\s*Annotated\[.*AfterValidator.*\]", re.MULTILINE
)

# NewType定義
NEWTYPE_PATTERN = re.compile(
    r"^\s*(\w+)\s*=\s*NewType\(['\"](\w+)['\"]\s*,\s*(\w+)\)", re.MULTILINE
)

# ファクトリ関数パターン
FACTORY_PATTERN = re.compile(
    r"^\s*def\s+(create_(\w+)|(\w+))\s*\([^)]*\)\s*->\s*(\w+):", re.MULTILINE
)

# @validate_call デコレータ + 関数定義（改行を許容、パラメータは.*?で非貪欲マッチ）
VALIDATE_CALL_PATTERN = re.compile(
    r"@validate_call\s*\n\s*def\s+(\w+)\s*\(.*?\)\s*->\s*(\w+):",
    re.MULTILINE | re.DOTALL,
)

# Level 3: BaseModel
LEVEL3_PATTERN = re.compile(r"^\s*class\s+(\w+)\(.*BaseModel.*\):", re.MULTILINE)

# その他のクラス
OTHER_CLASS_PATTERN = re.compile(
    r"^\s*class\s+(\w+)(?:\((?!.*BaseModel).*\))?:", re.MULTILINE
)
```

### TypeDefinitionモデル

```python
@dataclass
class TypeDefinition:
    """型定義の情報"""
    name: str                    # 型名
    level: str                   # Level (level1/level2/level3/other)
    file_path: str               # ファイルパス
    line_number: int             # 行番号
    definition: str              # 定義コード
    category: str                # カテゴリ (type_alias/newtype_with_factory/basemodel等)
    docstring: str | None        # docstring
    has_docstring: bool          # docstringの有無
    docstring_lines: int         # docstring行数
    target_level: str | None     # @target-level指定
    keep_as_is: bool             # @keep-as-is指定
```

### カテゴリ一覧

| カテゴリ | 説明 | レベル |
|---------|------|--------|
| `type_alias` | type文による型エイリアス | Level 1 |
| `newtype_plain` | NewType（ファクトリ関数なし） | Level 1 |
| `newtype_with_factory` | NewType + ファクトリ関数 | Level 2 |
| `annotated` | Annotated + AfterValidator（旧パターン） | Level 2 |
| `basemodel` | BaseModelクラス | Level 3 |
| `dataclass` | dataclassクラス | other |
| `typeddict` | TypedDictクラス | other |
| `class` | その他のクラス | other |

---

## 関連ドキュメント

- [docs/typing-rule.md](typing-rule.md) - 型定義ルール（Level 1/2/3の詳細）
- [MIGRATION_PLAN.md](../MIGRATION_PLAN.md) - PEP 484準拠パターンへの移行計画
- [AGENTS.md](../AGENTS.md) - 開発ガイドライン

---

## 変更履歴

| 日付 | バージョン | 変更内容 |
|------|-----------|---------|
| 2025-01-XX | 1.0.0 | 初版作成（NewType + ファクトリ関数パターン対応） |
