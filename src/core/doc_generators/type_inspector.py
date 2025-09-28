"""Type inspection utilities for type documentation generation."""

import inspect
import json
from typing import Any, get_args, get_origin

from pydantic import BaseModel


class TypeInspector:
    """Utility class for extracting information from types."""

    def __init__(self, skip_types: set[str] | None = None) -> None:
        """Initialize type inspector.

        Args:
            skip_types: Set of type names to skip during inspection
        """
        self.skip_types = skip_types or {"NewType"}

    def get_docstring(self, type_cls: type[Any]) -> str | None:
        """Get docstring from a type class.

        Args:
            type_cls: Type class to inspect

        Returns:
            Docstring if available, None otherwise
        """
        return inspect.getdoc(type_cls)

    def extract_code_blocks(self, docstring: str) -> tuple[list[str], list[str]]:
        """Extract description lines and code blocks from docstring.

        Args:
            docstring: Raw docstring content

        Returns:
            Tuple of (description_lines, code_blocks)
        """
        lines = docstring.split("\n")
        description_lines = []
        code_blocks = []
        in_code_block = False
        current_code: list[str] = []

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
        """Get type origin and args.

        Args:
            type_cls: Type class to inspect

        Returns:
            Tuple of (origin, args)
        """
        return get_origin(type_cls), get_args(type_cls)

    def is_pydantic_model(self, type_cls: type[Any]) -> bool:
        """Check if type is a Pydantic model.

        Args:
            type_cls: Type class to check

        Returns:
            True if it's a Pydantic BaseModel, False otherwise
        """
        return (
            hasattr(type_cls, "model_json_schema")
            and isinstance(type_cls, type)
            and issubclass(type_cls, BaseModel)
        )

    def is_newtype(self, type_cls: type[Any]) -> bool:
        """Check if type is a NewType.

        Args:
            type_cls: Type class to check

        Returns:
            True if it's a NewType, False otherwise
        """
        return hasattr(type_cls, "__supertype__")

    def get_newtype_supertype(self, type_cls: type[Any]) -> type[Any] | None:
        """Get NewType supertype.

        Args:
            type_cls: NewType class

        Returns:
            Supertype if available, None otherwise
        """
        return getattr(type_cls, "__supertype__", None)

    def get_pydantic_schema(self, type_cls: type[Any]) -> dict[str, Any] | None:
        """Get Pydantic JSON schema.

        Args:
            type_cls: Pydantic model class

        Returns:
            JSON schema if available, None otherwise
        """
        if not self.is_pydantic_model(type_cls):
            return None

        try:
            return type_cls.model_json_schema()  # type: ignore[no-any-return]
        except Exception:
            # Handle any schema generation errors
            return None

    def is_standard_newtype_doc(self, docstring: str) -> bool:
        """Check if docstring is the standard NewType documentation.

        Args:
            docstring: Docstring to check

        Returns:
            True if it's standard NewType documentation
        """
        return (
            "NewType creates simple unique types" in docstring
            or "Usage:: UserId = NewType" in docstring
        )

    def should_skip_type(self, type_name: str) -> bool:
        """Check if type should be skipped.

        Args:
            type_name: Name of the type

        Returns:
            True if type should be skipped
        """
        return type_name in self.skip_types

    def format_type_definition(self, name: str, type_cls: type[Any]) -> str:
        """Format type definition for documentation.

        Args:
            name: Type name
            type_cls: Type class

        Returns:
            Formatted type definition string
        """
        if self.is_pydantic_model(type_cls):
            schema = self.get_pydantic_schema(type_cls)
            if schema:
                return (
                    f"```json\n{json.dumps(schema, indent=2, ensure_ascii=False)}\n```"
                )

        if self.is_newtype(type_cls):
            supertype = self.get_newtype_supertype(type_cls)
            if supertype and hasattr(supertype, "__name__"):
                return f"```python\nNewType('{name}', {supertype.__name__})\n```"
            else:
                return f"```python\nNewType('{name}', {str(supertype)})\n```"

        origin, args = self.get_type_origin(type_cls)
        if origin is not None:
            # TypeAlias
            if hasattr(origin, "__name__"):
                return f"```python\nTypeAlias('{name}', {origin.__name__})\n```"
            else:
                return f"```python\nTypeAlias('{name}', {origin})\n```"

        # Fallback
        return f"```python\n{name} (型情報: {type_cls})\n```"
