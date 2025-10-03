"""型ドキュメント生成用の型検査ユーティリティ。"""

import inspect
import json
from typing import Any, get_args, get_origin

from pydantic import BaseModel

from src.core.schemas.types import CodeLineList, SkipTypeSet


class TypeInspector:
    """型から情報を抽出するためのユーティリティクラス。"""

    def __init__(self, skip_types: SkipTypeSet | None = None) -> None:
        """型検査器を初期化する。

        Args:
            skip_types: 検査時にスキップする型名のセット
        """
        self.skip_types = skip_types or set()

    def get_docstring(self, type_cls: type[Any]) -> str | None:
        """型クラスからdocstringを取得する。

        Args:
            type_cls: 検査する型クラス

        Returns:
            docstringが存在する場合はその内容、存在しない場合はNone
        """
        return inspect.getdoc(type_cls)

    def extract_code_blocks(self, docstring: str) -> tuple[list[str], list[str]]:
        """docstringから説明文行とコードブロックを抽出する。

        Args:
            docstring: 生のdocstring内容

        Returns:
            (説明文行のリスト, コードブロックのリスト) のタプル
        """
        lines = docstring.split("\n")
        description_lines = []
        code_blocks = []
        in_code_block = False
        current_code: CodeLineList = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("```"):
                if in_code_block:
                    # Code block end
                    code_blocks.append("\n".join(current_code))
                    current_code = []
                    in_code_block = False
                else:
                    # Code block start
                    in_code_block = True
            elif in_code_block:
                current_code.append(line)
            else:
                description_lines.append(line)

        return description_lines, code_blocks

    def get_type_origin(self, type_cls: type[Any]) -> tuple[Any, tuple[Any, ...]]:
        """型のoriginとargsを取得する。

        Args:
            type_cls: 検査する型クラス

        Returns:
            (origin, args) のタプル
        """
        return get_origin(type_cls), get_args(type_cls)

    def is_pydantic_model(self, type_cls: type[Any]) -> bool:
        """型がPydanticモデルかどうかを確認する。

        Args:
            type_cls: 確認する型クラス

        Returns:
            Pydantic BaseModelの場合はTrue、それ以外の場合はFalse
        """
        return (
            hasattr(type_cls, "model_json_schema")
            and isinstance(type_cls, type)
            and issubclass(type_cls, BaseModel)
        )

    def get_pydantic_schema(self, type_cls: type[Any]) -> dict[str, Any] | None:
        """Pydantic JSONスキーマを取得する。

        Args:
            type_cls: Pydanticモデルクラス

        Returns:
            JSONスキーマが存在する場合はその内容、存在しない場合はNone
        """
        if not self.is_pydantic_model(type_cls):
            return None

        try:
            return type_cls.model_json_schema()  # type: ignore[no-any-return]
        except Exception:
            # Handle any schema generation errors
            return None

    def should_skip_type(self, type_name: str) -> bool:
        """型をスキップすべきかどうかを確認する。

        Args:
            type_name: 型の名前

        Returns:
            型をスキップすべき場合はTrue
        """
        return type_name in self.skip_types

    def format_type_definition(self, name: str, type_cls: type[Any]) -> str:
        """ドキュメント用の型定義をフォーマットする。

        Args:
            name: 型名
            type_cls: 型クラス

        Returns:
            フォーマットされた型定義文字列
        """
        if self.is_pydantic_model(type_cls):
            schema = self.get_pydantic_schema(type_cls)
            if schema:
                return (
                    f"```json\n{json.dumps(schema, indent=2, ensure_ascii=False)}\n```"
                )

        origin, _args = self.get_type_origin(type_cls)
        if origin is not None:
            # TypeAlias
            if hasattr(origin, "__name__"):
                return f"```python\nTypeAlias('{name}', {origin.__name__})\n```"
            else:
                return f"```python\nTypeAlias('{name}', {origin})\n```"

        # Fallback
        return f"```python\n{name} (型情報: {type_cls})\n```"
