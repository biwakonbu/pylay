"""
改善プランテンプレート

型定義の品質改善のための具体的なテンプレートとヒューリスティックを提供します。
"""

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


def suggest_type_name(var_name: str, primitive_type: str) -> list[str]:
    """変数名とprimitive型から型名候補を推測

    Args:
        var_name: 変数名（例: "user_id", "email_address"）
        primitive_type: primitive型（例: "str", "int"）

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
        "[ ] 形式チェック（識別子、メール、URL など）",
        "[ ] 長さ制限",
        "[ ] 許可リスト/拒否リスト",
        "[ ] 既存データとの整合性チェック",
    ]

    if primitive_type == "int":
        int_checks = [
            "[ ] 範囲チェック（最小値・最大値）",
            "[ ] 正の整数チェック",
            "[ ] 非負整数チェック",
        ]
        return "\n  ".join(int_checks)

    return "\n  ".join(common_checks)


def extract_variable_name(code_line: str) -> str:
    """コード行から変数名を抽出

    Args:
        code_line: コード行（例: "type_name: str = type_def.name"）

    Returns:
        抽出された変数名（例: "type_name"）
    """
    # パターン1: 変数アノテーション（var_name: type）
    if ":" in code_line:
        parts = code_line.split(":")
        var_part = parts[0].strip()
        # 関数定義の場合はスキップ
        if "def " in var_part:
            return "value"
        # インデントを除去して変数名を取得
        var_name = var_part.split()[-1].strip()
        return var_name

    # パターン2: 代入文（var_name = value）
    if "=" in code_line and "def " not in code_line:
        parts = code_line.split("=")
        var_part = parts[0].strip()
        var_name = var_part.split()[-1].strip()
        return var_name

    # デフォルト
    return "value"
