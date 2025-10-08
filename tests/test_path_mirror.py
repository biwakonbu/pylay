"""パッケージ構造ミラーリング機能のテスト

Issue #51: パッケージ構造をdocs/pylay/配下にミラーリング
"""

from pathlib import Path

from src.core.converters.path_mirror import (
    ensure_output_directory,
    find_project_root,
    mirror_package_path,
)


class TestMirrorPackagePath:
    """パッケージパスミラーリングのテスト"""

    def test_mirror_src_path_to_docs_pylay(self, tmp_path: Path) -> None:
        """src/ 配下のパスが docs/pylay/src/ にミラーリングされることを確認"""
        project_root = tmp_path
        input_path = project_root / "src" / "core" / "schemas" / "types.py"
        output_base = project_root / "docs" / "pylay"

        result = mirror_package_path(input_path, project_root, output_base, ".lay.yaml")

        expected = output_base / "src" / "core" / "schemas" / "types.lay.yaml"
        assert result == expected

    def test_mirror_with_lay_py_suffix(self, tmp_path: Path) -> None:
        """.lay.py 拡張子でミラーリングされることを確認"""
        project_root = tmp_path
        input_path = project_root / "src" / "models.yaml"
        output_base = project_root / "docs" / "pylay"

        result = mirror_package_path(input_path, project_root, output_base, ".lay.py")

        expected = output_base / "src" / "models.lay.py"
        assert result == expected

    def test_mirror_nested_package(self, tmp_path: Path) -> None:
        """深くネストしたパッケージが正しくミラーリングされることを確認"""
        project_root = tmp_path
        input_path = project_root / "src" / "a" / "b" / "c" / "d" / "e" / "module.py"
        output_base = project_root / "docs" / "pylay"

        result = mirror_package_path(input_path, project_root, output_base, ".lay.yaml")

        expected = output_base / "src" / "a" / "b" / "c" / "d" / "e" / "module.lay.yaml"
        assert result == expected

    def test_mirror_outside_project(self, tmp_path: Path) -> None:
        """プロジェクト外のファイルはファイル名のみ使用することを確認"""
        project_root = tmp_path / "project"
        project_root.mkdir()
        input_path = tmp_path / "outside" / "module.py"
        output_base = project_root / "docs" / "pylay"

        result = mirror_package_path(input_path, project_root, output_base, ".lay.yaml")

        expected = output_base / "module.lay.yaml"
        assert result == expected


class TestEnsureOutputDirectory:
    """出力ディレクトリ作成のテスト"""

    def test_create_nested_directory(self, tmp_path: Path) -> None:
        """ネストしたディレクトリが作成されることを確認"""
        output_path = tmp_path / "docs" / "pylay" / "src" / "core" / "types.lay.yaml"

        ensure_output_directory(output_path)

        assert output_path.parent.exists()
        assert output_path.parent.is_dir()

    def test_directory_already_exists(self, tmp_path: Path) -> None:
        """既存ディレクトリの場合もエラーにならないことを確認"""
        output_path = tmp_path / "existing" / "file.lay.yaml"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # エラーなく実行できることを確認
        ensure_output_directory(output_path)

        assert output_path.parent.exists()


class TestFindProjectRoot:
    """プロジェクトルート検索のテスト"""

    def test_find_project_root_from_nested_dir(self, tmp_path: Path) -> None:
        """ネストしたディレクトリからプロジェクトルートを検出できることを確認"""
        project_root = tmp_path / "project"
        nested_dir = project_root / "src" / "core" / "schemas"
        nested_dir.mkdir(parents=True)

        # pyproject.toml を作成
        pyproject = project_root / "pyproject.toml"
        pyproject.write_text("[tool.pylay]\n")

        result = find_project_root(nested_dir)

        assert result == project_root

    def test_find_project_root_from_root(self, tmp_path: Path) -> None:
        """ルートディレクトリから検索しても検出できることを確認"""
        project_root = tmp_path
        pyproject = project_root / "pyproject.toml"
        pyproject.write_text("[tool.pylay]\n")

        result = find_project_root(project_root)

        assert result == project_root

    def test_no_project_root_found(self, tmp_path: Path) -> None:
        """pyproject.tomlが見つからない場合はNoneを返すことを確認"""
        nested_dir = tmp_path / "src" / "core"
        nested_dir.mkdir(parents=True)

        result = find_project_root(nested_dir)

        assert result is None
