# pylay: YAML <-> Python型 + docstrings マッピング仕様 (v1.1)

## 目的

pylayプロジェクトにおけるYAML型仕様とPythonの型ヒント + docstringsの役割を明確化する仕様書です。
- YAML形式での型表現とPython型の対応関係を定義
- docstringsのYAML `description` フィールドへの自動マッピング
- 相互変換（Python型 ↔ YAML）のラウンドトリップ整合性確保

この仕様はYAMLの階層性を活かした「立体的な」構造を採用。`name` フィールドを省略し、トップレベルキーを型名として使用します。

## 1. 基本原則

### 1.1 型情報の役割
- **Python側**: 型ヒント（typingモジュール）とdocstringsで型安全性を記述し、ドキュメントを自動生成
- **YAML側**: 型仕様をYAMLでシリアライズ。Pydantic BaseModelでバリデーションし、Markdownドキュメント生成を支援
- **変換フロー**: Python型 → YAML → TypeSpec → Markdown（順方向）。逆方向もラウンドトリップ可能

### 1.2 docstringsの扱い
- Pythonの `__doc__` 属性をYAMLの `description` に自動反映（`inspect.getdoc(typ)` 使用）
- 原則: docstringsは人間可読の説明文。YAMLではオプションだが、存在すればMarkdownヘッダー/本文に展開
- フィールドレベル: クラス属性のdocstringsをプロパティdescriptionに反映（Pydantic Field拡張対応）

### 1.3 相互変換の透過性 (ラウンドトリップ)
- **要件**: Python型 → YAML → Python型 で、元の型情報（type, description, 構造）が同等に復元可能
- **透過性の基準**:
  - 型カテゴリ（str/int/list/dict/union）が一致
  - descriptionがdocstringsと同等（null/文字列の復元）
  - 複合型のネスト/参照が維持（例: List[User] → items: User）
  - 損失なし: 変換で情報が失われない（例: 循環参照解決）
- **検証方法**: ラウンドトリップテスト（type_to_yaml → yaml_to_spec → type_to_yaml で同一YAML生成）
- **制限**: 動的型（ForwardRef）や未サポート型は部分透過性。段階的拡張で完全透過を目指す
- **欠損保証**: 生成YAMLと復元YAMLの文字列比較（正規化後）。descriptionの有無/内容を個別アサーション

## 2. YAML型仕様の構造 (v1.1)

YAMLはPydantic BaseModelで定義。トップレベルキーを型名として使用し、`name` フィールドを省略。単一型または複数型（`types` ルート）で表現。

### 2.1 単一型の場合
トップレベルキーが型名。Dict/List/Unionなどの複合型は再帰的にキー/値で表現。

```yaml
User:                          # 型名をキーとして使用
  type: dict                   # 型カテゴリ (str, int, float, bool, list, dict, union)
  description: ユーザー情報を表す型  # docstringsから自動取得 (オプション)
  required: true               # 必須フラグ (デフォルト: true)
  additional_properties: false  # Dictの場合の追加プロパティ許可 (デフォルト: false)
  properties:                  # Dictの場合: プロパティ（キー名=プロパティ名）
    id:
      type: int
      description: ユーザーID    # プロパティdocstringsから取得
      required: true
    name:
      type: str
      description: ユーザー名
      required: true
    email:
      type: str
      description: メールアドレス
      required: false

Users:                         # List型例
  type: list
  description: ユーザーリスト
  items:                       # Listの場合: 要素型（キー名=要素型名）
    User: {}                   # 参照（循環参照対応。空オブジェクトで型名指定）
```

### 2.2 複数型の場合 (推奨)
モジュール全体の型仕様を1ファイルにまとめる場合、`types` ルートを使用。

```yaml
types:                        # ルートキー: 複数型を管理
  User:
    type: dict
    description: ユーザー情報を表す型
    properties:
      id:
        type: int
        description: ユーザーID
        required: true
      name:
        type: str
        description: ユーザー名
        required: true
  Users:
    type: list
    description: ユーザーリスト
    items:
      User: {}                 # User型を参照（型名キー）
  Result:
    type: union
    description: 結果型 (数値または文字列)
    variants:                  # Unionの場合: バリアント配列（各要素に型キー）
      - type: int
      - type: str
```

#### 構造の利点
- **簡潔で直感的**: キー名が型/プロパティ名を兼ね、重複記述なし（例: `User.properties.id`）
- **階層性（立体性）**: YAMLのネストを活かし、複合型を自然に表現
- **拡張性**: `types` ルートで複数型管理。参照（`items: User`）で循環/共有型対応
- **Pydantic互換**: Rootを `dict[str, TypeSpec]` で動的バリデーション可能

#### 参照と循環対応
- 参照: `items: User` で既存型をキー参照（YAMLアンカー `&User` もオプション対応）
- 循環参照: 解析時に型名をキーとして解決（例: 相互参照型）

## 3. Python型とYAMLのマッピング

### 3.1 基本型
| Python型 | YAML表現 (キー下) | descriptionの扱い |
|----------|-------------------|-------------------|
| `str`    | `str` キー下 `type: str` | `__doc__` を反映 |
| `int`    | `int` キー下 `type: int` | 同上 |
| `float`  | `float` キー下 `type: float` | 同上 |
| `bool`   | `bool` キー下 `type: bool` | 同上 |

**例**:
```python
class UserId:  # NewType相当
    '''ユーザーID（正の整数）'''
    value: int

# YAML出力 (複数型):
types:
  UserId:
    type: int
    description: ユーザーID（正の整数）
```

### 3.2 コレクション型
- **List[T]**: `type: "list"`, `items: TのYAML表現` (T型名をキー)
- **Dict[K, V]**: `type: "dict"`, `properties: {K: VのYAML表現}` (Kをキー名)

**例**:
```python
from typing import List
class User:
    '''ユーザークラス'''
    name: str

Users = List[User]

# YAML出力 (複数型):
types:
  Users:
    type: list
    description: null  # List自体の__doc__なし（要改善: ジェネリックdoc拡張）
    items:
      User:
        type: dict
        description: ユーザークラス
        properties:
          name:
            type: str
            description: null  # フィールドdocstrings未対応（要拡張）
```

### 3.3 Union型
- **Union[T1, T2]**: `type: "union"`, `variants: [T1のYAML, T2のYAML]` (配列要素に型キー)

**例**:
```python
from typing import Union
Result = Union[int, str]  # 結果型

# YAML出力 (複数型):
types:
  Result:
    type: union
    description: 結果型 (数値または文字列)
    variants:
      - type: int
      - type: str
```

## 4. docstringsの詳細マッピング

### 4.1 取得方法
- `inspect.getdoc(typ)` で型/クラスのdocstring取得
- フィールドレベル: クラス属性docstrings（dataclasses/Pydantic Fieldのmetadata対応）
- 優先順位: クラスdoc > プロパティdoc > デフォルトnull

### 4.2 変換フロー
1. **Python → YAML**:
   - `type_to_spec()` で型名をキー、内容に `__doc__` を `description` に設定
   - 再帰適用: サブ型（items, properties, variants）のdescriptionもdocstringsから取得
   - 出力: `{型名: spec.model_dump(exclude={'name'})}` または `types: {型名: ...}`

2. **YAML → TypeSpec**:
   - ルートキーを型名として解析、`name` 省略時はキーから補完
   - Pydantic `TypeRoot` でバリデーション（`types: dict[str, TypeSpec]`）

3. **YAML → Markdown**:
   - 型名キーをヘッダー（`# 型仕様: User`）
   - `description` を本文展開、プロパティごとにサブセクション

4. **ラウンドトリップ (透過性検証)**:
   - **流れ**: Python型 → YAML生成 (type_to_yaml) → TypeSpec解析 (yaml_to_spec) → YAML復元 (type_to_yaml)
   - **チェック**: 生成YAMLと復元YAMLを文字列比較（正規化: インデント/順序無視）
   - **具体例**:
     ```python
     # 元のPython型
     class User:
         '''ユーザー情報を表す型'''
         id: int

     # → YAML生成
     yaml_original = """
     types:
       User:
         type: dict
         description: ユーザー情報を表す型
         properties:
           id:
             type: int
     """

     # → yaml_to_spec → type_to_spec → YAML復元
     spec = yaml_to_spec(yaml_original)
     yaml_restored = type_to_yaml(spec.types['User'], as_root=True)  # またはTypeRoot全体

     # → 比較アサーション
     assert normalize_yaml(yaml_original) == normalize_yaml(yaml_restored)  # 同一確認
     assert spec.types['User'].description == 'ユーザー情報を表す型'  # description復元
     ```
   - **ツール**: pytestでYAML比較ライブラリ（deepdiff or yaml-safe-load + dict比較）。descriptionの有無/内容を個別テスト
   - **欠損保証**: 比較で差分検出時エラー。description null/文字列の復元を明示テスト

### 4.3 課題と対応
- **ジェネリック型のdescription**: List/Dict自体の__doc__がNone → TypeFactory拡張で要素型docを継承
- **フィールドdocstrings**: 未対応 → Pydantic Field(metadata) または属性doc取得を実装
- **循環参照**: 解析時に型名キー解決 → 遅延評価 or YAMLアンカー対応
- **透過性の損失**: 未サポート型（Generic/ForwardRef） → 段階的拡張（エラー/部分復元）。テストで80%復元率保証

## 5. 実装方針
- **schemas/yaml_type_spec.py**: `name: Optional[str]`、Root `TypeRoot(types: dict[str, TypeSpec])`
- **converters/type_to_yaml.py**: `as_root=True` でキー出力、`description=inspect.getdoc(typ)`
- **converters/yaml_to_type.py**: ルートキー解析、`yaml_to_spec(data, root_key=None)`
- **doc_generators/yaml_doc_generator.py**: ルートキーから型名取得、ヘッダー生成調整
- **テスト**: v1.1構造のラウンドトリップ（単一/複数型、docstrings反映）
- **互換性**: `as_root=False` でv1形式出力オプション

## 6. 次のステップ
- v1.1構造のプロトタイプ実装とテスト
- docstrings自動取得の完全対応（フィールドレベル含む）
- ラウンドトリップ検証: Python型 ↔ YAMLの透過性テスト（pytestでYAML比較、description/構造の欠損なし保証）
  - テスト例: 10種の型（基本/コレクション/Union）で復元率100%確認
  - ツール: pytest + yamlライブラリで自動化
- サンプルYAML生成とMarkdown出力確認
- 仕様の最終レビュー

---
*最終更新: 2025-09-27*
*バージョン: v1.1*
