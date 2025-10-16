"""ドキュメントジェネレーター用のファイルシステム抽象化。"""

from abc import abstractmethod
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class FileSystemInterface(Protocol):
    """依存性注入用の型安全なファイルシステムインターフェース。"""

    @abstractmethod
    def write_text(self, path: str | Path, content: str, encoding: str = "utf-8") -> None:
        """テキストコンテンツをファイルに書き込む。"""
        ...

    @abstractmethod
    def mkdir(self, path: str | Path, *, parents: bool = True, exist_ok: bool = True) -> None:
        """ディレクトリを作成する。"""
        ...

    @abstractmethod
    def exists(self, path: str | Path) -> bool:
        """パスが存在するかどうかを確認する。"""
        ...


class RealFileSystem:
    """実際のファイルシステム実装。"""

    def write_text(self, path: str | Path, content: str, encoding: str = "utf-8") -> None:
        """テキストコンテンツをファイルに書き込む。"""
        Path(path).write_text(content, encoding=encoding)

    def mkdir(self, path: str | Path, *, parents: bool = True, exist_ok: bool = True) -> None:
        """ディレクトリを作成する。"""
        Path(path).mkdir(parents=parents, exist_ok=exist_ok)

    def exists(self, path: str | Path) -> bool:
        """パスが存在するかどうかを確認する。"""
        return Path(path).exists()


class InMemoryFileSystem:
    """テスト用のインメモリファイルシステム。"""

    def __init__(self) -> None:
        """インメモリファイルシステムを初期化する。"""
        self.files: dict[Path, str] = {}
        self.directories: set[Path] = set()

    def write_text(self, path: str | Path, content: str, encoding: str = "utf-8") -> None:
        """テキストコンテンツをメモリに書き込む。"""
        # Ensure parent directories exist
        path_obj = Path(path)
        parent = path_obj.parent
        if parent != path_obj:  # Avoid infinite loop for root
            self.mkdir(parent)
        self.files[path_obj] = content

    def mkdir(self, path: str | Path, *, parents: bool = True, exist_ok: bool = True) -> None:
        """メモリ内にディレクトリを作成する。"""
        path_obj = Path(path)
        if path_obj in self.directories and not exist_ok:
            raise FileExistsError(f"Directory {path_obj} already exists")

        if parents:
            # Create all parent directories
            current = path_obj
            while current.parent != current:
                self.directories.add(current)
                current = current.parent
        else:
            self.directories.add(path_obj)

    def exists(self, path: str | Path) -> bool:
        """パスがメモリ内に存在するかどうかを確認する。"""
        path_obj = Path(path)
        return path_obj in self.files or path_obj in self.directories

    def get_content(self, path: Path) -> str:
        """ファイルコンテンツを取得する（テストヘルパー）。"""
        if path not in self.files:
            raise FileNotFoundError(f"File {path} not found")
        return self.files[path]

    def list_files(self) -> list[Path]:
        """すべてのファイルをリストする（テストヘルパー）。"""
        return list(self.files.keys())
