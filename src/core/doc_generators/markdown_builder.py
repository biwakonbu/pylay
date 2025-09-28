"""Markdown builder with fluent API for document generation."""

from typing import Self


class MarkdownBuilder:
    """Fluent API for building Markdown documents."""

    def __init__(self) -> None:
        """Initialize empty markdown builder."""
        self._content: list[str] = []

    def heading(self, level: int, text: str) -> Self:
        """Add heading with specified level (1-6)."""
        if not 1 <= level <= 6:
            raise ValueError(f"Heading level must be 1-6, got {level}")
        prefix = "#" * level
        self._content.append(f"{prefix} {text}\n")
        return self

    def paragraph(self, text: str) -> Self:
        """Add paragraph text."""
        self._content.append(f"{text}\n")
        return self

    def line_break(self) -> Self:
        """Add line break."""
        self._content.append("\n")
        return self

    def code_block(self, language: str, code: str) -> Self:
        """Add code block with syntax highlighting."""
        self._content.append(f"```{language}\n{code}\n```\n")
        return self

    def code_inline(self, code: str) -> Self:
        """Add inline code."""
        self._content.append(f"`{code}`")
        return self

    def bullet_point(self, text: str, level: int = 1) -> Self:
        """Add bullet point with optional indentation level."""
        indent = "  " * (level - 1)
        self._content.append(f"{indent}- {text}\n")
        return self

    def numbered_list(self, text: str, number: int = 1, level: int = 1) -> Self:
        """Add numbered list item."""
        indent = "  " * (level - 1)
        self._content.append(f"{indent}{number}. {text}\n")
        return self

    def bold(self, text: str) -> str:
        """Return bold-formatted text."""
        return f"**{text}**"

    def italic(self, text: str) -> str:
        """Return italic-formatted text."""
        return f"*{text}*"

    def link(self, text: str, url: str) -> str:
        """Return link-formatted text."""
        return f"[{text}]({url})"

    def table_header(self, headers: list[str]) -> Self:
        """Add table header row."""
        header_row = "| " + " | ".join(headers) + " |"
        separator_row = "| " + " | ".join("---" for _ in headers) + " |"
        self._content.extend([header_row + "\n", separator_row + "\n"])
        return self

    def table_row(self, cells: list[str]) -> Self:
        """Add table data row."""
        row = "| " + " | ".join(cells) + " |"
        self._content.append(row + "\n")
        return self

    def horizontal_rule(self) -> Self:
        """Add horizontal rule."""
        self._content.append("---\n")
        return self

    def blockquote(self, text: str) -> Self:
        """Add blockquote."""
        lines = text.split("\n")
        for line in lines:
            self._content.append(f"> {line}\n")
        return self

    def raw(self, content: str) -> Self:
        """Add raw content without formatting."""
        self._content.append(content)
        return self

    def build(self) -> str:
        """Build and return the final markdown content."""
        return "".join(self._content)

    def clear(self) -> Self:
        """Clear all content."""
        self._content.clear()
        return self

    def __str__(self) -> str:
        """Return current content as string."""
        return self.build()
