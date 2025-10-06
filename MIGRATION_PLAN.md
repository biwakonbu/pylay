# 型定義パターン移行計画（PEP 484準拠）

## 📋 概要

pylayプロジェクトの型定義パターンを**PEP 484完全準拠**に移行します。

### 変更の背景

**問題**: 従来の`NewType('X', Annotated[...])`パターンはPEP 484非準拠
- PEP 484仕様: `NewType`の第2引数はクラスのみ許可（`Annotated`は型構築子）
- pyrightで型エラーが発生（mypyは拡張機能として許可）

**解決策**: `NewType` + ファクトリ関数パターンに移行
- PEP 484完全準拠
- pyrightとmypyの両方で型チェック通過
- 名目的型付けの維持
- バリデーションの分離・明示化

### 新旧パターン比較

**旧パターン（PEP 484非準拠）**:
```python
from typing import Annotated
from pydantic import Field

type UserId = Annotated[str, Field(min_length=8)]
```

**新パターン（PEP 484準拠）**:
```python
from typing import NewType, Annotated
from pydantic import Field, TypeAdapter, validate_call

# パターン1: TypeAdapter + ファクトリ関数（基本）
UserId = NewType('UserId', str)
UserIdValidator = TypeAdapter(Annotated[str, Field(min_length=8)])

def create_user_id(value: str) -> UserId:
    validated = UserIdValidator.validate_python(value)
    return UserId(validated)

# パターン2: @validate_call + 関数名再利用（実用的、推奨）
UserId = NewType('UserId', str)

@validate_call
def UserId(value: Annotated[str, Field(min_length=8)]) -> UserId:  # type: ignore[no-redef]
    return NewType('UserId', str)(value)
```

---

## 🎯 移行の方針

### 段階的移行の原則

1. **破壊的変更を避ける**: 既存コードは引き続き動作
2. **新規作成は新パターン**: これから書くコードは新パターンを使用
3. **解析ロジックの両対応**: 新旧両方のパターンを検出可能に
4. **ドキュメント優先**: 新パターンの推奨を明示

### 移行完了の定義

- ✅ ドキュメントが新パターンを推奨
- ✅ 解析ロジックが新パターンを検出可能
- ✅ 改善プランが新パターンを提示
- ✅ 既存コードが段階的に新パターンへ移行（任意）

---

## 📅 移行スケジュール

### Phase 0: ドキュメント更新【完了】✅

**目的**: 新パターンの推奨を明示

**完了済み**:
- ✅ `docs/typing-rule.md` - Level 2定義を全面改訂
- ✅ `AGENTS.md` - Level 2定義を更新
- ✅ `CLAUDE.md` - Level 2定義を更新
- ✅ Issue #45とPR #47の本文を更新

**成果物**: 新パターンのドキュメント化

---

### Phase 1: 型レベル検出ロジックの拡張【次のステップ】🔧

**目的**: 新パターン（`NewType` + ファクトリ関数）をLevel 2として検出

**対象ファイル**:
- `src/core/analyzer/type_classifier.py`
- `src/core/analyzer/type_level_analyzer.py`

**実装内容**:

1. **NewType定義の検出**
   ```python
   # 検出パターン
   NEWTYPE_PATTERN = re.compile(
       r'^(\w+)\s*=\s*NewType\([\'"](\w+)[\'"]\s*,\s*(\w+)\)',
       re.MULTILINE
   )
   ```

2. **ファクトリ関数の検出**
   ```python
   # パターン1: create_* 関数
   FACTORY_PATTERN = re.compile(
       r'def\s+create_(\w+)\s*\([^)]*\)\s*->\s*(\w+):',
       re.MULTILINE
   )

   # パターン2: @validate_call + 同名関数
   VALIDATE_CALL_PATTERN = re.compile(
       r'@validate_call\s+def\s+(\w+)\s*\([^)]*\)\s*->\s*(\w+):',
       re.MULTILINE
   )
   ```

3. **ペアリング判定**
   ```python
   def _detect_newtype_with_factory(self, source_code: str) -> list[TypeDefinition]:
       """NewType + ファクトリ関数のペアを検出"""
       newtype_defs = {}  # {type_name: (line, definition)}
       factory_funcs = {}  # {type_name: factory_function}

       # NewType定義を収集
       for match in NEWTYPE_PATTERN.finditer(source_code):
           var_name = match.group(1)
           type_name = match.group(2)
           base_type = match.group(3)
           # ...

       # ファクトリ関数を収集
       for match in FACTORY_PATTERN.finditer(source_code):
           # ...

       # ペアになっているものをLevel 2と判定
       level2_types = []
       for type_name in newtype_defs:
           if type_name in factory_funcs:
               level2_types.append(...)

       return level2_types
   ```

**テスト**:
```python
# tests/test_type_classifier.py
def test_detect_newtype_with_factory():
    """NewType + ファクトリ関数パターンの検出"""
    source_code = """
    from typing import NewType, Annotated
    from pydantic import Field, TypeAdapter

    UserId = NewType('UserId', str)
    UserIdValidator = TypeAdapter(Annotated[str, Field(min_length=8)])

    def create_user_id(value: str) -> UserId:
        validated = UserIdValidator.validate_python(value)
        return UserId(validated)
    """

    result = classifier.classify_types(source_code)
    assert result['UserId'].level == 'level2'
```

**完了条件**:
- [ ] 新パターンがLevel 2として検出される
- [ ] 旧パターンも引き続きLevel 2として検出される
- [ ] テストが全て通過
- [ ] `make type-check`が成功

---

### Phase 2: 改善プランテンプレートの更新【次のステップ】📝

**目的**: Level 2への昇格推奨で新パターンを提示

**対象ファイル**:
- `src/core/analyzer/quality_checker.py`
- `src/core/analyzer/improvement_templates.py`

**実装内容**:

1. **`improvement_templates.py`に新テンプレート追加**
   ```python
   # 新パターンのテンプレート
   LEVEL2_NEWTYPE_TEMPLATE = """
   ## Level 2: NewType + ファクトリ関数パターン（PEP 484準拠、推奨）

   ```python
   from typing import NewType, Annotated
   from pydantic import Field, validate_call

   # NewType定義
   {type_name} = NewType('{type_name}', {base_type})

   # ファクトリ関数（バリデーション付き）
   @validate_call
   def {type_name}(value: Annotated[{base_type}, Field({constraints})]) -> {type_name}:
       return NewType('{type_name}', {base_type})(value)
   ```

   使用例:
   ```python
   user_id = {type_name}("user_12345")  # ✅ バリデーション実行
   ```
   """
   ```

2. **`_generate_primitive_replacement_plan`メソッドの更新**
   ```python
   def _generate_primitive_replacement_plan(self, detail: PrimitiveUsageDetail) -> str:
       """primitive型置き換えの詳細プランを生成（新パターン対応）"""

       # ... (既存の推測ロジック)

       # 新パターンのプランを生成
       plan = f"""primitive型 {detail.primitive_type} をドメイン型に置き換える手順:

   ## 推奨: NewType + ファクトリ関数パターン（PEP 484準拠）

   ### Step 1: src/core/schemas/types.py に型定義を作成

   ```python
   from typing import NewType, Annotated
   from pydantic import Field, validate_call

   # 型名候補: {', '.join(type_candidates)}

   # NewType定義
   {type_candidates[0]} = NewType('{type_candidates[0]}', {detail.primitive_type})

   # ファクトリ関数（バリデーション付き）
   @validate_call
   def {type_candidates[0]}(
       value: Annotated[{detail.primitive_type}, Field({suggested_constraints})]
   ) -> {type_candidates[0]}:
       '''{{description}}'''
       return NewType('{type_candidates[0]}', {detail.primitive_type})(value)
   ```

   ### Step 2: 使用箇所を修正

   File: {detail.location.file}:{detail.location.line}

   ```python
   # インポート追加
   from src.core.schemas.types import {type_candidates[0]}

   # Before
   {detail.location.code.strip()}

   # After
   {fixed_code}

   # 値の生成（バリデーション付き）
   value = {type_candidates[0]}("example_value")
   ```

   ### 利点
   - ✅ PEP 484完全準拠（pyrightとmypyの両対応）
   - ✅ 名目的型付け（{type_candidates[0]}とstrが区別される）
   - ✅ 自動バリデーション（@validate_callで実行）
   - ✅ 型安全性向上

   ### 参考
   - 型定義ルール: docs/typing-rule.md - Level 2
   - 既存の型定義: src/core/schemas/types.py
   """
       return plan
   ```

**完了条件**:
- [ ] 改善プランが新パターンを提示
- [ ] `pylay quality`コマンドで新パターンが表示される
- [ ] テストが全て通過

---

### Phase 3: primitive型検出ロジックの拡張【Phase 2後】🔍

**目的**: `NewType` + ファクトリ関数パターンをprimitive使用として検出**しない**

**対象ファイル**:
- `src/core/analyzer/code_locator.py`

**実装内容**:

1. **`_extract_primitive_type`メソッドの拡張**
   ```python
   def _extract_primitive_type(self, annotation: ast.expr) -> str | None:
       """アノテーションからprimitive型を抽出

       Note:
           以下のパターンを検出:
           - 直接のprimitive型: str, int, float, bool, bytes
           - Annotated内のprimitive型: Annotated[str, ...]

           以下は検出しない:
           - NewType定義: NewType('X', str) → primitive使用ではない
           - ファクトリ関数の返り値: -> UserId → primitive使用ではない
       """
       # ... (既存ロジック)

       # NewTypeチェックを追加
       if isinstance(annotation, ast.Call):
           if isinstance(annotation.func, ast.Name) and annotation.func.id == "NewType":
               # NewType定義はprimitive使用としてカウントしない
               return None

       # ... (残りのロジック)
   ```

2. **ファクトリ関数のチェック追加**
   ```python
   def _is_factory_function(self, node: ast.FunctionDef) -> bool:
       """ファクトリ関数かどうかを判定"""
       # create_* パターン
       if node.name.startswith("create_"):
           return True

       # @validate_call デコレータ付き
       for decorator in node.decorator_list:
           if isinstance(decorator, ast.Name) and decorator.id == "validate_call":
               return True

       return False
   ```

**完了条件**:
- [ ] NewType定義がprimitive使用として検出されない
- [ ] ファクトリ関数の返り値がprimitive使用として検出されない
- [ ] テストが全て通過

---

### Phase 4: 既存コードベースの段階的移行【任意】🔄

**目的**: 既存の型定義を新パターンに段階的に移行

**方針**:
- **任意実施**: 旧パターンも引き続き動作するため、緊急性は低い
- **優先度順**: 使用頻度の高い型から順次移行
- **破壊的変更なし**: 使用箇所の変更は最小限に

**対象ファイル**:
| ファイル | 型定義数 | 優先度 | 備考 |
|---------|---------|--------|------|
| `src/core/schemas/types.py` | 4箇所 | HIGH | コア型定義（全モジュールで使用） |
| `src/core/analyzer/types.py` | 2箇所 | MEDIUM | analyzerモジュール内のみ |
| `src/core/converters/types.py` | 2箇所 | MEDIUM | convertersモジュール内のみ |
| `src/core/doc_generators/types.py` | 2箇所 | MEDIUM | doc_generatorsモジュール内のみ |
| その他 | 4箇所 | LOW | 使用頻度が低い |

**変換手順（例: `IndexFilename`）**:

1. **変更前**:
   ```python
   # src/core/schemas/types.py
   type IndexFilename = Annotated[str, AfterValidator(validate_index_filename)]
   ```

2. **変更後**:
   ```python
   # src/core/schemas/types.py
   from typing import NewType, Annotated
   from pydantic import AfterValidator, validate_call

   IndexFilename = NewType('IndexFilename', str)

   @validate_call
   def IndexFilename(  # type: ignore[no-redef]
       value: Annotated[str, AfterValidator(validate_index_filename)]
   ) -> IndexFilename:
       '''インデックスファイル名（バリデーション付き）'''
       return NewType('IndexFilename', str)(value)
   ```

3. **使用箇所の変更**:
   ```python
   # 変更前
   filename: IndexFilename = "types_index.yaml"

   # 変更後（バリデーション付き生成）
   filename = IndexFilename("types_index.yaml")
   ```

**完了条件**:
- [ ] コア型定義（`src/core/schemas/types.py`）の移行完了
- [ ] 各モジュールの型定義の移行完了
- [ ] `make type-check`が成功
- [ ] `make test`が全て通過

---

## ✅ 進捗管理

### 完了済み ✅

- [x] **Phase 0**: ドキュメント更新
  - [x] `docs/typing-rule.md` 更新
  - [x] `AGENTS.md` 更新
  - [x] `CLAUDE.md` 更新
  - [x] Issue #45とPR #47の本文更新

- [x] **Phase 1**: 型レベル検出ロジックの拡張
  - [x] `NEWTYPE_PATTERN`の追加
  - [x] `FACTORY_PATTERN`の追加
  - [x] `VALIDATE_CALL_PATTERN`の追加
  - [x] `_detect_newtype_with_factory()`メソッドの実装
  - [x] `_classify_assign_alias()`の修正（NewTypeスキップ）
  - [x] テストケース24件追加（全て成功）

- [x] **Phase 2**: 改善プランテンプレートの更新
  - [x] `quality_checker.py`の推奨テキスト更新
  - [x] `pyproject.toml`のimprovement_guidance更新

- [x] **Phase 3**: primitive型検出ロジックの拡張
  - [x] `code_locator.py`のNewType定義除外処理

### 未着手 📋

- [ ] **Phase 4**: 既存コードベースの段階的移行（任意）
  - 旧パターンも動作するため、緊急性は低い
  - 必要に応じて段階的に実施

---

## 📊 成功基準

### 必須（Phase 1-3）

- ✅ mypyとpyrightの両方で型チェック通過
- ✅ 新パターンがLevel 2として検出される
- ✅ 改善プランが新パターンを提示
- ✅ 全テストが通過（`make test`）
- ✅ ドキュメントが新パターンを推奨

### 任意（Phase 4）

- 既存の型定義が新パターンに移行
- 使用箇所が新しい使用法に更新

---

## 🔗 参考資料

- [PEP 484 – Type Hints](https://peps.python.org/pep-0484/) - NewTypeの仕様
- [docs/typing-rule.md](docs/typing-rule.md) - 新しい型定義ルール
- [Pydantic TypeAdapter](https://docs.pydantic.dev/latest/concepts/type_adapter/) - ランタイムバリデーション
- [Pydantic validate_call](https://docs.pydantic.dev/latest/concepts/validation_decorator/) - 関数バリデーション

---

## 📝 更新履歴

- 2025-10-07: 初版作成（Phase 0完了、Phase 1-3計画策定）
