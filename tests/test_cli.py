"""CLI 機能のテスト"""

from click.testing import CliRunner

from src.cli.main import cli


class TestCLI:
    """CLIコマンドのテスト"""

    def test_cli_help(self):
        """CLIのヘルプが表示されることを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "pylay: 型解析、自動型生成、ドキュメント生成ツール" in result.stdout

    def test_generate_help(self):
        """generateコマンドのヘルプが表示されることを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ["generate", "--help"])
        assert result.exit_code == 0
        assert "ドキュメント/型生成コマンド" in result.stdout

    def test_analyze_help(self):
        """analyzeコマンドのヘルプが表示されることを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "--help"])
        assert result.exit_code == 0
        assert "静的解析コマンド" in result.stdout

    def test_convert_help(self):
        """convertコマンドのヘルプが表示されることを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ["convert", "--help"])
        assert result.exit_code == 0
        assert "型と YAML の相互変換" in result.stdout

    def test_generate_type_docs_help(self):
        """generate type-docsコマンドのヘルプが表示されることを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ["generate", "type-docs", "--help"])
        assert result.exit_code == 0
        assert "Python 型から Markdown ドキュメントを生成" in result.stdout

    def test_analyze_types_help(self):
        """analyze typesコマンドのヘルプが表示されることを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "types", "--help"])
        assert result.exit_code == 0
        assert "モジュールから型を解析" in result.stdout

    def test_convert_to_yaml_help(self):
        """convert to-yamlコマンドのヘルプが表示されることを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ["convert", "to-yaml", "--help"])
        assert result.exit_code == 0
        assert "Python 型を YAML に変換" in result.stdout

    def test_convert_to_type_help(self):
        """convert to-typeコマンドのヘルプが表示されることを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ["convert", "to-type", "--help"])
        assert result.exit_code == 0
        assert "YAML を Pydantic BaseModel に変換" in result.stdout

    def test_cli_version(self):
        """CLIのバージョン情報が表示されることを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        # バージョン情報が表示されることを確認（実際のバージョンはpyproject.tomlによる）

    def test_generate_type_docs_with_invalid_input(self):
        """無効な入力ファイルでエラーが発生することを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ["generate", "type-docs", "nonexistent.py"])
        assert result.exit_code != 0  # エラーが発生することを期待

    def test_analyze_types_with_invalid_input(self):
        """無効な入力ファイルでエラーが発生することを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "types", "nonexistent.py"])
        assert result.exit_code != 0  # エラーが発生することを期待

    def test_convert_to_yaml_with_invalid_input(self):
        """無効な入力ファイルでエラーが発生することを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ["convert", "to-yaml", "nonexistent.py"])
        assert result.exit_code != 0  # エラーが発生することを期待

    def test_convert_to_type_with_invalid_input(self):
        """無効な入力YAMLファイルでエラーが発生することを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ["convert", "to-type", "nonexistent.yaml"])
        assert result.exit_code != 0  # エラーが発生することを期待

    def test_analyze_types_with_infer_option(self, tmp_path):
        """inferオプション付きでanalyze typesが動作することを確認"""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
class User:
    name: str
    age: int
""")

        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "types", str(test_file), "--infer"])
        # 実際の動作確認のため、exit_code=0を期待（エラーがなければOK）
        # mypy推論が実行されることを確認
        assert result.exit_code == 0 or "mypy 出力" in result.output
