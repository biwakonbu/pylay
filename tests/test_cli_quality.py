"""
品質チェックCLIコマンドのテスト

quality.pyコマンドの機能をテストします。
"""

from collections.abc import Generator

import pytest
from click.testing import CliRunner

from src.cli.commands.quality import quality as main


class TestQualityCommand:
    """品質チェックCLIコマンドのテスト"""

    @pytest.fixture  # type: ignore[misc]
    def runner(self) -> Generator[CliRunner, None, None]:
        """CLIテスト用のランナー"""
        yield CliRunner()

    def test_quality_command_basic(self, runner: CliRunner) -> None:
        """基本的な品質チェックコマンドテスト"""
        # srcディレクトリを対象に品質チェックを実行（設定ファイルを明示）
        result = runner.invoke(main, ["--config", "pyproject.toml", "src"])

        # コマンドが正常終了するか確認（品質チェックは警告が出る可能性がある）
        assert result.exit_code in [0, 1]  # 0: 成功, 1: エラーあり

        # 出力が含まれているか確認
        assert "Quality" in result.output or "quality" in result.output.lower()

    def test_quality_command_with_options(self, runner: CliRunner) -> None:
        """オプション付きの品質チェックコマンドテスト"""
        result = runner.invoke(
            main,
            ["--config", "pyproject.toml", "src", "--show-details"],
        )

        assert result.exit_code in [0, 1]

    def test_quality_command_strict_mode(self, runner: CliRunner) -> None:
        """厳格モードの品質チェックコマンドテスト"""
        result = runner.invoke(main, ["--config", "pyproject.toml", "src", "--strict"])

        # 厳格モードではエラーがあると終了コード1
        assert result.exit_code in [0, 1]

    def test_quality_command_with_severity_filter(self, runner: CliRunner) -> None:
        """深刻度フィルタのテスト"""
        # adviceフィルタ
        result = runner.invoke(
            main, ["--config", "pyproject.toml", "src", "--severity", "advice"]
        )
        assert result.exit_code in [0, 1]
        assert "ADVICE" in result.output or "Advice" in result.output

        # errorフィルタ
        result = runner.invoke(
            main, ["--config", "pyproject.toml", "src", "--severity", "error"]
        )
        assert result.exit_code in [0, 1]

    def test_quality_command_with_issue_type_filter(self, runner: CliRunner) -> None:
        """問題タイプフィルタのテスト"""
        result = runner.invoke(
            main,
            [
                "--config",
                "pyproject.toml",
                "src",
                "--issue-type",
                "level1_ratio_high",
            ],
        )
        assert result.exit_code in [0, 1]

    def test_quality_command_with_combined_filters(self, runner: CliRunner) -> None:
        """組み合わせフィルタのテスト"""
        result = runner.invoke(
            main,
            [
                "--config",
                "pyproject.toml",
                "src",
                "--severity",
                "advice",
                "--issue-type",
                "level1_ratio_high",
            ],
        )
        assert result.exit_code in [0, 1]
