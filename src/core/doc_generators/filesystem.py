"""File system abstraction for document generators."""

from abc import abstractmethod
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class FileSystemInterface(Protocol):
    """Type-safe file system interface for dependency injection."""

    @abstractmethod
    def write_text(self, path: Path, content: str, encoding: str = "utf-8") -> None:
        """Write text content to a file."""
        ...

    @abstractmethod
    def mkdir(self, path: Path, parents: bool = True, exist_ok: bool = True) -> None:
        """Create directory."""
        ...

    @abstractmethod
    def exists(self, path: Path) -> bool:
        """Check if path exists."""
        ...


class RealFileSystem:
    """Real file system implementation."""

    def write_text(self, path: Path, content: str, encoding: str = "utf-8") -> None:
        """Write text content to a file."""
        path.write_text(content, encoding=encoding)

    def mkdir(self, path: Path, parents: bool = True, exist_ok: bool = True) -> None:
        """Create directory."""
        path.mkdir(parents=parents, exist_ok=exist_ok)

    def exists(self, path: Path) -> bool:
        """Check if path exists."""
        return path.exists()


class InMemoryFileSystem:
    """In-memory file system for testing."""

    def __init__(self) -> None:
        """Initialize in-memory file system."""
        self.files: dict[Path, str] = {}
        self.directories: set[Path] = set()

    def write_text(self, path: Path, content: str, encoding: str = "utf-8") -> None:
        """Write text content to memory."""
        # Ensure parent directories exist
        parent = path.parent
        if parent != path:  # Avoid infinite loop for root
            self.mkdir(parent)
        self.files[path] = content

    def mkdir(self, path: Path, parents: bool = True, exist_ok: bool = True) -> None:
        """Create directory in memory."""
        if path in self.directories and not exist_ok:
            raise FileExistsError(f"Directory {path} already exists")

        if parents:
            # Create all parent directories
            current = path
            while current.parent != current:
                self.directories.add(current)
                current = current.parent
        else:
            self.directories.add(path)

    def exists(self, path: Path) -> bool:
        """Check if path exists in memory."""
        return path in self.files or path in self.directories

    def get_content(self, path: Path) -> str:
        """Get file content (test helper)."""
        if path not in self.files:
            raise FileNotFoundError(f"File {path} not found")
        return self.files[path]

    def list_files(self) -> list[Path]:
        """List all files (test helper)."""
        return list(self.files.keys())
