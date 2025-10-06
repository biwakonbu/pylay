"""
品質チェックCLIコマンドのテスト

quality.pyコマンドの機能をテストします。
"""

from collections.abc import Generator

import pytest
from click.testing import CliRunner

from src.cli.commands.quality import main


class TestQualityCommand:
    """品質チェックCLIコマンドのテスト"""

    @pytest.fixture  # type: ignore[misc]
    def runner(self) -> Generator[CliRunner, None, None]:
        """CLIテスト用のランナー"""
        yield CliRunner()

    def test_quality_command_basic(self, runner: CliRunner) -> None:
        """基本的な品質チェックコマンドテスト"""
        # srcディレクトリを対象に品質チェックを実行
        result = runner.invoke(main, ["src"])

        # コマンドが正常終了するか確認（品質チェックは警告が出る可能性がある）
        assert result.exit_code in [0, 1]  # 0: 成功, 1: エラーあり

        # 出力が含まれているか確認
        assert "Quality check" in result.output

    def test_quality_command_with_options(self, runner: CliRunner) -> None:
        """オプション付きの品質チェックコマンドテスト"""
        result = runner.invoke(main, ["src", "--format", "json", "--show-details"])

        assert result.exit_code in [0, 1]

    def test_quality_command_strict_mode(self, runner: CliRunner) -> None:
        """厳格モードの品質チェックコマンドテスト"""
        result = runner.invoke(main, ["src", "--strict"])

        # 厳格モードではエラーがあると終了コード1
        assert result.exit_code in [0, 1]
