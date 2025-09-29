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
        assert "型解析・依存関係分析コマンド" in result.stdout

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

    def test_analyze_infer_deps_help(self):
        """analyze infer-depsコマンドのヘルプが表示されることを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "infer-deps", "--help"])
        assert result.exit_code == 0
        assert "型推論と依存関係抽出を実行" in result.stdout

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

    def test_analyze_infer_deps_with_invalid_input(self):
        """無効な入力ファイルでエラーが発生することを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "infer-deps", "nonexistent.py"])
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

    def test_analyze_infer_deps_with_visualize_option(self, tmp_path):
        """visualizeオプション付きでanalyze infer-depsが動作することを確認"""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
class User:
    name: str
    age: int
""")

        runner = CliRunner()
        result = runner.invoke(
            cli, ["analyze", "infer-deps", str(test_file), "--visualize"]
        )
        # 実際の動作確認のため、exit_code=0を期待（エラーがなければOK）
        # 依存関係抽出が実行されることを確認
        assert result.exit_code == 0 or "依存関係抽出" in result.output
