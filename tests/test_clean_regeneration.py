"""クリーン再生成機能のテスト

Issue #51: 古い .lay.* ファイルの自動削除機能
"""

from pathlib import Path

from src.core.converters.clean_regeneration import (
    clean_lay_files,
    clean_lay_files_recursive,
    is_lay_generated_file,
)


class TestIsLayGeneratedFile:
    """pylayが生成したファイルかどうかの判定テスト"""

    def test_detect_lay_generated_python_file(self, tmp_path: Path) -> None:
        """pylayが生成した.lay.pyファイルを検出できることを確認"""
        lay_file = tmp_path / "test.lay.py"
        lay_file.write_text(
            '"""\n'
            "====================================\n"
            "pylay自動生成ファイル\n"
            "このファイルを直接編集しないでください\n"
            '====================================\n"""'
        )

        assert is_lay_generated_file(lay_file) is True

    def test_detect_lay_generated_yaml_file(self, tmp_path: Path) -> None:
        """pylayが生成した.lay.yamlファイルを検出できることを確認"""
        lay_file = tmp_path / "test.lay.yaml"
        lay_file.write_text(
            "# ====================================\n"
            "# pylay自動生成ファイル\n"
            "# このファイルを直接編集しないでください\n"
            "# ===================================="
        )

        assert is_lay_generated_file(lay_file) is True

    def test_manual_file_is_not_detected(self, tmp_path: Path) -> None:
        """手動実装ファイルは検出されないことを確認"""
        manual_file = tmp_path / "models.py"
        manual_file.write_text("# Manual implementation\nclass User:\n    pass")

        assert is_lay_generated_file(manual_file) is False

    def test_nonexistent_file_returns_false(self, tmp_path: Path) -> None:
        """存在しないファイルはFalseを返すことを確認"""
        nonexistent = tmp_path / "nonexistent.py"

        assert is_lay_generated_file(nonexistent) is False


class TestCleanLayFiles:
    """ディレクトリ内の.lay.pyファイル削除テスト"""

    def test_delete_lay_py_files(self, tmp_path: Path) -> None:
        """ディレクトリ内の.lay.pyファイルが削除されることを確認"""
        # .lay.pyファイルを作成
        lay_file1 = tmp_path / "types1.lay.py"
        lay_file2 = tmp_path / "types2.lay.py"

        for lay_file in [lay_file1, lay_file2]:
            lay_file.write_text(
                '"""\npylay自動生成ファイル\nこのファイルを直接編集しないでください\n"""'
            )

        # 削除実行
        deleted = clean_lay_files(tmp_path, ".lay.py")

        assert len(deleted) == 2
        assert not lay_file1.exists()
        assert not lay_file2.exists()

    def test_manual_files_are_not_deleted(self, tmp_path: Path) -> None:
        """手動実装ファイルは削除されないことを確認"""
        # .lay.pyファイルと手動ファイルを作成
        lay_file = tmp_path / "types.lay.py"
        lay_file.write_text(
            '"""\npylay自動生成ファイル\nこのファイルを直接編集しないでください\n"""'
        )

        manual_file = tmp_path / "models.py"
        manual_file.write_text("# Manual implementation")

        # 削除実行
        deleted = clean_lay_files(tmp_path, ".lay.py")

        assert len(deleted) == 1
        assert not lay_file.exists()
        assert manual_file.exists()

    def test_delete_lay_yaml_files(self, tmp_path: Path) -> None:
        """ディレクトリ内の.lay.yamlファイルが削除されることを確認"""
        # .lay.yamlファイルを作成
        lay_file1 = tmp_path / "types1.lay.yaml"
        lay_file2 = tmp_path / "types2.lay.yaml"

        for lay_file in [lay_file1, lay_file2]:
            lay_file.write_text(
                "# pylay自動生成ファイル\n# このファイルを直接編集しないでください"
            )

        # 削除実行
        deleted = clean_lay_files(tmp_path, ".lay.yaml")

        assert len(deleted) == 2
        assert not lay_file1.exists()
        assert not lay_file2.exists()

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        """存在しないディレクトリの場合は空リストを返すことを確認"""
        nonexistent = tmp_path / "nonexistent"

        deleted = clean_lay_files(nonexistent, ".lay.py")

        assert deleted == []


class TestCleanLayFilesRecursive:
    """再帰的な.lay.pyファイル削除テスト"""

    def test_delete_lay_py_files_recursively(self, tmp_path: Path) -> None:
        """サブディレクトリ含めて.lay.pyファイルが削除されることを確認"""
        # ディレクトリ構造を作成
        subdir1 = tmp_path / "subdir1"
        subdir2 = tmp_path / "subdir2"
        subdir1.mkdir()
        subdir2.mkdir()

        # .lay.pyファイルを作成
        lay_file1 = tmp_path / "types1.lay.py"
        lay_file2 = subdir1 / "types2.lay.py"
        lay_file3 = subdir2 / "types3.lay.py"

        for lay_file in [lay_file1, lay_file2, lay_file3]:
            lay_file.write_text(
                '"""\npylay自動生成ファイル\nこのファイルを直接編集しないでください\n"""'
            )

        # 削除実行
        deleted = clean_lay_files_recursive(tmp_path, ".lay.py")

        assert len(deleted) == 3
        assert not lay_file1.exists()
        assert not lay_file2.exists()
        assert not lay_file3.exists()

    def test_manual_files_are_preserved_recursively(self, tmp_path: Path) -> None:
        """再帰削除でも手動ファイルは保護されることを確認"""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # .lay.pyファイルと手動ファイルを作成
        lay_file = subdir / "types.lay.py"
        lay_file.write_text(
            '"""\npylay自動生成ファイル\nこのファイルを直接編集しないでください\n"""'
        )

        manual_file1 = tmp_path / "models.py"
        manual_file2 = subdir / "api.py"
        manual_file1.write_text("# Manual implementation")
        manual_file2.write_text("# Manual implementation")

        # 削除実行
        deleted = clean_lay_files_recursive(tmp_path, ".lay.py")

        assert len(deleted) == 1
        assert not lay_file.exists()
        assert manual_file1.exists()
        assert manual_file2.exists()
