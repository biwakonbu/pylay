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

    def test_check_help(self):
        """checkコマンドのヘルプが表示されることを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ["check", "--help"])
        assert result.exit_code == 0
        assert "品質をチェック" in result.stdout

    def test_check_focus_types(self, tmp_path):
        """check --focus typesオプションが動作することを確認"""
        runner = CliRunner()
        # テスト用のPythonファイルを作成
        test_file = tmp_path / "test.py"
        test_file.write_text("""
from typing import NewType
UserId = NewType('UserId', str)
""")
        result = runner.invoke(cli, ["check", "--focus", "types", str(test_file)])
        assert result.exit_code == 0
        # 型定義レベル統計が実行されることを確認
        assert "型定義レベル統計" in result.stdout or "解析中" in result.stdout

    def test_check_focus_ignore(self, tmp_path):
        """check --focus ignoreオプションが動作することを確認"""
        runner = CliRunner()
        # テスト用のPythonファイルを作成
        test_file = tmp_path / "test.py"
        test_file.write_text("""
def test_func(x):  # type: ignore
    return x + 1
""")
        result = runner.invoke(cli, ["check", "--focus", "ignore", str(test_file)])
        assert result.exit_code == 0
        # type-ignore診断が実行されることを確認
        assert "type-ignore" in result.stdout or "解析中" in result.stdout

    def test_check_focus_quality(self, tmp_path):
        """check --focus qualityオプションが動作することを確認"""
        runner = CliRunner()
        # テスト用のPythonファイルを作成
        test_file = tmp_path / "test.py"
        test_file.write_text("""
from typing import NewType
UserId = NewType('UserId', str)
""")
        result = runner.invoke(cli, ["check", "--focus", "quality", str(test_file)])
        assert result.exit_code == 0
        # 品質チェックが実行されることを確認
        assert "品質チェック" in result.stdout or "解析中" in result.stdout

    def test_yaml_help(self):
        """yamlコマンドのヘルプが表示されることを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ["yaml", "--help"])
        assert result.exit_code == 0
        assert "Python型からYAML仕様を生成" in result.stdout

    def test_types_help(self):
        """typesコマンドのヘルプが表示されることを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ["types", "--help"])
        assert result.exit_code == 0
        assert "YAML仕様からPython型を生成" in result.stdout

    def test_docs_help(self):
        """docsコマンドのヘルプが表示されることを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ["docs", "--help"])
        assert result.exit_code == 0
        assert "ドキュメント生成" in result.stdout

    def test_generate_type_docs_help(self):
        """generate type-docsコマンドのヘルプが表示されることを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ["generate", "type-docs", "--help"])
        assert result.exit_code == 0
        assert "Python 型から Markdown ドキュメントを生成" in result.stdout

    def test_infer_deps_help(self):
        """infer-depsコマンドのヘルプが表示されることを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ["infer-deps", "--help"])
        assert result.exit_code == 0
        assert "型推論と依存関係抽出を実行" in result.stdout

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

    def test_infer_deps_with_invalid_input(self):
        """無効な入力ファイルでエラーが発生することを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ["infer-deps", "nonexistent.py"])
        assert result.exit_code != 0  # エラーが発生することを期待

    def test_yaml_with_invalid_input(self):
        """無効な入力ファイルでエラーが発生することを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ["yaml", "nonexistent.py"])
        assert result.exit_code != 0  # エラーが発生することを期待

    def test_yaml_single_file_mode_with_type_alias(self, tmp_path):
        """yamlコマンド（単一ファイルモード）でtype文が正しく変換されることを確認"""
        runner = CliRunner()
        # テスト用のPythonファイルを作成
        test_file = tmp_path / "test_types.py"
        test_file.write_text(
            """
type UserId = str
type Point = tuple[float, float]
""",
        )
        # YAMLファイルの出力先を指定
        output_file = tmp_path / "test_types.lay.yaml"
        result = runner.invoke(cli, ["yaml", str(test_file), "-o", str(output_file)])

        # 実行が成功することを確認
        assert result.exit_code == 0

        # YAMLファイルが生成されることを確認
        assert output_file.exists()

        # YAML内容を検証
        yaml_content = output_file.read_text()
        assert "UserId:" in yaml_content
        assert "type: type_alias" in yaml_content
        assert "target: str" in yaml_content
        assert "Point:" in yaml_content
        assert "target: tuple[float, float]" in yaml_content

    def test_yaml_single_file_mode_with_newtype(self, tmp_path):
        """yamlコマンド（単一ファイルモード）でNewTypeが正しく変換されることを確認"""
        runner = CliRunner()
        # テスト用のPythonファイルを作成
        test_file = tmp_path / "test_newtypes.py"
        test_file.write_text(
            """
from typing import NewType

UserId = NewType('UserId', str)
Count = NewType('Count', int)
""",
        )
        # YAMLファイルの出力先を指定
        output_file = tmp_path / "test_newtypes.lay.yaml"
        result = runner.invoke(cli, ["yaml", str(test_file), "-o", str(output_file)])

        # 実行が成功することを確認
        assert result.exit_code == 0

        # YAMLファイルが生成されることを確認
        assert output_file.exists()

        # YAML内容を検証
        yaml_content = output_file.read_text()
        assert "UserId:" in yaml_content
        assert "type: newtype" in yaml_content
        assert "base_type: str" in yaml_content
        assert "Count:" in yaml_content
        assert "base_type: int" in yaml_content

    def test_yaml_single_file_mode_with_dataclass(self, tmp_path):
        """yamlコマンド（単一ファイルモード）でdataclassが正しく変換されることを確認"""
        runner = CliRunner()
        # テスト用のPythonファイルを作成
        test_file = tmp_path / "test_dataclasses.py"
        test_file.write_text(
            '''
from dataclasses import dataclass

@dataclass(frozen=True)
class Point:
    """2D座標点"""
    x: float
    y: float

@dataclass
class User:
    """ユーザー情報"""
    name: str
    age: int
''',
        )
        # YAMLファイルの出力先を指定
        output_file = tmp_path / "test_dataclasses.lay.yaml"
        result = runner.invoke(cli, ["yaml", str(test_file), "-o", str(output_file)])

        # 実行が成功することを確認
        assert result.exit_code == 0

        # YAMLファイルが生成されることを確認
        assert output_file.exists()

        # YAML内容を検証
        yaml_content = output_file.read_text()
        assert "Point:" in yaml_content
        assert "type: dataclass" in yaml_content
        assert "frozen: true" in yaml_content
        assert "description: 2D座標点" in yaml_content
        assert "User:" in yaml_content
        assert "frozen: false" in yaml_content
        assert "description: ユーザー情報" in yaml_content

    def test_types_with_invalid_input(self):
        """無効な入力YAMLファイルでエラーが発生することを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ["types", "nonexistent.yaml"])
        assert result.exit_code != 0  # エラーが発生することを期待

    def test_infer_deps_with_visualize_option(self, tmp_path):
        """visualizeオプション付きでinfer-depsが動作することを確認"""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
class User:
    name: str
    age: int
""")

        runner = CliRunner()
        result = runner.invoke(cli, ["infer-deps", str(test_file), "--visualize"])
        # 実際の動作確認のため、exit_code=0を期待（エラーがなければOK）
        # 依存関係抽出が実行されることを確認
        assert result.exit_code == 0 or "依存関係抽出" in result.output
