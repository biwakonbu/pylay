# 既存モジュールの移行手順

このガイドでは、既存のモジュールをDjango風パッケージ構造に移行する手順を説明します。

## 目次

- [移行の目的](#移行の目的)
- [移行前の確認](#移行前の確認)
- [移行手順](#移行手順)
- [段階的移行戦略](#段階的移行戦略)
- [トラブルシューティング](#トラブルシューティング)
- [移行例](#移行例)

## 移行の目的

既存モジュールをDjango風パッケージ構造に移行することで、以下のメリットが得られます:

1. **型定義の明確化**: types.py による型定義の一元管理
2. **依存関係の可視化**: protocols.py によるインターフェースの明示
3. **保守性の向上**: models.py によるドメインモデルの分離
4. **型安全性の向上**: プリミティブ型の直接使用を避ける

## 移行前の確認

移行を開始する前に、以下の項目を確認してください:

### チェックリスト

- [ ] モジュールの責務を理解している
- [ ] 現在の型定義を把握している
- [ ] プリミティブ型の使用箇所を特定している
- [ ] テストが整備されている（移行後の動作確認用）
- [ ] チームメンバーに移行を周知している

### 準備

```bash
# 1. 現在のブランチをバックアップ
git checkout -b backup/before-migration

# 2. 新しい作業ブランチを作成
git checkout -b feature/migrate-module-name

# 3. テストが通ることを確認
uv run pytest tests/

# 4. 型チェックが通ることを確認
uv run mypy src/
```

## 移行手順

### Phase 1: types.py の作成

#### Step 1.1: プリミティブ型の使用箇所を特定

```bash
# モジュール内のプリミティブ型使用箇所を検索
grep -rn "def.*str\|def.*int\|def.*float" src/core/your_module/

# 型アノテーションを確認
grep -rn ": str\|: int\|: float" src/core/your_module/
```

#### Step 1.2: types.py を作成

```python
# src/core/your_module/types.py
"""your_module モジュールの型定義"""

from typing import NewType, Annotated
from pydantic import Field, TypeAdapter

# プリミティブ型を置き換える型定義を追加
# 例: str → FilePath
FilePath = NewType('FilePath', str)
FilePathValidator = TypeAdapter(Annotated[str, Field(min_length=1)])

def create_file_path(value: str) -> FilePath:
    """ファイルパスを作成する"""
    validated = FilePathValidator.validate_python(value)
    return FilePath(validated)

# 例: int → Count
Count = NewType('Count', int)
CountValidator = TypeAdapter(Annotated[int, Field(ge=0)])

def create_count(value: int) -> Count:
    """カウントを作成する"""
    validated = CountValidator.validate_python(value)
    return Count(validated)
```

#### Step 1.3: 既存コードを段階的に更新

```python
# Before (プリミティブ型を直接使用)
def process_file(file_path: str, count: int) -> dict:
    ...

# After (ドメイン型を使用)
from .types import FilePath, Count

def process_file(file_path: FilePath, count: Count) -> dict:
    ...
```

### Phase 2: protocols.py の作成（オプション）

#### Step 2.1: インターフェースの抽出

既存のクラスから共通インターフェースを抽出します。

```python
# src/core/your_module/protocols.py
"""your_module モジュールのプロトコル定義"""

from typing import Protocol
from .types import FilePath, Count

class FileProcessor(Protocol):
    """ファイル処理のプロトコル"""

    def process(self, file_path: FilePath) -> Count:
        """ファイルを処理する"""
        ...

    def validate(self, file_path: FilePath) -> bool:
        """処理可能かチェックする"""
        ...
```

#### Step 2.2: 既存クラスをプロトコルに準拠させる

```python
# Before
class MyProcessor:
    def process(self, file_path: str) -> int:
        ...

# After
from .protocols import FileProcessor
from .types import FilePath, Count, create_file_path, create_count

class MyProcessor:
    """FileProcessorプロトコルに準拠"""

    def process(self, file_path: FilePath) -> Count:
        ...

    def validate(self, file_path: FilePath) -> bool:
        ...
```

### Phase 3: models.py の作成（必要に応じて）

#### Step 3.1: 複雑なドメインモデルの抽出

複雑なビジネスロジックを持つクラスを `models.py` に移動します。

```python
# src/core/your_module/models.py
"""your_module モジュールのドメインモデル"""

from pydantic import BaseModel, Field
from .types import FilePath, Count

class ProcessingResult(BaseModel):
    """処理結果"""

    source: FilePath
    processed_count: Count
    errors: list[str] = Field(default_factory=list)

    def is_success(self) -> bool:
        """処理が成功したかチェック"""
        return len(self.errors) == 0

    def get_summary(self) -> str:
        """結果サマリーを取得"""
        return f"Processed {self.processed_count} items from {self.source}"
```

#### Step 3.2: 既存コードを更新

```python
# Before
def process_file(file_path: str) -> dict:
    return {
        "source": file_path,
        "count": 10,
        "errors": [],
    }

# After
from .types import create_file_path
from .models import ProcessingResult

def process_file(file_path: str) -> ProcessingResult:
    source_path = create_file_path(file_path)
    count = create_count(10)
    return ProcessingResult(
        source=source_path,
        processed_count=count,
    )
```

### Phase 4: テストの更新

#### Step 4.1: 型定義のテストを追加

```python
# tests/core/your_module/test_types.py
import pytest
from src.core.your_module.types import create_file_path, create_count

def test_create_file_path_valid():
    """有効なファイルパスの作成"""
    path = create_file_path("/path/to/file.py")
    assert path == "/path/to/file.py"

def test_create_file_path_invalid():
    """無効なファイルパス（空文字列）"""
    with pytest.raises(ValueError):
        create_file_path("")

def test_create_count_valid():
    """有効なカウントの作成"""
    count = create_count(10)
    assert count == 10

def test_create_count_invalid():
    """無効なカウント（負数）"""
    with pytest.raises(ValueError):
        create_count(-1)
```

#### Step 4.2: 既存テストの更新

```python
# Before
def test_process_file():
    result = process_file("/path/to/file.py", 10)
    assert result["count"] == 10

# After
from src.core.your_module.types import create_file_path, create_count

def test_process_file():
    file_path = create_file_path("/path/to/file.py")
    count = create_count(10)
    result = process_file(file_path, count)
    assert result.processed_count == 10
```

### Phase 5: ドキュメントの更新

#### Step 5.1: モジュールREADME.mdの作成

```markdown
# your_module モジュール

## 概要

このモジュールは、○○機能を提供します。

## 構造

- `types.py`: モジュール固有の型定義（Level 1/2）
- `protocols.py`: Protocolインターフェース定義
- `models.py`: Pydanticモデル（Level 3）
- `*.py`: ビジネスロジック実装

## 使用例

```python
from .types import create_file_path, create_count
from .models import ProcessingResult

# ファイルパスの作成
file_path = create_file_path("/path/to/file.py")

# 処理の実行
result = process_file(file_path)

# 結果の確認
if result.is_success():
    print(result.get_summary())
```

## 依存関係

- `src.core.schemas.types`: 共通型定義
- `pydantic`: バリデーション
```



#### Step 5.2: AGENTS.mdの更新

プロジェクトのAGENTS.mdに移行完了を記載します。

## 段階的移行戦略

一度にすべてを移行するのではなく、以下の戦略で段階的に移行します:

### 戦略1: 新規コードから適用

```python
# 既存コード（そのまま）
def old_function(path: str) -> int:
    ...

# 新規コード（新構造を適用）
from .types import create_file_path, create_count

def new_function(path: FilePath) -> Count:
    ...
```

### 戦略2: ファイル単位で移行

```text
Phase 1: types.py 作成
    ↓
Phase 2: file_a.py を更新（新しい型を使用）
    ↓
Phase 3: file_b.py を更新
    ↓
Phase 4: file_c.py を更新
    ↓
Phase 5: protocols.py, models.py 作成
```

### 戦略3: 型レベルごとに移行

```text
Step 1: Level 1型の定義（type エイリアス）
    ↓
Step 2: Level 2型への昇格（NewType + ファクトリ）
    ↓
Step 3: Level 3型の抽出（BaseModel）
```

## トラブルシューティング

### 問題1: 循環import

**症状**:

```text
ImportError: cannot import name 'SomeType' from partially initialized module
```

**原因**:

types.py → models.py → types.py の循環import

**解決策**:

```python
# types.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import SomeModel

def process(model: "SomeModel") -> None:
    ...
```

### 問題2: 型チェックエラー

**症状**:

```text
error: Argument 1 has incompatible type "str"; expected "FilePath"
```

**原因**:

既存コードがプリミティブ型を使用している

**解決策**:

```python
# Before
result = process_file("/path/to/file")  # str

# After
from .types import create_file_path

result = process_file(create_file_path("/path/to/file"))  # FilePath
```

### 問題3: テスト失敗

**症状**:

```text
ValidationError: value is not a valid integer
```

**原因**:

ファクトリ関数のバリデーションが厳しすぎる

**解決策**:

```python
# Before（厳しすぎる）
CountValidator = TypeAdapter(Annotated[int, Field(gt=0, lt=100)])

# After（適切な制約）
CountValidator = TypeAdapter(Annotated[int, Field(ge=0)])
```

### 問題4: パフォーマンス低下

**症状**:

バリデーションにより処理速度が低下

**解決策**:

```python
# パフォーマンスクリティカルな箇所では、バリデーションをスキップ
from typing import cast

def fast_process(path: str) -> None:
    # すでに検証済みの場合
    file_path = cast(FilePath, path)
    ...
```

## 移行例

### 例1: converters モジュールの移行

#### 移行前

```python
# src/core/converters/type_to_yaml.py
def convert_to_yaml(source: str, output: str) -> dict:
    """型をYAMLに変換する"""
    # 実装...
    return {
        "source": source,
        "output": output,
        "count": 10,
    }
```

#### 移行後

**types.py**:

```python
# src/core/converters/types.py
from typing import NewType, Annotated
from pathlib import Path
from pydantic import Field, TypeAdapter

SourcePath = NewType('SourcePath', Path)
SourcePathValidator = TypeAdapter(Annotated[Path, Field()])

def create_source_path(value: Path | str) -> SourcePath:
    if isinstance(value, str):
        value = Path(value)
    validated = SourcePathValidator.validate_python(value)
    return SourcePath(validated)

OutputPath = NewType('OutputPath', Path)

# ... (同様にOutputPathを定義)

ConversionCount = NewType('ConversionCount', int)

# ... (同様にConversionCountを定義)
```

**models.py**:

```python
# src/core/converters/models.py
from pydantic import BaseModel
from .types import SourcePath, OutputPath, ConversionCount

class ConversionResult(BaseModel):
    """変換結果"""

    source: SourcePath
    output: OutputPath
    count: ConversionCount

    def is_success(self) -> bool:
        return self.count > 0
```

**type_to_yaml.py**:

```python
# src/core/converters/type_to_yaml.py
from pathlib import Path
from .types import create_source_path, create_output_path, create_conversion_count
from .models import ConversionResult

def convert_to_yaml(source: str | Path, output: str | Path) -> ConversionResult:
    """型をYAMLに変換する"""
    source_path = create_source_path(source)
    output_path = create_output_path(output)

    # 実装...
    count = create_conversion_count(10)

    return ConversionResult(
        source=source_path,
        output=output_path,
        count=count,
    )
```

### 例2: analyzer モジュールの移行

#### 移行前

```python
# src/core/analyzer/type_inferrer.py
class TypeInferrer:
    def infer(self, code: str) -> list[dict]:
        """型を推論する"""
        return [
            {"name": "User", "level": "level2"},
            {"name": "Post", "level": "level3"},
        ]
```

#### 移行後

**types.py**:

```python
# src/core/analyzer/types.py
from typing import NewType, Literal, Annotated
from pydantic import Field, TypeAdapter

TypeLevel = NewType('TypeLevel', Literal['level1', 'level2', 'level3'])
TypeLevelValidator = TypeAdapter(
    Annotated[Literal['level1', 'level2', 'level3'], Field()]
)

def create_type_level(value: str) -> TypeLevel:
    validated = TypeLevelValidator.validate_python(value)
    return TypeLevel(validated)

TypeName = NewType('TypeName', str)
TypeNameValidator = TypeAdapter(Annotated[str, Field(min_length=1)])

def create_type_name(value: str) -> TypeName:
    validated = TypeNameValidator.validate_python(value)
    return TypeName(validated)
```

**models.py**:

```python
# src/core/analyzer/models.py
from pydantic import BaseModel
from .types import TypeName, TypeLevel

class InferredType(BaseModel):
    """推論された型情報"""

    name: TypeName
    level: TypeLevel

    def is_high_level(self) -> bool:
        """Level 3かチェック"""
        return self.level == "level3"
```

**type_inferrer.py**:

```python
# src/core/analyzer/type_inferrer.py
from .types import create_type_name, create_type_level
from .models import InferredType

class TypeInferrer:
    def infer(self, code: str) -> list[InferredType]:
        """型を推論する"""
        return [
            InferredType(
                name=create_type_name("User"),
                level=create_type_level("level2"),
            ),
            InferredType(
                name=create_type_name("Post"),
                level=create_type_level("level3"),
            ),
        ]
```

## まとめ

移行の成功基準:

- [ ] types.py が作成され、プリミティブ型が置き換えられている
- [ ] protocols.py が作成され、インターフェースが明確化されている（オプション）
- [ ] models.py が作成され、ドメインモデルが分離されている（必要に応じて）
- [ ] すべてのテストが通過する
- [ ] mypyとpyrightの型チェックが通過する
- [ ] ドキュメントが更新されている

## 関連ガイド

- [Django風パッケージ構造ガイド](./django-style-structure.md)
- [types.py作成ガイドライン](./types-creation-guide.md)
- [型定義ルール](../typing-rule.md)
