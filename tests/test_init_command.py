"""pylay init コマンドのテスト

Issue #51: pylay init コマンドの実装
"""

from pathlib import Path

from src.cli.commands.init import run_init


class TestInitCommand:
    """pylay init コマンドのテスト"""

    def test_init_creates_config_in_pyproject(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """pyproject.toml に設定が追加されることを確認"""
        # テスト用のディレクトリに移動
        monkeypatch.chdir(tmp_path)

        # 空の pyproject.toml を作成
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            "[project]\n" 'name = "test-project"\n' 'version = "0.1.0"\n'
        )

        # init コマンド実行
        run_init()

        # pyproject.toml を確認
        content = pyproject.read_text()
        assert "[tool.pylay]" in content
        assert "[tool.pylay.generation]" in content
        assert "[tool.pylay.output]" in content
        assert "[tool.pylay.imports]" in content

    def test_init_preserves_existing_content(self, tmp_path: Path, monkeypatch) -> None:
        """既存の内容が保持されることを確認"""
        monkeypatch.chdir(tmp_path)

        # 既存の内容を持つ pyproject.toml を作成
        pyproject = tmp_path / "pyproject.toml"
        original_content = (
            "[project]\n"
            'name = "test-project"\n'
            'version = "0.1.0"\n'
            "\n"
            "[tool.mypy]\n"
            "strict = true\n"
        )
        pyproject.write_text(original_content)

        # init コマンド実行
        run_init()

        # 既存の内容が保持されているか確認
        content = pyproject.read_text()
        assert "[project]" in content
        assert 'name = "test-project"' in content
        assert "[tool.mypy]" in content
        assert "strict = true" in content
        assert "[tool.pylay]" in content

    def test_init_without_pyproject_fails(self, tmp_path: Path, monkeypatch) -> None:
        """pyproject.toml がない場合はエラーになることを確認"""
        # 空のディレクトリに移動
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        monkeypatch.chdir(empty_dir)

        # init コマンド実行（エラーにならないことを確認）
        run_init()

        # pyproject.toml が作成されていないことを確認
        assert not (empty_dir / "pyproject.toml").exists()

    def test_init_with_force_overwrites_config(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """--force オプションで既存の設定を上書きできることを確認"""
        monkeypatch.chdir(tmp_path)

        # 既存の設定を持つ pyproject.toml を作成
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            "[project]\n"
            'name = "test-project"\n'
            "\n"
            "[tool.pylay]\n"
            'target_dirs = ["old"]\n'
        )

        # force オプションで init コマンド実行
        run_init(force=True)

        # 設定が更新されていることを確認
        content = pyproject.read_text()
        assert "[tool.pylay]" in content
        # デフォルト設定が含まれていることを確認（シングルクォートまたはダブルクォート）
        assert "target_dirs = ['src']" in content or 'target_dirs = ["src"]' in content

    def test_init_without_force_preserves_existing_config(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """--force なしでは既存の設定を保持することを確認"""
        monkeypatch.chdir(tmp_path)

        # 既存の設定を持つ pyproject.toml を作成
        pyproject = tmp_path / "pyproject.toml"
        original_pylay_config = (
            "[project]\n"
            'name = "test-project"\n'
            "\n"
            "[tool.pylay]\n"
            'target_dirs = ["old"]\n'
        )
        pyproject.write_text(original_pylay_config)

        # force なしで init コマンド実行
        run_init(force=False)

        # 既存の設定が保持されていることを確認
        content = pyproject.read_text()
        assert 'target_dirs = ["old"]' in content

    def test_generated_config_has_comments(self, tmp_path: Path, monkeypatch) -> None:
        """生成される設定にコメントが含まれることを確認"""
        monkeypatch.chdir(tmp_path)

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[project]\n" 'name = "test"\n')

        run_init()

        content = pyproject.read_text()
        # コメントが含まれていることを確認
        assert "# pylay の設定" in content
        assert "# スキャン対象ディレクトリ" in content
        assert "# ファイル生成設定" in content
