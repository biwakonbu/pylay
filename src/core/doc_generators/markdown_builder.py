"""Markdownドキュメント生成のための流暢なAPIを提供するビルダー

Markdownドキュメントを簡単に生成するためのBuilderパターン実装です。
"""

from typing import Self


class MarkdownBuilder:
    """Markdownドキュメント構築のための流暢なAPI

    メソッドチェーンを使用してMarkdownドキュメントを簡単に構築できます。
    """

    def __init__(self) -> None:
        """空のMarkdownビルダーを初期化

        空のMarkdownビルダーを初期化し、コンテンツリストを準備します。
        """
        self._content: list[str] = []

    def heading(self, level: int, text: str) -> Self:
        """指定されたレベル（1-6）の見出しを追加する。"""
        if not 1 <= level <= 6:
            raise ValueError(f"Heading level must be 1-6, got {level}")
        prefix = "#" * level
        self._content.append(f"{prefix} {text}\n")
        return self

    def paragraph(self, text: str) -> Self:
        """段落テキストを追加する。"""
        self._content.append(f"{text}\n")
        return self

    def line_break(self) -> Self:
        """改行を追加する。"""
        self._content.append("\n")
        return self

    def code_block(self, language: str, code: str) -> Self:
        """構文ハイライト付きのコードブロックを追加する。"""
        self._content.append(f"```{language}\n{code}\n```\n")
        return self

    def code_inline(self, code: str) -> Self:
        """インラインコードを追加する。"""
        self._content.append(f"`{code}`")
        return self

    def bullet_point(self, text: str, level: int = 1) -> Self:
        """オプションのインデントレベル付きの箇点リスト項目を追加する。"""
        indent = "  " * (level - 1)
        self._content.append(f"{indent}- {text}\n")
        return self

    def numbered_list(self, text: str, number: int = 1, level: int = 1) -> Self:
        """番号付きリスト項目を追加する。"""
        indent = "  " * (level - 1)
        self._content.append(f"{indent}{number}. {text}\n")
        return self

    def bold(self, text: str) -> str:
        """太字フォーマットのテキストを返す。"""
        return f"**{text}**"

    def italic(self, text: str) -> str:
        """斜体フォーマットのテキストを返す。"""
        return f"*{text}*"

    def link(self, text: str, url: str) -> str:
        """リンクフォーマットのテキストを返す。"""
        return f"[{text}]({url})"

    def table_header(self, headers: list[str]) -> Self:
        """テーブルヘッダー行を追加する。"""
        header_row = "| " + " | ".join(headers) + " |"
        separator_row = "| " + " | ".join("---" for _ in headers) + " |"
        self._content.extend([header_row + "\n", separator_row + "\n"])
        return self

    def table_row(self, cells: list[str]) -> Self:
        """テーブルデータ行を追加する。"""
        row = "| " + " | ".join(cells) + " |"
        self._content.append(row + "\n")
        return self

    def horizontal_rule(self) -> Self:
        """水平線を追加する。"""
        self._content.append("---\n")
        return self

    def blockquote(self, text: str) -> Self:
        """引用ブロックを追加する。"""
        lines = text.split("\n")
        for line in lines:
            self._content.append(f"> {line}\n")
        return self

    def raw(self, content: str) -> Self:
        """フォーマットなしで生コンテンツを追加する。"""
        self._content.append(content)
        return self

    def build(self) -> str:
        """最終的なMarkdownコンテンツを構築して返す。"""
        return "".join(self._content)

    def clear(self) -> Self:
        """すべてのコンテンツをクリアする。"""
        self._content.clear()
        return self

    def __str__(self) -> str:
        """現在のコンテンツを文字列として返す。"""
        return self.build()
