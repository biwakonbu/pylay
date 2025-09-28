"""Base classes for document generators."""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from .filesystem import FileSystemInterface, RealFileSystem
from .markdown_builder import MarkdownBuilder


class DocumentGenerator(ABC):
    """Abstract base class for document generators."""

    def __init__(
        self,
        filesystem: FileSystemInterface | None = None,
        markdown_builder: MarkdownBuilder | None = None,
    ) -> None:
        """Initialize document generator with dependencies.

        Args:
            filesystem: File system interface for dependency injection
            markdown_builder: Markdown builder for content generation
        """
        self.fs = filesystem or RealFileSystem()
        self.md = markdown_builder or MarkdownBuilder()

    @abstractmethod
    def generate(self, output_path: Path, **kwargs: object) -> None:
        """Generate documentation.

        Args:
            output_path: Path where documentation should be written
            **kwargs: Additional configuration parameters
        """
        ...

    def _ensure_output_directory(self, output_path: Path) -> None:
        """Ensure output directory exists."""
        if output_path.suffix:  # It's a file path
            directory = output_path.parent
        else:  # It's a directory path
            directory = output_path

        self.fs.mkdir(directory, parents=True, exist_ok=True)

    def _write_file(self, path: Path, content: str) -> None:
        """Write content to file with proper directory creation."""
        self._ensure_output_directory(path)
        self.fs.write_text(path, content)

    def _format_timestamp(self, dt: datetime | None = None) -> str:
        """Format timestamp in ISO format."""
        if dt is None:
            dt = datetime.now()
        return dt.isoformat()

    def _format_generation_footer(self, additional_info: str = "") -> str:
        """Format standard generation footer."""
        timestamp = self._format_timestamp()
        footer = f"**生成日**: {timestamp}\n"
        if additional_info:
            footer += f"\n{additional_info}\n"
        return footer
