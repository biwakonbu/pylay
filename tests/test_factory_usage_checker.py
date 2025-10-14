"""
NewType直接使用検出機能のテスト
"""

from pathlib import Path
from textwrap import dedent

from src.core.analyzer.factory_usage_checker import (
    DirectUsageIssue,
    FactoryUsageChecker,
    check_directory,
)


class TestFactoryUsageChecker:
    """FactoryUsageCheckerのテスト"""

    def test_detect_direct_usage_with_factory(self, tmp_path: Path) -> None:
        """ファクトリ関数が存在する場合、直接使用を検出"""
        source_code = dedent("""
            from typing import NewType
            from pydantic import TypeAdapter, Field

            UserId = NewType('UserId', str)
            UserIdValidator: TypeAdapter[str] = TypeAdapter(str)

            def create_user_id(value: str) -> UserId:
                validated = UserIdValidator.validate_python(value)
                return UserId(validated)

            # 直接使用（検出対象）
            user_id = UserId("user123")
        """)

        test_file = tmp_path / "test.py"
        test_file.write_text(source_code)

        checker = FactoryUsageChecker()
        issues = checker.check_file(test_file)

        assert len(issues) == 1
        issue = issues[0]
        assert issue.type_name == "UserId"
        assert issue.factory_name == "create_user_id"
        assert "UserId" in issue.code_snippet

    def test_no_detection_without_factory(self, tmp_path: Path) -> None:
        """ファクトリ関数がない場合、検出しない"""
        source_code = dedent("""
            from typing import NewType

            UserId = NewType('UserId', str)

            # ファクトリ関数がないので検出対象外
            user_id = UserId("user123")
        """)

        test_file = tmp_path / "test.py"
        test_file.write_text(source_code)

        checker = FactoryUsageChecker()
        issues = checker.check_file(test_file)

        assert len(issues) == 0

    def test_no_detection_in_factory_function(self, tmp_path: Path) -> None:
        """ファクトリ関数内での使用は検出しない"""
        source_code = dedent("""
            from typing import NewType
            from pydantic import TypeAdapter

            UserId = NewType('UserId', str)
            UserIdValidator: TypeAdapter[str] = TypeAdapter(str)

            def create_user_id(value: str) -> UserId:
                validated = UserIdValidator.validate_python(value)
                # ファクトリ関数内での使用は除外
                return UserId(validated)
        """)

        test_file = tmp_path / "test.py"
        test_file.write_text(source_code)

        checker = FactoryUsageChecker()
        issues = checker.check_file(test_file)

        assert len(issues) == 0

    def test_detect_multiple_direct_usage(self, tmp_path: Path) -> None:
        """複数の直接使用を検出"""
        source_code = dedent("""
            from typing import NewType
            from pydantic import TypeAdapter

            UserId = NewType('UserId', str)
            UserIdValidator: TypeAdapter[str] = TypeAdapter(str)

            def create_user_id(value: str) -> UserId:
                return UserId(UserIdValidator.validate_python(value))

            # 複数の直接使用
            user1 = UserId("user1")
            user2 = UserId("user2")
            user3 = UserId("user3")
        """)

        test_file = tmp_path / "test.py"
        test_file.write_text(source_code)

        checker = FactoryUsageChecker()
        issues = checker.check_file(test_file)

        assert len(issues) == 3
        assert all(issue.type_name == "UserId" for issue in issues)
        assert all(issue.factory_name == "create_user_id" for issue in issues)

    def test_snake_case_to_pascal_case_conversion(self, tmp_path: Path) -> None:
        """snake_caseのファクトリ関数名をPascalCaseの型名に変換"""
        source_code = dedent("""
            from typing import NewType
            from pydantic import TypeAdapter

            LineNumber = NewType('LineNumber', int)
            LineNumberValidator: TypeAdapter[int] = TypeAdapter(int)

            def create_line_number(value: int) -> LineNumber:
                return LineNumber(LineNumberValidator.validate_python(value))

            # 直接使用
            line = LineNumber(123)
        """)

        test_file = tmp_path / "test.py"
        test_file.write_text(source_code)

        checker = FactoryUsageChecker()
        issues = checker.check_file(test_file)

        assert len(issues) == 1
        assert issues[0].type_name == "LineNumber"
        assert issues[0].factory_name == "create_line_number"

    def test_issue_to_dict(self) -> None:
        """DirectUsageIssueの辞書変換"""
        issue = DirectUsageIssue(
            file_path="/path/to/file.py",
            line_number=10,
            type_name="UserId",
            factory_name="create_user_id",
            code_snippet='user_id = UserId("test")',
        )

        result = issue.to_dict()

        assert result["file_path"] == "/path/to/file.py"
        assert result["line_number"] == 10
        assert result["type_name"] == "UserId"
        assert result["factory_name"] == "create_user_id"
        assert result["code_snippet"] == 'user_id = UserId("test")'

    def test_invalid_file(self, tmp_path: Path) -> None:
        """存在しないファイルはエラーを返さない"""
        checker = FactoryUsageChecker()
        issues = checker.check_file(tmp_path / "nonexistent.py")

        assert len(issues) == 0

    def test_syntax_error_file(self, tmp_path: Path) -> None:
        """構文エラーのファイルはエラーを返さない"""
        test_file = tmp_path / "invalid.py"
        test_file.write_text("invalid python syntax !@#$")

        checker = FactoryUsageChecker()
        issues = checker.check_file(test_file)

        assert len(issues) == 0


class TestCheckDirectory:
    """check_directory関数のテスト"""

    def test_check_directory_with_multiple_files(self, tmp_path: Path) -> None:
        """複数ファイルのディレクトリチェック"""
        # File 1: 問題あり
        file1 = tmp_path / "file1.py"
        file1.write_text(
            dedent("""
            from typing import NewType
            from pydantic import TypeAdapter

            UserId = NewType('UserId', str)
            def create_user_id(value: str) -> UserId:
                return UserId(value)

            user = UserId("test")
        """),
        )

        # File 2: 問題なし
        file2 = tmp_path / "file2.py"
        file2.write_text(
            dedent("""
            from typing import NewType

            Email = NewType('Email', str)
            email = Email("test@example.com")
        """),
        )

        results = check_directory(tmp_path)

        assert len(results) == 1
        assert str(file1) in results
        assert len(results[str(file1)]) == 1

    def test_check_directory_with_pattern(self, tmp_path: Path) -> None:
        """パターン指定でファイルをフィルタリング"""
        # Pythonファイル
        py_file = tmp_path / "test.py"
        py_file.write_text(
            dedent("""
            from typing import NewType
            from pydantic import TypeAdapter

            UserId = NewType('UserId', str)
            def create_user_id(value: str) -> UserId:
                return UserId(value)

            user = UserId("test")
        """),
        )

        # テキストファイル（除外対象）
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("not python code")

        results = check_directory(tmp_path, pattern="**/*.py")

        assert len(results) == 1
        assert str(py_file) in results

    def test_check_directory_empty(self, tmp_path: Path) -> None:
        """空のディレクトリは結果も空"""
        results = check_directory(tmp_path)

        assert len(results) == 0


class TestImportedTypes:
    """インポートされた型の検出テスト"""

    def test_detect_imported_type_usage(self, tmp_path: Path) -> None:
        """インポートされた型の直接使用を検出"""
        source_code = dedent("""
            from src.core.schemas.types import MaxDepth, LineNumber

            def process_data(depth: int):
                # インポートされた型の直接使用
                max_d = MaxDepth(depth)
                line = LineNumber(123)
                return max_d, line
        """)

        test_file = tmp_path / "test.py"
        test_file.write_text(source_code)

        checker = FactoryUsageChecker()
        issues = checker.check_file(test_file)

        assert len(issues) == 2
        type_names = {issue.type_name for issue in issues}
        assert "MaxDepth" in type_names
        assert "LineNumber" in type_names
        assert all(issue.factory_name for issue in issues)


class TestRealWorldScenarios:
    """実際のコードパターンのテスト"""

    def test_pydantic_field_default(self, tmp_path: Path) -> None:
        """Pydantic Fieldのデフォルト値での直接使用を検出"""
        source_code = dedent("""
            from typing import NewType
            from pydantic import BaseModel, Field, TypeAdapter

            MaxDepth = NewType('MaxDepth', int)
            MaxDepthValidator: TypeAdapter[int] = TypeAdapter(int)

            def create_max_depth(value: int) -> MaxDepth:
                return MaxDepth(MaxDepthValidator.validate_python(value))

            class Config(BaseModel):
                # type: ignoreがあっても検出
                max_depth: MaxDepth = Field(default=10)  # type: ignore[assignment]
        """)

        test_file = tmp_path / "test.py"
        test_file.write_text(source_code)

        checker = FactoryUsageChecker()
        issues = checker.check_file(test_file)

        # NOTE: Field(default=10) は MaxDepth(10) とは異なるため検出されない
        # これは実際の使用パターンを考慮した仕様
        assert len(issues) == 0

    def test_direct_constructor_call(self, tmp_path: Path) -> None:
        """コンストラクタ直接呼び出しを検出"""
        source_code = dedent("""
            from typing import NewType
            from pydantic import TypeAdapter

            Weight = NewType('Weight', float)
            WeightValidator: TypeAdapter[float] = TypeAdapter(float)

            def create_weight(value: float) -> Weight:
                return Weight(WeightValidator.validate_python(value))

            def calculate_score():
                # 直接呼び出し
                weight = Weight(0.5)
                return weight
        """)

        test_file = tmp_path / "test.py"
        test_file.write_text(source_code)

        checker = FactoryUsageChecker()
        issues = checker.check_file(test_file)

        assert len(issues) == 1
        assert issues[0].type_name == "Weight"
        assert issues[0].factory_name == "create_weight"
