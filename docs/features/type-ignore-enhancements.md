# type:ignore 診断機能の拡張提案

## 概要

現在の`pylay check --focus ignore`機能を拡張し、単なる検出だけでなく、具体的なリファクタリング提案を行う機能を追加します。

## 現在の機能

```bash
$ uv run pylay check --focus ignore
```

**出力**:
- type:ignoreの箇所を検出
- 優先度判定（HIGH/MEDIUM/LOW）
- 簡単な原因説明

## 提案する拡張機能

### 1. パターン検出とリファクタリング提案

#### 1.1 Literal型オーバーライドパターンの検出

**検出条件**:
```python
# AST解析で以下を検出
1. ClassDefノード（BaseModelを継承）
2. フィールドアノテーションが Literal[...]
3. 基底クラスの同名フィールドが str/int等の広い型
4. type: ignore[assignment] コメントがある
```

**提案内容**:
```yaml
pattern: "literal_override"
severity: "medium"
message: "Literal型によるフィールドオーバーライドは型理論的に問題があります"
suggestion:
  - title: "継承を使わない設計に変更（推奨）"
    template: "refactoring_patterns/literal_override_no_inheritance"
    effort: "medium"
  - title: "Tagged Union パターンを使用"
    template: "refactoring_patterns/literal_override_tagged_union"
    effort: "high"
  - title: "フィールドをimmutableにする"
    template: "refactoring_patterns/literal_override_frozen"
    effort: "low"
references:
  - "docs/refactoring-patterns.md#パターン1-literal型のオーバーライド"
  - "https://peps.python.org/pep-0544/"  # Protocol
```

#### 1.2 NewType + Field パターンの検出

**検出条件**:
```python
1. Field(default=...) でプリミティブ値を直接指定
2. フィールド型が NewType
3. type: ignore[assignment] コメント
```

**提案内容**:
```yaml
pattern: "newtype_field_default"
severity: "low"
message: "NewType使用時はデフォルト値を型キャストしてください"
suggestion:
  - title: "NewTypeでキャストする"
    before: "max_depth: MaxDepth = Field(default=10)"
    after: "max_depth: MaxDepth = Field(default=MaxDepth(10))"
    effort: "trivial"
auto_fix: true  # 自動修正可能
```

### 2. インタラクティブモード

```bash
$ uv run pylay check --focus ignore --interactive

Found 3 type:ignore issues with refactoring suggestions:

[1/3] src/core/schemas/yaml_spec.py:62
  Pattern: literal_override
  Issue: type: Literal["list"] = "list"  # type: ignore[assignment]

  Suggestions:
    1. 継承を使わない設計に変更（推奨）
    2. Tagged Union パターンを使用
    3. フィールドをimmutableにする
    4. Skip this issue

  Choose action [1-4]: _
```

### 3. 自動修正機能

```bash
$ uv run pylay check --focus ignore --auto-fix

Analyzing type:ignore issues...
Found 5 auto-fixable issues:

  ✓ src/core/schemas/pylay_config.py:244
    Fixed: MaxDepth(10) applied

  ✓ src/core/schemas/graph.py:99
    Fixed: Weight(1.0) applied

  ! src/core/schemas/yaml_spec.py:62
    Skipped: Manual review required (literal_override)

Applied 2 automatic fixes.
3 issues require manual review.
```

### 4. ナレッジベース構築

#### 4.1 パターンデータベース

```yaml
# .pylay/ignore_patterns.yaml
patterns:
  - id: "literal_override"
    name: "Literal型フィールドオーバーライド"
    detection:
      type: "ast"
      conditions:
        - "is_pydantic_basemodel"
        - "has_literal_field"
        - "overrides_parent_field"
    templates:
      - "no_inheritance"
      - "tagged_union"
      - "frozen_field"

  - id: "newtype_field"
    name: "NewType + Field デフォルト値"
    detection:
      type: "regex"
      pattern: '(\w+):\s*(\w+)\s*=\s*Field\(default=([^)]+)\).*# type: ignore\[assignment\]'
      groups:
        field_name: 1
        type_name: 2
        default_value: 3
    auto_fix:
      enabled: true
      template: "{field_name}: {type_name} = Field(default={type_name}({default_value}))"
```

#### 4.2 プロジェクト固有のルール

```yaml
# pyproject.toml
[tool.pylay.ignore_checker]
# 許容するパターン
allowed_patterns = [
  "pydantic_dynamic_attribute",  # Pydantic動的属性は許容
]

# 警告レベルのカスタマイズ
severity_override = [
  { pattern = "literal_override", severity = "high" },  # プロジェクトでは高優先度
]

# プロジェクト固有のテンプレート
custom_templates = "docs/custom-refactoring-patterns.md"
```

### 5. レポート生成

```bash
$ uv run pylay check --focus ignore --report

Generating type:ignore analysis report...

=== Type:ignore Analysis Report ===

Total issues: 44

By Pattern:
  - literal_override: 7 issues (3 auto-fixable)
  - newtype_field: 5 issues (5 auto-fixable)
  - pydantic_dynamic: 21 issues (0 auto-fixable, allowed pattern)
  - unknown: 11 issues

Recommendations:
  HIGH: 7 issues require design changes
  MEDIUM: 5 issues have simple fixes
  LOW: 32 issues are acceptable

Auto-fix potential: 8 issues (18%)

Saved to: docs/type-ignore-report.md
```

## 実装ロードマップ

### Phase 1: パターン検出（v0.6.0）
- [ ] AST解析でLiteral型オーバーライドを検出
- [ ] NewType + Fieldパターンを検出
- [ ] 検出結果にパターンIDを付与

### Phase 2: リファクタリング提案（v0.7.0）
- [ ] パターンごとの提案を表示
- [ ] ドキュメントへのリンク生成
- [ ] 難易度（effort）の表示

### Phase 3: 自動修正（v0.8.0）
- [ ] NewType + Field の自動修正
- [ ] default_factory への自動変換
- [ ] インタラクティブモード

### Phase 4: ナレッジベース（v1.0.0）
- [ ] パターンデータベース実装
- [ ] カスタムパターン登録
- [ ] プロジェクト固有ルール

## 技術的詳細

### パターン検出アルゴリズム

```python
class TypeIgnorePattern(Protocol):
    """type:ignoreパターンの基底プロトコル"""

    id: str
    name: str
    severity: Literal["high", "medium", "low"]

    def detect(self, node: ast.AST, context: AnalysisContext) -> bool:
        """パターンを検出"""
        ...

    def suggest(self, node: ast.AST) -> list[RefactoringSuggestion]:
        """リファクタリング提案を生成"""
        ...

    def auto_fix(self, node: ast.AST) -> str | None:
        """自動修正コードを生成（可能な場合）"""
        ...

class LiteralOverridePattern(TypeIgnorePattern):
    """Literal型オーバーライドパターン"""

    id = "literal_override"
    name = "Literal型フィールドオーバーライド"
    severity = "medium"

    def detect(self, node: ast.AST, context: AnalysisContext) -> bool:
        if not isinstance(node, ast.ClassDef):
            return False

        # BaseModel継承チェック
        if not self._is_pydantic_model(node):
            return False

        # Literal型フィールドの検出
        for field in node.body:
            if self._is_literal_field(field):
                parent_field = self._get_parent_field(node, field.target.id)
                if parent_field and not self._is_literal(parent_field):
                    return True

        return False
```

### 提案テンプレート

```python
@dataclass
class RefactoringSuggestion:
    """リファクタリング提案"""

    title: str
    description: str
    effort: Literal["trivial", "low", "medium", "high"]
    template_id: str
    auto_fixable: bool

    def generate_code(self, context: CodeContext) -> str:
        """提案に基づいたコードを生成"""
        template = load_template(self.template_id)
        return template.render(context)
```

## まとめ

この拡張により、pylayは単なる検出ツールから、**積極的な設計改善を提案する賢いツール**に進化します。

開発者は：
1. type:ignoreの理由を理解できる
2. 具体的な修正方法を学べる
3. 自動修正で時間を節約できる
4. プロジェクト固有のベストプラクティスを蓄積できる
