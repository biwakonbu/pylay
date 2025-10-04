"""
analyze-typesコマンドの詳細表示機能統合テスト

--show-details と --export-details オプションのテスト。
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import yaml
from click.testing import CliRunner

from src.cli.commands.analyze_types import analyze_types
from src.core.analyzer.type_level_models import TypeAnalysisReport, TypeStatistics


class TestAnalyzeTypesDetails:
    """analyze-typesコマンドの詳細表示機能テスト"""

    def setup_method(self):
        """テストセットアップ"""
        self.runner = CliRunner()

    @patch("src.cli.commands.analyze_types.TypeLevelAnalyzer")
    @patch("src.cli.commands.analyze_types._output_console_report")
    def test_show_details_option(self, mock_output_console, mock_analyzer_class):
        """--show-detailsオプションのテスト"""
        # モックアナライザーの設定
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer

        # モックレポートの設定
        mock_report = Mock(spec=TypeAnalysisReport)
        mock_report.statistics = Mock(spec=TypeStatistics)
        mock_report.type_definitions = []
        mock_analyzer.analyze_directory.return_value = mock_report

        # CLI実行
        result = self.runner.invoke(analyze_types, ["src", "--show-details"])

        # コマンドが正常終了することを確認
        assert result.exit_code == 0

        # _output_console_reportが正しい引数で呼ばれていることを確認
        mock_output_console.assert_called_once()
        args = mock_output_console.call_args[0]
        assert args[0] == mock_analyzer  # analyzer
        assert args[1] == mock_report  # report
        assert args[4] is True  # show_details
        assert args[5] is True  # show_stats (デフォルトTrue)
        assert args[6] == ["src"]  # target_dirs

    @patch("src.cli.commands.analyze_types._output_console_report")
    def test_no_stats_option(self, mock_output_console, mock_analyzer_class):
        """--no-statsオプションのテスト"""
        # モックアナライザーの設定
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer

        # モックレポートの設定
        mock_report = Mock(spec=TypeAnalysisReport)
        mock_report.statistics = Mock(spec=TypeStatistics)
        mock_report.type_definitions = []
        mock_analyzer.analyze_directory.return_value = mock_report

        # CLI実行
        result = self.runner.invoke(analyze_types, ["src", "--no-stats"])

        # コマンドが正常終了することを確認
        assert result.exit_code == 0

        # _output_console_reportが正しい引数で呼ばれていることを確認
        mock_output_console.assert_called_once()
        args = mock_output_console.call_args[0]
        assert args[0] == mock_analyzer  # analyzer
        assert args[1] == mock_report  # report
        assert args[4] is False  # show_details (デフォルトFalse)
        assert args[5] is False  # show_stats (False)
        assert args[6] == ["src"]  # target_dirs

    def test_export_details_yaml_structure(self):
        """YAMLエクスポートの構造テスト"""
        from src.cli.commands.analyze_types import _export_details_to_yaml

        # モックデータの作成
        mock_analyzer = Mock()
        mock_report = Mock()
        mock_report.type_definitions = []

        # 一時ファイルでテスト
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".yaml", delete=False
        ) as tmp_file:
            tmp_path = tmp_file.name

        try:
            # 実際の関数を呼び出し
            with patch(
                "src.core.analyzer.code_locator.CodeLocator"
            ) as mock_locator_class:
                mock_locator = Mock()
                mock_locator.find_primitive_usages.return_value = []
                mock_locator.find_level1_types.return_value = []
                mock_locator.find_unused_types.return_value = []
                mock_locator.find_deprecated_typing.return_value = []
                mock_locator_class.return_value = mock_locator

                _export_details_to_yaml(mock_analyzer, mock_report, tmp_path, ["src"])

                # 生成されたYAMLを読み込み
                with open(tmp_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                # 構造チェック
                assert "problem_details" in data
                assert isinstance(data["problem_details"], dict)

        finally:
            Path(tmp_path).unlink(missing_ok=True)


class TestExportDetailsToYaml:
    """YAMLエクスポート機能のテスト"""

    @patch("src.core.analyzer.code_locator.CodeLocator")
    def test_export_details_structure(self, mock_code_locator_class):
        """エクスポートされるYAML構造のテスト"""
        from src.cli.commands.analyze_types import _export_details_to_yaml

        # モックCodeLocatorの設定
        mock_locator = Mock()
        mock_code_locator_class.return_value = mock_locator

        # モック詳細データの設定
        mock_primitive_detail = Mock()
        mock_primitive_detail.location.file = Path("src/test.py")
        mock_primitive_detail.location.line = 10
        mock_primitive_detail.location.column = 5
        mock_primitive_detail.location.context_before = ["# comment"]
        mock_primitive_detail.location.code = "def func(user_id: str):"
        mock_primitive_detail.location.context_after = ["    pass"]
        mock_primitive_detail.kind = "function_argument"
        mock_primitive_detail.primitive_type = "str"
        mock_primitive_detail.function_name = "func"
        mock_primitive_detail.class_name = None

        mock_locator.find_primitive_usages.return_value = [mock_primitive_detail]
        mock_locator.find_level1_types.return_value = []
        mock_locator.find_unused_types.return_value = []
        mock_locator.find_deprecated_typing.return_value = []

        # モックアナライザーとレポート
        mock_analyzer = Mock()
        mock_report = Mock()
        mock_report.type_definitions = []

        # 一時ファイルでテスト
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".yaml", delete=False
        ) as tmp_file:
            tmp_path = tmp_file.name

        try:
            _export_details_to_yaml(mock_analyzer, mock_report, tmp_path, ["src"])

            # 生成されたYAMLを読み込み
            with open(tmp_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            # 構造チェック
            assert "problem_details" in data
            assert "primitive_usage" in data["problem_details"]
            assert len(data["problem_details"]["primitive_usage"]) == 1

            usage = data["problem_details"]["primitive_usage"][0]
            assert usage["file"] == "src/test.py"
            assert usage["line"] == 10
            assert usage["type"] == "function_argument"
            assert usage["primitive_type"] == "str"
            assert "context" in usage
            assert "suggestion" in usage

        finally:
            Path(tmp_path).unlink(missing_ok=True)


class TestConsoleReportDetails:
    """コンソールレポートの詳細表示機能テスト"""

    @patch("src.core.analyzer.type_reporter.TypeReporter")
    def test_output_console_report_with_details(self, mock_reporter_class):
        """詳細表示付きコンソールレポートのテスト"""
        from src.cli.commands.analyze_types import _output_console_report

        # モックreporterの設定
        mock_reporter = Mock()
        mock_reporter_class.return_value = mock_reporter

        # モックアナライザーとレポート
        mock_analyzer = Mock()
        mock_report = Mock()

        # テスト実行
        _output_console_report(
            mock_analyzer, mock_report, False, False, True, True, ["src"]
        )

        # TypeReporterが正しい引数で初期化されていることを確認
        mock_reporter_class.assert_called_once_with(target_dirs=[Path("src")])

        # generate_detailed_reportが呼ばれていることを確認
        mock_reporter.generate_detailed_report.assert_called_once_with(
            mock_report, True, True
        )

    @patch("src.core.analyzer.type_reporter.TypeReporter")
    def test_output_console_report_without_details(self, mock_reporter_class):
        """詳細表示なしのコンソールレポートのテスト"""
        from src.cli.commands.analyze_types import _output_console_report

        # モックreporterの設定
        mock_reporter = Mock()
        mock_reporter_class.return_value = mock_reporter

        # モックアナライザーとレポート
        mock_analyzer = Mock()
        mock_report = Mock()

        # テスト実行（show_details=False）
        _output_console_report(
            mock_analyzer, mock_report, False, False, False, True, ["src"]
        )

        # generate_detailed_reportがFalseで呼ばれていることを確認
        mock_reporter.generate_detailed_report.assert_called_once_with(
            mock_report, False, True
        )
