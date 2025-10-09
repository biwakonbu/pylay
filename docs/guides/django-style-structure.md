# Django風パッケージ構造ガイド

pylayプロジェクトでは、Djangoのアプリケーション構造に倣った「Django風パッケージ構造」を採用しています。各モジュールが独立したパッケージとして完結し、型定義、プロトコル、モデル、実装が明確に分離されています。

## 目次

- [基本原則](#基本原則)
- [4ファイル構造](#4ファイル構造)
- [依存関係の方向](#依存関係の方向)
- [実装例](#実装例)
- [ベストプラクティス](#ベストプラクティス)
- [移行ガイド](#移行ガイド)

## 基本原則

### 1. モジュールの独立性

各モジュール（`converters/`, `analyzer/`, `doc_generators/`等）は、独立したパッケージとして完結します。

```text
src/core/
├── converters/          # 型変換モジュール（独立パッケージ）
│   ├── types.py        # モジュール固有の型定義
│   ├── protocols.py    # Protocolインターフェース定義
│   ├── models.py       # Pydanticモデル（Level 3）
│   └── *.py            # ビジネスロジック実装
├── analyzer/           # 型解析モジュール（独立パッケージ）
│   ├── types.py
│   ├── protocols.py
│   ├── models.py
│   └── *.py
└── schemas/            # 共通型定義（複数モジュールで共有）
    ├── types.py        # 共通ドメイン型
    ├── graph.py        # グラフ型定義
    └── *.py
```

### 2. 型定義の階層化

各モジュールは、以下の4ファイル構造を目指します（**types.py優先**）:

1. **types.py**: モジュール固有の型定義（Level 1/2を優先）
2. **protocols.py**: Protocolインターフェース定義（抽象）
3. **models.py**: Pydanticモデル（Level 3: BaseModel）
4. **実装ファイル**: ビジネスロジック実装

### 3. schemas/の役割

`src/core/schemas/` は**複数モジュールで共有される共通型のみ**を配置します。

- ✅ 複数モジュールで使用される型（例: `TypeLevel`, `FilePath`）
- ❌ 特定モジュール専用の型（各モジュールの `types.py` に配置）

## 4ファイル構造

### types.py

**目的**: モジュール固有の型定義（Level 1/2を優先）

**配置する型**:

- Level 1: `type` エイリアス（制約なし）
- Level 2: `NewType` + ファクトリ関数 + `TypeAdapter`（★プリミティブ型代替、最頻出）
- 簡単なドメイン型（`Annotated`を使った制約付き型）

**例** (`src/core/converters/types.py`):

```python
"""converters モジュールの型定義"""

from typing import NewType, Annotated
from pathlib import Path
from pydantic import Field, TypeAdapter, validate_call

# Level 1: 型エイリアス
type Timestamp = float

# Level 2: NewType + ファクトリ関数（★最頻出パターン）
SourcePath = NewType('SourcePath', Path)
SourcePathValidator = TypeAdapter(Annotated[Path, Field()])

def create_source_path(value: Path | str) -> SourcePath:
    """ソースパスを作成する"""
    validated = SourcePathValidator.validate_python(value)
    return SourcePath(validated)

# または @validate_call パターン
ConversionCount = NewType('ConversionCount', int)

@validate_call
def create_conversion_count(
    value: Annotated[int, Field(ge=0)]
) -> ConversionCount:
    """変換回数を作成する"""
    return ConversionCount(value)
```

### protocols.py

**目的**: Protocolインターフェース定義（抽象）

**配置する型**:

- `Protocol` クラス（構造的部分型）
- `ABC` 抽象基底クラス（必要に応じて）

**例** (`src/core/converters/protocols.py`):

```python
"""converters モジュールのプロトコル定義"""

from typing import Protocol
from pathlib import Path

from .types import SourcePath

class TypeConverter(Protocol):
    """型変換器のプロトコル"""

    def convert(self, source: SourcePath) -> str:
        """型をYAML文字列に変換する"""
        ...

    def validate(self, source: SourcePath) -> bool:
        """変換可能かチェックする"""
        ...
```

### models.py

**目的**: Pydanticモデル（Level 3: BaseModel）

**配置する型**:

- Level 3: `dataclass` + Pydantic または `BaseModel`（複雑なドメイン型）
- ビジネスロジックを持つモデル

**例** (`src/core/converters/models.py`):

```python
"""converters モジュールのドメインモデル"""

from pydantic import BaseModel, Field
from pathlib import Path

from .types import SourcePath, ConversionCount

class ConversionResult(BaseModel):
    """型変換結果"""

    source: SourcePath
    yaml_output: str
    types_count: ConversionCount
    errors: list[str] = Field(default_factory=list)

    def is_success(self) -> bool:
        """変換が成功したかチェック"""
        return len(self.errors) == 0

    def get_summary(self) -> str:
        """結果サマリーを取得"""
        return f"{self.types_count} types from {self.source}"
```

### 実装ファイル

**目的**: ビジネスロジック実装

**例** (`src/core/converters/type_to_yaml.py`):

```python
"""型からYAMLへの変換実装"""

from pathlib import Path
from .types import (
    SourcePath,
    create_source_path,
    ConversionCount,
    create_conversion_count,
)
from .protocols import TypeConverter
from .models import ConversionResult

class TypeToYamlConverter:
    """型をYAMLに変換するクラス"""

    def convert(self, source: str | Path) -> ConversionResult:
        """型をYAMLに変換する"""
        # SourcePath型に変換
        source_path = create_source_path(Path(source))

        # 変換処理...
        yaml_output = "..."
        types_count = create_conversion_count(10)

        return ConversionResult(
            source=source_path,
            yaml_output=yaml_output,
            types_count=types_count,
        )
```

## 依存関係の方向

依存関係は以下の方向に制限されます:

```text
実装ファイル
    ↓ import
models.py
    ↓ import
types.py

実装ファイル
    ↓ import
protocols.py
```

**禁止パターン**:

- ❌ `types.py` → `models.py` のimport
- ❌ `protocols.py` → `models.py` のimport
- ❌ 循環import

**理由**: 型定義（types.py）は最も基本的な層であり、他の層に依存してはいけません。

## 実装例

### 完全な例: `converters/` モジュール

**types.py**:

```python
"""converters モジュールの型定義"""

from typing import NewType, Annotated
from pathlib import Path
from pydantic import Field, TypeAdapter, validate_call

# Level 1: 型エイリアス
type YamlString = str
type Timestamp = float

# Level 2: NewType + ファクトリ関数
SourcePath = NewType('SourcePath', Path)
SourcePathValidator = TypeAdapter(Annotated[Path, Field()])

def create_source_path(value: Path | str) -> SourcePath:
    validated = SourcePathValidator.validate_python(value)
    return SourcePath(validated)

OutputPath = NewType('OutputPath', Path)

@validate_call
def OutputPath(value: Annotated[Path, Field()]) -> OutputPath:  # type: ignore[no-redef]
    return NewType('OutputPath', Path)(value)

ConversionCount = NewType('ConversionCount', int)

@validate_call
def create_conversion_count(
    value: Annotated[int, Field(ge=0)]
) -> ConversionCount:
    return ConversionCount(value)
```

**protocols.py**:

```python
"""converters モジュールのプロトコル定義"""

from typing import Protocol
from .types import SourcePath, YamlString

class TypeConverter(Protocol):
    """型変換器のプロトコル"""

    def convert(self, source: SourcePath) -> YamlString:
        ...

    def validate(self, source: SourcePath) -> bool:
        ...

class YamlFormatter(Protocol):
    """YAML整形器のプロトコル"""

    def format(self, yaml: YamlString) -> YamlString:
        ...
```

**models.py**:

```python
"""converters モジュールのドメインモデル"""

from pydantic import BaseModel, Field
from .types import SourcePath, OutputPath, YamlString, ConversionCount, Timestamp

class ConversionResult(BaseModel):
    """型変換結果"""

    source: SourcePath
    output: OutputPath | None = None
    yaml_content: YamlString
    types_count: ConversionCount
    timestamp: Timestamp
    errors: list[str] = Field(default_factory=list)

    def is_success(self) -> bool:
        return len(self.errors) == 0

    def get_summary(self) -> str:
        return f"{self.types_count} types from {self.source}"

class ConversionOptions(BaseModel):
    """変換オプション"""

    include_metadata: bool = True
    root_key: str | None = None
    validate_output: bool = True
```

**type_to_yaml.py** (実装):

```python
"""型からYAMLへの変換実装"""

from pathlib import Path
import time
from .types import (
    SourcePath,
    OutputPath,
    YamlString,
    create_source_path,
    ConversionCount,
    create_conversion_count,
)
from .protocols import TypeConverter
from .models import ConversionResult, ConversionOptions

class TypeToYamlConverter:
    """型をYAMLに変換するクラス"""

    def __init__(self, options: ConversionOptions | None = None):
        self.options = options or ConversionOptions()

    def convert(self, source: str | Path, output: str | Path | None = None) -> ConversionResult:
        """型をYAMLに変換する"""
        # 型変換
        source_path = create_source_path(Path(source))
        output_path = OutputPath(Path(output)) if output else None

        # 変換処理...
        yaml_content = self._extract_types(source_path)
        types_count = self._count_types(yaml_content)

        return ConversionResult(
            source=source_path,
            output=output_path,
            yaml_content=yaml_content,
            types_count=types_count,
            timestamp=time.time(),
        )

    def _extract_types(self, source: SourcePath) -> YamlString:
        """型情報を抽出してYAMLに変換"""
        # 実装...
        return "types:\n  User:\n    ..."

    def _count_types(self, yaml: YamlString) -> ConversionCount:
        """型の数をカウント"""
        # 実装...
        return create_conversion_count(10)
```

## ベストプラクティス

### 1. types.pyを優先する

新しい型定義を追加する際は、まず `types.py` への配置を検討します。

**判断基準**:

- プリミティブ型の代替 → `types.py` (Level 2: NewType)
- 簡単なドメイン型 → `types.py` (Level 2: Annotated)
- 複雑なドメイン型 → `models.py` (Level 3: BaseModel)

### 2. 共有型は schemas/ へ

複数モジュールで使用される型は `src/core/schemas/` に配置します。

```python
# src/core/schemas/types.py
from typing import NewType
from pydantic import TypeAdapter, Field, Annotated

# 共通型定義
FilePath = NewType('FilePath', str)
FilePathValidator = TypeAdapter(Annotated[str, Field(min_length=1)])

def create_file_path(value: str) -> FilePath:
    validated = FilePathValidator.validate_python(value)
    return FilePath(validated)
```

### 3. 循環importを避ける

**禁止**:

```python
# types.py
from .models import SomeModel  # ❌

# models.py
from .types import SomeType  # ✅ これは許可
```

**解決策**: 型ヒントに文字列を使用（forward reference）

```python
# types.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import SomeModel

def process(model: "SomeModel") -> None:
    ...
```

### 4. Level 1は一時的な状態

Level 1（単純な型エイリアス）は一時的な状態であり、適切な制約（Level 2）やビジネスロジック（Level 3）への昇格を検討してください。

```python
# 一時的 (Level 1)
type UserId = str

# 推奨 (Level 2)
UserId = NewType('UserId', str)
UserIdValidator = TypeAdapter(Annotated[str, Field(min_length=8)])

def create_user_id(value: str) -> UserId:
    validated = UserIdValidator.validate_python(value)
    return UserId(validated)
```

### 5. docstringで設計意図を明記

型定義にdocstringを追加し、設計意図を明記します。

```python
SourcePath = NewType('SourcePath', Path)
"""
ソースファイルのパス

**設計意図**:
- 入力ファイルパスとして使用
- 存在チェックはファクトリ関数で実施
- 相対パス/絶対パスの両方をサポート

**使用例**:
    source = create_source_path(Path("src/core/types.py"))
"""
```

## 移行ガイド

既存モジュールをDjango風構造に移行する手順については、[既存モジュールの移行手順](./migration-guide.md) を参照してください。

## 関連ガイド

- [types.py作成ガイドライン](./types-creation-guide.md)
- [既存モジュールの移行手順](./migration-guide.md)
- [型定義ルール](../typing-rule.md)

## Protocolの詳細と利用シーン

### Protocolの役割

**protocols.py** で定義されるProtocolは、構造的部分型（Structural Subtyping）を実現するための抽象インターフェースです。Pythonの型システムにおいて、以下の重要な役割を果たします：

1. **型チェックのための抽象インターフェース定義**
   - 実装クラスとの疎結合を実現
   - 明示的な継承なしに型互換性を提供

2. **循環参照の回避**
   - types.py → protocols.py の一方向依存を維持
   - models.py や実装ファイルへの依存を排除

3. **テスト可能性の向上**
   - モックやスタブの作成が容易
   - 依存性注入（DI）パターンの実装を支援

### 具体的な利用シーン

#### シーン1: 型変換器の抽象化

```python
# protocols.py
from typing import Protocol
from .types import SourcePath, YamlString

class TypeConverter(Protocol):
    """型変換器のプロトコル

    複数の変換実装（AST変換、mypy変換等）を
    統一的に扱うためのインターフェース
    """

    def convert(self, source: SourcePath) -> YamlString:
        """型をYAML文字列に変換する"""
        ...

    def validate(self, source: SourcePath) -> bool:
        """変換可能かチェックする"""
        ...

# 実装例1: AST変換器
class AstTypeConverter:
    def convert(self, source: SourcePath) -> YamlString:
        # AST解析による変換
        ...

    def validate(self, source: SourcePath) -> bool:
        # ASTで解析可能かチェック
        ...

# 実装例2: mypy変換器
class MypyTypeConverter:
    def convert(self, source: SourcePath) -> YamlString:
        # mypy型推論による変換
        ...

    def validate(self, source: SourcePath) -> bool:
        # mypy解析可能かチェック
        ...

# 利用側: どちらの実装でも同じインターフェースで使用可能
def process_file(converter: TypeConverter, source: SourcePath) -> YamlString:
    if not converter.validate(source):
        raise ValueError(f"Cannot convert {source}")
    return converter.convert(source)
```

#### シーン2: 依存性注入とテスト

```python
# protocols.py
from typing import Protocol
from .types import UserId

class UserRepository(Protocol):
    """ユーザーリポジトリのプロトコル"""

    def find_by_id(self, user_id: UserId) -> dict | None:
        """ユーザーIDでユーザーを検索"""
        ...

# 本番実装
class SqlAlchemyUserRepository:
    def find_by_id(self, user_id: UserId) -> dict | None:
        # データベースアクセス
        ...

# テスト用モック
class InMemoryUserRepository:
    def __init__(self):
        self.users: dict[UserId, dict] = {}

    def find_by_id(self, user_id: UserId) -> dict | None:
        return self.users.get(user_id)

# サービス層: Protocolに依存
class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo  # 実装に依存せず、Protocolに依存

    def get_user(self, user_id: UserId) -> dict:
        user = self.repo.find_by_id(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")
        return user

# テスト時は InMemoryUserRepository を注入
# 本番時は SqlAlchemyUserRepository を注入
```

### モジュール間の依存関係図

```text
┌─────────────────────────────────────────────────┐
│                  実装ファイル                      │
│             (type_to_yaml.py等)                 │
│                                                 │
│  - ビジネスロジック実装                           │
│  - Protocolインターフェースを実装                 │
│  - models.py と types.py を使用                  │
└────────────┬────────────────────────┬──────────┘
             │                        │
             │ import                 │ import
             ↓                        ↓
    ┌─────────────┐          ┌─────────────┐
    │ models.py   │          │protocols.py │
    │             │          │             │
    │ Level 3型   │          │ Protocol    │
    │ BaseModel   │          │ 定義        │
    └──────┬──────┘          └──────┬──────┘
           │                        │
           │ import                 │ import
           ↓                        ↓
    ┌──────────────────────────────────┐
    │           types.py               │
    │                                  │
    │  Level 1/2型定義                 │
    │  (NewType, Annotated等)          │
    └──────────────────────────────────┘
```

**依存方向のルール**:

- ✅ 実装 → protocols.py（Protocolの実装）
- ✅ 実装 → models.py（ドメインモデルの使用）
- ✅ 実装 → types.py（基本型の使用）
- ✅ models.py → types.py（基本型の使用）
- ✅ protocols.py → types.py（基本型の使用）
- ❌ types.py → models.py（禁止）
- ❌ types.py → protocols.py（禁止）
- ❌ protocols.py → models.py（禁止）

### Protocolのベストプラクティス

1. **メソッド定義は最小限に**
   - 必要なメソッドのみを定義
   - 単一責任原則（SRP）を遵守

2. **型ヒントは厳格に**
   - 引数と戻り値に明確な型を指定
   - types.py の型を積極的に使用

3. **docstringで契約を明示**
   - メソッドの責務と期待動作を記述
   - 例外の可能性を明記

4. **実装の強制はしない**
   - Protocolは構造的部分型
   - 明示的な継承は不要（但し推奨）

## 参考資料

- [PEP 484 – Type Hints](https://peps.python.org/pep-0484/)
- [PEP 544 – Protocols](https://peps.python.org/pep-0544/)
- [PEP 695 – Type Parameter Syntax](https://peps.python.org/pep-0695/)
- [Pydantic ドキュメント](https://docs.pydantic.dev/)
