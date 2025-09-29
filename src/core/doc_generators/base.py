"""ドキュメントジェネレーターの基底クラス。"""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from .filesystem import FileSystemInterface, RealFileSystem
from .markdown_builder import MarkdownBuilder


class DocumentGenerator(ABC):
    """ドキュメントジェネレーターの抽象基底クラス。"""

    def __init__(
        self,
        filesystem: FileSystemInterface | None = None,
        markdown_builder: MarkdownBuilder | None = None,
    ) -> None:
        """依存関係を注入してドキュメントジェネレーターを初期化する。

        Args:
            filesystem: 依存性注入用のファイルシステムインターフェース
            markdown_builder: コンテンツ生成用のMarkdownビルダー
        """
        self.fs = filesystem or RealFileSystem()
        self.md = markdown_builder or MarkdownBuilder()

    @abstractmethod
    def generate(self, output_path: Path, **kwargs: object) -> None:
        """ドキュメントを生成する。

        Args:
            output_path: ドキュメントの書き込み先パス
            **kwargs: 追加の設定パラメータ
        """
        ...

    def _ensure_output_directory(self, output_path: Path) -> None:
        """出力ディレクトリが存在することを確認する。"""
        if output_path.suffix:  # It's a file path
            directory = output_path.parent
        else:  # It's a directory path
            directory = output_path

        self.fs.mkdir(directory, parents=True, exist_ok=True)

    def _write_file(self, path: Path, content: str) -> None:
        """適切なディレクトリ作成を行ってファイルにコンテンツを書き込む。"""
        self._ensure_output_directory(path)
        self.fs.write_text(path, content)

    def _format_timestamp(self, dt: datetime | None = None) -> str:
        """タイムスタンプをISO形式でフォーマットする。"""
        if dt is None:
            dt = datetime.now()
        return dt.isoformat()

    def _format_generation_footer(self, additional_info: str = "") -> str:
        """標準的な生成フッターをフォーマットする。"""
        timestamp = self._format_timestamp()
        footer = f"**生成日**: {timestamp}\n"
        if additional_info:
            footer += f"\n{additional_info}\n"
        return footer
