"""設定ファイルの整合性テスト.

mypy.iniとpyrightconfig.jsonの設定が意図せず変更されることを防ぐため、
重要な設定項目の値を検証する。

【重要】このテストが失敗した場合:
- mypy.iniやpyrightconfig.jsonを勝手に変更しないでください
- ユーザーから明確に変更を指示された場合のみ変更してください
- 変更する場合は、このテストファイルも同時に更新してください
"""

import configparser
import json
from pathlib import Path

import pytest

# プロジェクトルートディレクトリ
PROJECT_ROOT = Path(__file__).parent.parent


class TestMypyConfig:
    """mypy.iniの設定整合性テスト."""

    @pytest.fixture  # type: ignore[misc]
    def mypy_config(self) -> configparser.ConfigParser:
        """mypy.iniを読み込む."""
        config = configparser.ConfigParser()
        config.read(PROJECT_ROOT / "mypy.ini")
        return config

    def test_mypy_python_version(self, mypy_config: configparser.ConfigParser) -> None:
        """Python 3.13が指定されていることを確認."""
        assert mypy_config.get("mypy", "python_version") == "3.13"

    def test_mypy_strict_mode(self, mypy_config: configparser.ConfigParser) -> None:
        """strictモードが有効化されていることを確認."""
        assert mypy_config.getboolean("mypy", "strict") is True

    def test_mypy_warning_settings(self, mypy_config: configparser.ConfigParser) -> None:
        """警告設定が正しく設定されていることを確認."""
        assert mypy_config.getboolean("mypy", "warn_redundant_casts") is True
        assert mypy_config.getboolean("mypy", "warn_unused_ignores") is True
        assert mypy_config.getboolean("mypy", "warn_no_return") is True
        assert mypy_config.getboolean("mypy", "warn_unreachable") is True

    def test_mypy_type_checking_strictness(self, mypy_config: configparser.ConfigParser) -> None:
        """型チェックの厳格化設定を確認."""
        assert mypy_config.getboolean("mypy", "disallow_untyped_defs") is True
        assert mypy_config.getboolean("mypy", "disallow_incomplete_defs") is True
        assert mypy_config.getboolean("mypy", "check_untyped_defs") is True
        assert mypy_config.getboolean("mypy", "disallow_untyped_decorators") is True

    def test_mypy_any_restrictions(self, mypy_config: configparser.ConfigParser) -> None:
        """Any型の制限設定を確認（大幅緩和されていることを確認）."""
        assert mypy_config.getboolean("mypy", "disallow_any_generics") is False
        assert mypy_config.getboolean("mypy", "disallow_any_unimported") is False
        assert mypy_config.getboolean("mypy", "disallow_any_expr") is False
        assert mypy_config.getboolean("mypy", "disallow_any_decorated") is False
        assert mypy_config.getboolean("mypy", "disallow_any_explicit") is False

    def test_mypy_import_settings(self, mypy_config: configparser.ConfigParser) -> None:
        """インポート関連設定を確認."""
        assert mypy_config.getboolean("mypy", "ignore_missing_imports") is True
        assert mypy_config.get("mypy", "follow_imports") == "silent"

    def test_mypy_pydantic_plugin(self, mypy_config: configparser.ConfigParser) -> None:
        """Pydanticプラグインが有効化されていることを確認."""
        assert mypy_config.get("mypy", "plugins") == "pydantic.mypy"

    def test_mypy_output_settings(self, mypy_config: configparser.ConfigParser) -> None:
        """出力設定を確認."""
        assert mypy_config.getboolean("mypy", "show_error_codes") is True
        assert mypy_config.getboolean("mypy", "show_column_numbers") is True
        assert mypy_config.getboolean("mypy", "error_summary") is True

    def test_mypy_module_settings(self, mypy_config: configparser.ConfigParser) -> None:
        """モジュール解決設定を確認."""
        assert mypy_config.get("mypy", "mypy_path") == "."
        assert mypy_config.getboolean("mypy", "explicit_package_bases") is True

    def test_mypy_disabled_error_codes(self, mypy_config: configparser.ConfigParser) -> None:
        """無効化されたエラーコードを確認."""
        disabled_codes = mypy_config.get("mypy", "disable_error_code")
        expected_codes = [
            "unreachable",
            "no-any-return",
            "return",
            "dict-item",
            "attr-defined",
            "operator",
            "union-attr",
            "arg-type",
            "func-returns-value",
            "unused-ignore",
            "index",
        ]
        for code in expected_codes:
            assert code in disabled_codes

    def test_mypy_test_section(self, mypy_config: configparser.ConfigParser) -> None:
        """テストファイル用の緩和設定を確認."""
        assert mypy_config.has_section("mypy-tests.*")
        assert mypy_config.getboolean("mypy-tests.*", "disallow_untyped_defs") is False
        assert mypy_config.getboolean("mypy-tests.*", "disallow_incomplete_defs") is False
        assert mypy_config.getboolean("mypy-tests.*", "check_untyped_defs") is False


class TestPyrightConfig:
    """pyrightconfig.jsonの設定整合性テスト."""

    @pytest.fixture  # type: ignore[misc]
    def pyright_config(self) -> dict:
        """pyrightconfig.jsonを読み込む."""
        with open(PROJECT_ROOT / "pyrightconfig.json") as f:
            return json.load(f)

    def test_pyright_python_version(self, pyright_config: dict) -> None:
        """Python 3.13が指定されていることを確認."""
        assert pyright_config["pythonVersion"] == "3.13"

    def test_pyright_type_checking_mode(self, pyright_config: dict) -> None:
        """型チェックモードが標準であることを確認."""
        assert pyright_config["typeCheckingMode"] == "standard"

    def test_pyright_venv_settings(self, pyright_config: dict) -> None:
        """仮想環境設定を確認."""
        assert pyright_config["venvPath"] == "."
        assert pyright_config["venv"] == ".venv"

    def test_pyright_library_code(self, pyright_config: dict) -> None:
        """ライブラリコードの型使用が有効化されていることを確認."""
        assert pyright_config["useLibraryCodeForTypes"] is True

    def test_pyright_import_diagnostics(self, pyright_config: dict) -> None:
        """インポート関連の診断設定を確認."""
        assert pyright_config["reportMissingImports"] == "error"
        assert pyright_config["reportMissingTypeStubs"] == "warning"
        assert pyright_config["reportImportCycles"] == "warning"

    def test_pyright_unused_diagnostics(self, pyright_config: dict) -> None:
        """未使用コードの診断設定を確認."""
        assert pyright_config["reportUnusedImport"] == "error"
        assert pyright_config["reportUnusedClass"] == "error"
        assert pyright_config["reportUnusedFunction"] == "error"
        assert pyright_config["reportUnusedVariable"] == "error"
        assert pyright_config["reportDuplicateImport"] == "error"

    def test_pyright_optional_diagnostics(self, pyright_config: dict) -> None:
        """Optional型の診断設定を確認."""
        assert pyright_config["reportOptionalSubscript"] == "error"
        assert pyright_config["reportOptionalMemberAccess"] == "error"
        assert pyright_config["reportOptionalCall"] == "error"
        assert pyright_config["reportOptionalIterable"] == "error"
        assert pyright_config["reportOptionalContextManager"] == "error"
        assert pyright_config["reportOptionalOperand"] == "error"

    def test_pyright_type_annotation_diagnostics(self, pyright_config: dict) -> None:
        """型アノテーション関連の診断設定を確認."""
        assert pyright_config["reportUntypedFunctionDecorator"] == "warning"
        assert pyright_config["reportUntypedClassDecorator"] == "warning"
        assert pyright_config["reportUntypedBaseClass"] == "error"
        assert pyright_config["reportUntypedNamedTuple"] == "error"

    def test_pyright_type_consistency_diagnostics(self, pyright_config: dict) -> None:
        """型の一貫性診断設定を確認."""
        assert pyright_config["reportConstantRedefinition"] == "error"
        assert pyright_config["reportIncompatibleMethodOverride"] == "error"
        assert pyright_config["reportIncompatibleVariableOverride"] == "error"
        assert pyright_config["reportInconsistentConstructor"] == "error"
        assert pyright_config["reportInvalidTypeVarUse"] == "error"

    def test_pyright_variable_diagnostics(self, pyright_config: dict) -> None:
        """変数診断設定を確認."""
        assert pyright_config["reportUnboundVariable"] == "error"
        assert pyright_config["reportUndefinedVariable"] == "error"

    def test_pyright_disabled_diagnostics(self, pyright_config: dict) -> None:
        """無効化された診断設定を確認."""
        assert pyright_config["reportPrivateUsage"] == "none"
        assert pyright_config["reportMissingSuperCall"] == "none"
        assert pyright_config["reportUninitializedInstanceVariable"] == "none"
        assert pyright_config["reportCallInDefaultInitializer"] == "none"
        assert pyright_config["reportUnnecessaryIsInstance"] == "none"
        assert pyright_config["reportUnknownVariableType"] == "none"
        assert pyright_config["reportUnknownMemberType"] == "none"
        assert pyright_config["reportUnknownArgumentType"] == "none"
        assert pyright_config["reportImplicitStringConcatenation"] == "none"
        assert pyright_config["reportMissingModuleSource"] == "none"

    def test_pyright_include_exclude(self, pyright_config: dict) -> None:
        """include/exclude設定を確認."""
        assert pyright_config["include"] == ["."]
        expected_excludes = [
            "**/__pycache__",
            "**/node_modules",
            "**/.git",
            "**/dist",
            "**/build",
            "**/*.pyc",
            "**/*.lay.py",  # 自動生成ファイルを除外
            "tests/fixtures/invalid.py",  # 意図的な構文エラーファイルを除外
        ]
        assert pyright_config["exclude"] == expected_excludes


class TestPyprojectConfig:
    """pyproject.tomlのpylay解析設定テスト."""

    @pytest.fixture  # type: ignore[misc]
    def pyproject_config(self) -> dict:
        """pyproject.tomlを読み込む."""
        import tomllib

        with open(PROJECT_ROOT / "pyproject.toml", "rb") as f:
            return tomllib.load(f)

    def test_pylay_target_dirs(self, pyproject_config: dict) -> None:
        """解析対象ディレクトリが正しく設定されていることを確認."""
        target_dirs = pyproject_config["tool"]["pylay"]["target_dirs"]
        assert target_dirs == ["src", "scripts", "utils"]

    def test_pylay_output_dir(self, pyproject_config: dict) -> None:
        """出力ディレクトリが正しく設定されていることを確認."""
        output_dir = pyproject_config["tool"]["pylay"]["output_dir"]
        assert output_dir == "docs/pylay"

    def test_pylay_feature_flags(self, pyproject_config: dict) -> None:
        """機能フラグが正しく設定されていることを確認."""
        pylay_config = pyproject_config["tool"]["pylay"]
        assert pylay_config["generate_markdown"] is True
        assert pylay_config["extract_deps"] is True
        assert pylay_config["clean_output_dir"] is True

    def test_pylay_infer_level(self, pyproject_config: dict) -> None:
        """型推論レベルが正しく設定されていることを確認."""
        infer_level = pyproject_config["tool"]["pylay"]["infer_level"]
        assert infer_level == "strict"

    def test_pylay_exclude_patterns(self, pyproject_config: dict) -> None:
        """除外パターンが正しく設定されていることを確認."""
        exclude_patterns = pyproject_config["tool"]["pylay"]["exclude_patterns"]
        expected_patterns = [
            "**/tests/**",
            "**/*_test.py",
            "**/__pycache__",
            "**/.venv/**",
            "**/node_modules/**",
            "**/dist/**",
            "**/build/**",
        ]
        assert exclude_patterns == expected_patterns

    def test_pylay_max_depth(self, pyproject_config: dict) -> None:
        """最大深度が正しく設定されていることを確認."""
        max_depth = pyproject_config["tool"]["pylay"]["max_depth"]
        assert max_depth == 10

    def test_pylay_quality_check_level_thresholds(self, pyproject_config: dict) -> None:
        """品質チェックの型レベル閾値が正しく設定されていることを確認."""
        thresholds = pyproject_config["tool"]["pylay"]["quality_check"]["level_thresholds"]
        assert thresholds["level1_max"] == 0.15
        assert thresholds["level2_min"] == 0.50
        assert thresholds["level3_min"] == 0.20

    def test_pylay_quality_check_error_conditions(self, pyproject_config: dict) -> None:
        """品質チェックのエラー条件が正しく設定されていることを確認."""
        error_conditions = pyproject_config["tool"]["pylay"]["quality_check"]["error_conditions"]
        assert len(error_conditions) == 5
        # 各条件が必須フィールドを持つことを確認
        for condition in error_conditions:
            assert "condition" in condition
            assert "message" in condition

    def test_pylay_quality_check_severity_levels(self, pyproject_config: dict) -> None:
        """品質チェックの重要度レベルが正しく設定されていることを確認."""
        severity_levels = pyproject_config["tool"]["pylay"]["quality_check"]["severity_levels"]
        assert len(severity_levels) == 3
        # 各レベルが必須フィールドを持つことを確認
        for level in severity_levels:
            assert "name" in level
            assert "color" in level
            assert "threshold" in level

    def test_pylay_quality_check_improvement_guidance(self, pyproject_config: dict) -> None:
        """品質チェックの改善ガイダンスが正しく設定されていることを確認."""
        improvement_guidance = pyproject_config["tool"]["pylay"]["quality_check"]["improvement_guidance"]
        assert len(improvement_guidance) == 5
        # 各ガイダンスが必須フィールドを持つことを確認
        for guidance in improvement_guidance:
            assert "level" in guidance
            assert "suggestion" in guidance


class TestConfigConsistency:
    """mypy.iniとpyrightconfig.jsonの一貫性テスト."""

    def test_python_version_consistency(self) -> None:
        """両設定ファイルでPython 3.13が指定されていることを確認."""
        # mypy.ini
        mypy_config = configparser.ConfigParser()
        mypy_config.read(PROJECT_ROOT / "mypy.ini")
        mypy_version = mypy_config.get("mypy", "python_version")

        # pyrightconfig.json
        with open(PROJECT_ROOT / "pyrightconfig.json") as f:
            pyright_config = json.load(f)
        pyright_version = pyright_config["pythonVersion"]

        assert mypy_version == pyright_version == "3.13"

    def test_strict_mode_consistency(self) -> None:
        """両設定ファイルで厳格な型チェックが有効化されていることを確認."""
        # mypy.ini
        mypy_config = configparser.ConfigParser()
        mypy_config.read(PROJECT_ROOT / "mypy.ini")
        mypy_strict = mypy_config.getboolean("mypy", "strict")

        # pyrightconfig.json
        with open(PROJECT_ROOT / "pyrightconfig.json") as f:
            pyright_config = json.load(f)
        # Pyrightの場合はtypeCheckingModeがbasic/standard/strictのいずれか
        pyright_mode = pyright_config["typeCheckingMode"]

        assert mypy_strict is True
        assert pyright_mode in ["standard", "strict"]


class TestPylayNewConfig:
    """Issue #51: .lay.py/.lay.yaml方式の設定テスト."""

    def test_generation_config_defaults(self) -> None:
        """generation設定のデフォルト値を確認."""
        from src.core.schemas.pylay_config import GenerationConfig

        config = GenerationConfig()
        assert config.lay_suffix == ".lay.py"
        assert config.lay_yaml_suffix == ".lay.yaml"
        assert config.add_generation_header is True
        assert config.include_source_path is True

    def test_output_config_defaults(self) -> None:
        """output設定のデフォルト値を確認."""
        from src.core.schemas.pylay_config import OutputConfig

        config = OutputConfig()
        # 新仕様：デフォルトはNone（Pythonソースと同じディレクトリ）
        assert config.yaml_output_dir is None
        assert config.markdown_output_dir is None
        assert config.mirror_package_structure is True
        assert config.include_metadata is True
        assert config.preserve_docstrings is True

    def test_imports_config_defaults(self) -> None:
        """imports設定のデフォルト値を確認."""
        from src.core.schemas.pylay_config import ImportsConfig

        config = ImportsConfig()
        assert config.use_relative_imports is True

    def test_pylay_config_with_new_sections(self) -> None:
        """PylayConfigが新しい設定セクションを持つことを確認."""
        from src.core.schemas.pylay_config import PylayConfig

        config = PylayConfig()
        assert config.generation is not None
        assert config.output is not None
        assert config.imports is not None

        # デフォルト値の確認
        assert config.generation.lay_suffix == ".lay.py"
        # 新仕様：デフォルトはNone（Pythonソースと同じディレクトリ）
        assert config.output.yaml_output_dir is None
        assert config.output.markdown_output_dir is None
        assert config.imports.use_relative_imports is True
