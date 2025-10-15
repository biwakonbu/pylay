"""
改善プランテンプレート

型定義の品質改善のための具体的なテンプレートとヒューリスティックを提供します。
"""

# Pydantic提供の型マッピング
PYDANTIC_TYPES: dict[str, dict[str, str]] = {
    "email": {
        "type": "EmailStr",
        "import": "from pydantic import EmailStr",
        "description": "メールアドレス(自動バリデーション)",
        "example": "user_email: EmailStr",
    },
    "url": {
        "type": "HttpUrl",
        "import": "from pydantic import HttpUrl",
        "description": "HTTP/HTTPS URL(自動バリデーション)",
        "example": "website: HttpUrl",
    },
    "filepath": {
        "type": "FilePath",
        "import": "from pydantic import FilePath",
        "description": "既存ファイルのパス(存在チェック)",
        "example": "config_file: FilePath",
    },
    "newpath": {
        "type": "NewPath",
        "import": "from pydantic import NewPath",
        "description": "新規作成するファイルのパス",
        "example": "output_file: NewPath",
    },
    "dirpath": {
        "type": "DirectoryPath",
        "import": "from pydantic import DirectoryPath",
        "description": "既存ディレクトリのパス(存在チェック)",
        "example": "data_dir: DirectoryPath",
    },
    "positive_int": {
        "type": "PositiveInt",
        "import": "from pydantic import PositiveInt",
        "description": "正の整数(1以上)",
        "example": "count: PositiveInt",
    },
    "non_negative_int": {
        "type": "NonNegativeInt",
        "import": "from pydantic import NonNegativeInt",
        "description": "非負整数(0以上)",
        "example": "index: NonNegativeInt",
    },
    "positive_float": {
        "type": "PositiveFloat",
        "import": "from pydantic import PositiveFloat",
        "description": "正の浮動小数点数",
        "example": "score: PositiveFloat",
    },
    "non_negative_float": {
        "type": "NonNegativeFloat",
        "import": "from pydantic import NonNegativeFloat",
        "description": "非負浮動小数点数",
        "example": "weight: NonNegativeFloat",
    },
    "uuid": {
        "type": "UUID4",
        "import": "from pydantic import UUID4",
        "description": "UUID version 4",
        "example": "id: UUID4",
    },
    "secret": {
        "type": "SecretStr",
        "import": "from pydantic import SecretStr",
        "description": "機密文字列(ログに表示されない)",
        "example": "password: SecretStr",
    },
}

# バリデーションパターンのカタログ
VALIDATION_PATTERNS: dict[str, dict[str, str]] = {
    "email": {
        "validator": """def validate_email(v: str) -> str:
    if "@" not in v:
        raise ValueError("有効なメールアドレスではありません")
    return v""",
        "description": "メールアドレス形式のチェック",
    },
    "non_empty": {
        "validator": """def validate_non_empty(v: str) -> str:
    if not v:
        raise ValueError("空文字列は許可されていません")
    return v""",
        "description": "空文字列チェック",
    },
    "identifier": {
        "validator": """def validate_identifier(v: str) -> str:
    if not v.isidentifier():
        raise ValueError("Python識別子である必要があります")
    return v""",
        "description": "Python識別子チェック",
    },
    "positive_int": {
        "validator": """def validate_positive(v: int) -> int:
    if v <= 0:
        raise ValueError("正の整数である必要があります")
    return v""",
        "description": "正の整数チェック",
    },
    "non_negative_int": {
        "validator": """def validate_non_negative(v: int) -> int:
    if v < 0:
        raise ValueError("0以上の整数である必要があります")
    return v""",
        "description": "非負整数チェック",
    },
    "url": {
        "validator": """def validate_url(v: str) -> str:
    if not v.startswith(("http://", "https://")):
        raise ValueError("有効なURLではありません")
    return v""",
        "description": "URL形式のチェック",
    },
    "file_path": {
        "validator": """def validate_file_path(v: str) -> str:
    from pathlib import Path
    if not Path(v).exists():
        raise ValueError(f"ファイルが存在しません: {v}")
    return v""",
        "description": "ファイルパス存在チェック",
    },
}


def _is_excluded_variable_name(var_name: str) -> bool:
    """変数名が除外パターンに該当するかをチェック

    Args:
        var_name: 変数名

    Returns:
        除外対象の場合True、それ以外False
    """
    var_lower = var_name.lower()

    # 除外パターン1: 一般的な変数名（設定値、フォーマット指定、一時変数等）
    exclude_exact = [
        "ctx",  # click.Context等のフレームワーク変数
        "context",
        "self",
        "cls",
        "args",
        "kwargs",
        "format",
        "type",
        "kind",
        "mode",
        "style",
        "encoding",
        "message",
        "error",
        "text",
        "value",
        "name",
        "key",
        "title",
        "label",
        "description",
        "data",
        "result",
        "output",
        "input",
        "verbose",
        "strict",
        "details",
    ]
    # 完全一致で除外
    if var_lower in exclude_exact:
        return True

    # 除外パターン2: サフィックスパターン
    exclude_suffixes = [
        "_format",
        "_type",
        "_kind",
        "_mode",
        "_style",
        "_encoding",
        "_message",
        "_error",
        "_text",
        "_value",
        "_name",
        "_key",
        "_title",
        "_label",
        "_description",
    ]
    # サフィックスで除外
    return any(var_lower.endswith(suffix) for suffix in exclude_suffixes)


def suggest_pydantic_type(var_name: str, primitive_type: str) -> dict[str, str] | None:
    """変数名とprimitive型からPydantic提供の型を推奨

    Args:
        var_name: 変数名(例: "user_email", "count")
        primitive_type: primitive型(例: "str", "int")

    Returns:
        Pydantic型の情報（type, import, description）またはNone
    """
    # 除外パターンチェック
    if _is_excluded_variable_name(var_name):
        return None

    var_lower = var_name.lower()

    # str型の場合
    if primitive_type == "str":
        # メールアドレス(明確なパターンのみ)
        if var_lower in ("email", "mail") or var_lower.endswith("_email"):
            return PYDANTIC_TYPES["email"]
        # URL(明確なパターンのみ)
        if var_lower in ("url", "link", "href") or var_lower.endswith("_url"):
            return PYDANTIC_TYPES["url"]
        # output系のファイル(新規作成を想定)
        if var_lower.startswith("output_") and ("file" in var_lower or "path" in var_lower):
            # output系は新規作成ファイルなのでNewPath、なければFilePath
            return PYDANTIC_TYPES.get("newpath", PYDANTIC_TYPES["filepath"])
        # input系のファイル(既存ファイルを想定)
        if var_lower.startswith("input_") and ("file" in var_lower or "path" in var_lower):
            # input系は既存ファイルなのでFilePath
            return PYDANTIC_TYPES["filepath"]
        # ファイルパス(より厳密に)
        if var_lower in ("file", "filename", "filepath"):
            return PYDANTIC_TYPES["filepath"]
        if var_lower.endswith(("_file", "_filename", "_filepath")):
            return PYDANTIC_TYPES["filepath"]
        # ディレクトリパス
        if var_lower in ("dir", "directory", "dirpath") or var_lower.endswith(("_dir", "_directory", "_dirpath")):
            return PYDANTIC_TYPES["dirpath"]
        # 機密情報
        if any(keyword in var_lower for keyword in ("password", "secret", "token", "api_key")):
            return PYDANTIC_TYPES["secret"]
        # UUID(明確なパターンのみ)
        if var_lower in ("uuid", "guid") or var_lower.endswith(("_uuid", "_guid")):
            return PYDANTIC_TYPES["uuid"]

    # int型の場合
    elif primitive_type == "int":
        # 正の整数
        if any(keyword in var_lower for keyword in ("count", "num", "size", "length")):
            return PYDANTIC_TYPES["positive_int"]
        # 非負整数(インデックス、深度等)
        if "index" in var_lower or "depth" in var_lower or "level" in var_lower:
            return PYDANTIC_TYPES["non_negative_int"]

    # float型の場合
    elif primitive_type == "float":
        # 正の浮動小数点数
        if any(keyword in var_lower for keyword in ("score", "rate", "ratio", "percentage")):
            return PYDANTIC_TYPES["positive_float"]
        # 非負浮動小数点数
        if "weight" in var_lower or "distance" in var_lower:
            return PYDANTIC_TYPES["non_negative_float"]

    return None


def suggest_type_name(var_name: str, primitive_type: str) -> list[str]:
    """変数名とprimitive型から型名候補を推測

    Args:
        var_name: 変数名(例: "user_id", "email_address")
        primitive_type: primitive型(例: "str", "int")

    Returns:
        型名候補のリスト（上位3候補）
    """
    candidates: list[str] = []
    var_lower = var_name.lower()

    # パターン1: _id で終わる場合
    if "_id" in var_lower:
        prefix = var_lower.split("_id")[0]
        pascal_prefix = "".join(word.capitalize() for word in prefix.split("_"))
        candidates.append(f"{pascal_prefix}Id")

    # パターン2: キーワードから推測
    keyword_mappings = {
        "email": "EmailAddress",
        "path": "FilePath",
        "file": "FilePath",
        "url": "Url",
        "name": "Name",
        "count": "Count",
        "index": "Index",
        "size": "Size",
        "length": "Length",
        "code": "Code",
        "key": "Key",
        "value": "Value",
        "text": "Text",
        "message": "Message",
        "description": "Description",
        "title": "Title",
    }

    for keyword, type_name in keyword_mappings.items():
        if keyword in var_lower and type_name not in candidates:
            candidates.append(type_name)
            break

    # パターン3: 汎用候補（snake_case → PascalCase）
    if not candidates:
        pascal_case = "".join(word.capitalize() for word in var_name.split("_"))
        if pascal_case and pascal_case not in candidates:
            candidates.append(pascal_case)

    # 候補が1つだけの場合、汎用候補も追加
    if len(candidates) == 1:
        pascal_case = "".join(word.capitalize() for word in var_name.split("_"))
        if pascal_case != candidates[0]:
            candidates.append(pascal_case)

    # 型の種類に応じた代替候補
    if primitive_type == "str" and "Text" not in candidates:
        candidates.append("Text")
    elif primitive_type == "int" and "Count" not in candidates:
        candidates.append("Count")

    return candidates[:3]  # 上位3候補


def suggest_validation_patterns(var_name: str, primitive_type: str) -> list[str]:
    """変数名とprimitive型から適用可能なバリデーションパターンを提案

    Args:
        var_name: 変数名
        primitive_type: primitive型

    Returns:
        適用可能なバリデーションパターンのキーリスト
    """
    suggestions: list[str] = []
    var_lower = var_name.lower()

    if primitive_type == "str":
        # 常に空文字チェックを推奨
        suggestions.append("non_empty")

        # キーワードベースの提案
        if "email" in var_lower:
            suggestions.append("email")
        if "url" in var_lower:
            suggestions.append("url")
        if "path" in var_lower or "file" in var_lower:
            suggestions.append("file_path")
        if "name" in var_lower or "identifier" in var_lower:
            suggestions.append("identifier")

    elif primitive_type == "int":
        # count, num, idなどは正の整数を推奨
        if any(keyword in var_lower for keyword in ["count", "num", "id", "index"]):
            suggestions.append("positive_int")
        # size, lengthなどは非負整数を推奨
        elif any(keyword in var_lower for keyword in ["size", "length", "age"]):
            suggestions.append("non_negative_int")

    return suggestions[:2]  # 上位2つを推奨


def format_validation_checklist(primitive_type: str) -> str:
    """バリデーションチェックリストをフォーマット

    Args:
        primitive_type: primitive型

    Returns:
        フォーマット済みのチェックリスト文字列
    """
    common_checks = [
        "[ ] 空文字チェック",
        "[ ] 形式チェック(識別子、メール、URL など)",
        "[ ] 長さ制限",
        "[ ] 許可リスト/拒否リスト",
        "[ ] 既存データとの整合性チェック",
    ]

    if primitive_type == "int":
        int_checks = [
            "[ ] 範囲チェック(最小値・最大値)",
            "[ ] 正の整数チェック",
            "[ ] 非負整数チェック",
        ]
        return "\n  ".join(int_checks)

    return "\n  ".join(common_checks)


def extract_variable_name(code_line: str) -> str:
    """コード行から変数名を抽出

    Args:
        code_line: コード行(例: "type_name: str = type_def.name")

    Returns:
        抽出された変数名(例: "type_name")
    """
    import re

    # パターン1: 関数パラメータ(def func(param: type)または (self, param: type)
    if "def " in code_line or "(" in code_line:
        # 関数パラメータ部分を抽出
        # 例: "def func(self, filename: str = 'test.txt')" → "filename"
        param_match = re.search(r"[,\(]\s*([a-zA-Z_]\w*)\s*:", code_line)
        if param_match:
            param_name = param_match.group(1)
            # selfやclsは除外
            if param_name not in ("self", "cls"):
                return param_name

    # パターン2: 変数アノテーション(var_name: type)
    if ":" in code_line and "def " not in code_line:
        parts = code_line.split(":")
        var_part = parts[0].strip()
        # インデントを除去して変数名を取得
        var_name = var_part.split()[-1].strip()
        # カンマやカッコを除去
        var_name = var_name.rstrip(",)")
        if var_name and var_name not in ("self", "cls"):
            return var_name

    # パターン3: 代入文(var_name = value)
    if "=" in code_line and "def " not in code_line:
        parts = code_line.split("=")
        var_part = parts[0].strip()
        var_name = var_part.split()[-1].strip()
        var_name = var_name.rstrip(",)")
        if var_name:
            return var_name

    # デフォルト
    return "value"


def generate_detailed_improvement_plan(
    var_name: str,
    primitive_type: str,
    file_path: str,
    line_number: int,
    code_line: str,
) -> str:
    """詳細な改善プラン（テンプレートベース）を生成

    Args:
        var_name: 変数名
        primitive_type: primitive型
        file_path: ファイルパス
        line_number: 行番号
        code_line: コード行

    Returns:
        詳細な改善プラン（マークダウン形式）
    """
    # 型名候補を取得
    type_candidates = suggest_type_name(var_name, primitive_type)
    primary_type_name = type_candidates[0] if type_candidates else "CustomType"

    # バリデーションパターンを取得
    validation_patterns = suggest_validation_patterns(var_name, primitive_type)

    # Pydantic型の推奨があるかチェック
    pydantic_type = suggest_pydantic_type(var_name, primitive_type)

    plan_sections = []

    # Step 1: 型定義の作成
    plan_sections.append(
        f"""**Step 1: src/core/schemas/types.py に型定義を作成**

型名の候補（コードから推測）:
  {", ".join(type_candidates)}"""
    )

    if pydantic_type:
        # Pydantic型がある場合
        plan_sections.append(
            f"""
推奨: Pydantic提供の {pydantic_type["type"]} を使用
  {pydantic_type["import"]}
  {pydantic_type["example"]}

または、カスタム型として定義:"""
        )

    # Level 1の例
    plan_sections.append(
        f"""
Level 1: 単純な型エイリアス
```python
type {primary_type_name} = {primitive_type}
```"""
    )

    # Level 2の例（バリデーション付き）
    if validation_patterns:
        validator_example = VALIDATION_PATTERNS[validation_patterns[0]]["validator"]
        plan_sections.append(
            f"""
Level 2: 制約付き型（推奨）
```python
from typing import Annotated
from pydantic import AfterValidator

{validator_example}

type {primary_type_name} = Annotated[
    {primitive_type}, AfterValidator(validate_{var_name})
]
```"""
        )
    else:
        plan_sections.append(
            f"""
Level 2: 制約付き型（推奨）
```python
from typing import Annotated
from pydantic import AfterValidator

def validate_{var_name}(v: {primitive_type}) -> {primitive_type}:
    # 適切なバリデーションを追加
    if not v:  # 例: 空チェック
        raise ValueError("{primary_type_name}は空にできません")
    return v

type {primary_type_name} = Annotated[
    {primitive_type}, AfterValidator(validate_{var_name})
]
```"""
        )

    # Step 2: 使用箇所の修正
    fixed_code = code_line.replace(f": {primitive_type}", f": {primary_type_name}")
    plan_sections.append(
        f"""
**Step 2: 使用箇所を修正**

File: {file_path}

インポート追加:
```python
from src.core.schemas.types import {primary_type_name}
```

Before (line {line_number}):
```python
{code_line.strip()}
```

After:
```python
{fixed_code.strip()}
```"""
    )

    # Step 3: バリデーションの検討
    checklist = format_validation_checklist(primitive_type)
    plan_sections.append(
        f"""
**Step 3: バリデーションの検討**

この型に必要な制約を検討してください:
  {checklist}"""
    )

    # Implementation Context
    plan_sections.append(
        f"""
**Implementation Context:**
  - Why: primitive型の直接使用は型の意図を不明確にします
  - Effect: 型名により「何の{primitive_type}か」が明確になります
  - Impact: {primary_type_name}を使う全ての箇所で型安全性が向上します"""
    )

    # Tools and References
    plan_sections.append(
        """
**Tools and References:**
  - Pydantic AfterValidator - バリデーション実装
  - typing.Annotated - 型制約の追加
  - docs/typing-rule.md - 型定義ルール
  - src/core/schemas/types.py - 既存の型定義例"""
    )

    # Related Files
    plan_sections.append(
        f"""
**Related Files:**
  - {file_path}:{line_number} - 修正対象
  - src/core/schemas/types.py - 型定義を追加"""
    )

    return "\n".join(plan_sections)
