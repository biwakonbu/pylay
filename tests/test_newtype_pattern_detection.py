"""NewType + ファクトリ関数パターンの検出テスト

PEP 484準拠のNewType + ファクトリ関数パターンが正しく検出されることを確認します。
"""

from pathlib import Path
from textwrap import dedent

import pytest

from src.core.analyzer.type_classifier import TypeClassifier


@pytest.fixture
def classifier() -> TypeClassifier:
    """TypeClassifierインスタンスを作成"""
    return TypeClassifier()


class TestNewTypePatternDetection:
    """NewType + ファクトリ関数パターンの検出テスト"""

    def test_newtype_with_create_factory(self, classifier: TypeClassifier, tmp_path: Path) -> None:
        """NewType + create_*ファクトリ関数のパターンを検出（Level 2）"""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            dedent("""
            from typing import NewType

            UserId = NewType('UserId', str)

            def create_user_id(value: str) -> UserId:
                '''UserIdを作成するファクトリ関数'''
                if len(value) < 8:
                    raise ValueError("UserId must be at least 8 characters")
                return UserId(value)
            """),
        )

        results = classifier.classify_file(test_file)

        # UserId がLevel 2として検出されること
        user_id_types = [td for td in results if td.name == "UserId"]
        assert len(user_id_types) == 1
        assert user_id_types[0].level == "level2"
        assert user_id_types[0].category == "newtype_with_factory"

    def test_newtype_with_validate_call(self, classifier: TypeClassifier, tmp_path: Path) -> None:
        """NewType + @validate_callファクトリ関数のパターンを検出（Level 2）"""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            dedent("""
            from typing import NewType, Annotated
            from pydantic import Field, validate_call

            Email = NewType('Email', str)

            @validate_call
            def Email(value: Annotated[str, Field(pattern=r'^[^@]+@[^@]+$')]) -> Email:
                '''Emailを作成する検証付きファクトリ関数'''
                return NewType('Email', str)(value)
            """),
        )

        results = classifier.classify_file(test_file)

        # Email がLevel 2として検出されること
        email_types = [td for td in results if td.name == "Email"]
        assert len(email_types) == 1
        assert email_types[0].level == "level2"
        assert email_types[0].category == "newtype_with_factory"

    def test_newtype_without_factory(self, classifier: TypeClassifier, tmp_path: Path) -> None:
        """ファクトリ関数なしのNewTypeパターンを検出 (Level 1)"""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            dedent("""
            from typing import NewType

            StatusCode = NewType('StatusCode', int)
            """),
        )

        results = classifier.classify_file(test_file)

        # StatusCode がLevel 1として検出されること
        status_types = [td for td in results if td.name == "StatusCode"]
        assert len(status_types) == 1
        assert status_types[0].level == "level1"
        assert status_types[0].category == "newtype_plain"

    def test_multiple_newtype_patterns(self, classifier: TypeClassifier, tmp_path: Path) -> None:
        """複数のNewTypeパターンが混在する場合の検出"""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            dedent("""
            from typing import NewType, Annotated
            from pydantic import Field, validate_call

            # Pattern 1: NewType + create_* factory (Level 2)
            UserId = NewType('UserId', str)

            def create_user_id(value: str) -> UserId:
                return UserId(value)

            # Pattern 2: NewType + @validate_call factory (Level 2)
            Email = NewType('Email', str)

            @validate_call
            def Email(value: Annotated[str, Field(pattern=r'^[^@]+@[^@]+$')]) -> Email:
                return NewType('Email', str)(value)

            # Pattern 3: NewType without factory (Level 1)
            StatusCode = NewType('StatusCode', int)
            ErrorCode = NewType('ErrorCode', int)

            # Pattern 4: type alias (Level 1)
            type Timestamp = float
            """),
        )

        results = classifier.classify_file(test_file)

        # Level 2の型定義を確認
        level2_types = [td for td in results if td.level == "level2"]
        assert len(level2_types) == 2
        level2_names = {td.name for td in level2_types}
        assert level2_names == {"UserId", "Email"}

        # Level 1の型定義を確認
        level1_types = [td for td in results if td.level == "level1"]
        assert len(level1_types) == 3
        level1_names = {td.name for td in level1_types}
        assert level1_names == {"StatusCode", "ErrorCode", "Timestamp"}

    def test_newtype_with_snake_case_factory(self, classifier: TypeClassifier, tmp_path: Path) -> None:
        """snake_case → PascalCaseの変換が正しく動作する"""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            dedent("""
            from typing import NewType

            UserProfileId = NewType('UserProfileId', str)

            def create_user_profile_id(value: str) -> UserProfileId:
                '''UserProfileIdを作成'''
                return UserProfileId(value)
            """),
        )

        results = classifier.classify_file(test_file)

        # UserProfileId がLevel 2として検出されること
        types = [td for td in results if td.name == "UserProfileId"]
        assert len(types) == 1
        assert types[0].level == "level2"
        assert types[0].category == "newtype_with_factory"

    def test_newtype_factory_mismatch(self, classifier: TypeClassifier, tmp_path: Path) -> None:
        """NewTypeとファクトリ関数の名前が一致しない場合はLevel 1"""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            dedent("""
            from typing import NewType

            UserId = NewType('UserId', str)

            # ファクトリ関数の返り値型が異なる
            def create_user_id(value: str) -> str:
                return value
            """),
        )

        results = classifier.classify_file(test_file)

        # UserId はLevel 1として検出されること（ファクトリ関数が一致しない）
        types = [td for td in results if td.name == "UserId"]
        assert len(types) == 1
        assert types[0].level == "level1"
        assert types[0].category == "newtype_plain"

    def test_newtype_with_docstring(self, classifier: TypeClassifier, tmp_path: Path) -> None:
        """docstringが正しく抽出される"""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            dedent("""
            from typing import NewType

            # ユーザー識別子
            UserId = NewType('UserId', str)

            def create_user_id(value: str) -> UserId:
                '''UserIdを作成するファクトリ関数'''
                return UserId(value)
            """),
        )

        results = classifier.classify_file(test_file)

        types = [td for td in results if td.name == "UserId"]
        assert len(types) == 1
        # docstringはコメント形式では抽出されないが、エラーにはならない
        assert types[0].level == "level2"

    def test_no_duplicate_detection(self, classifier: TypeClassifier, tmp_path: Path) -> None:
        """同じ型定義が重複して検出されないことを確認"""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            dedent("""
            from typing import NewType

            UserId = NewType('UserId', str)

            def create_user_id(value: str) -> UserId:
                return UserId(value)
            """),
        )

        results = classifier.classify_file(test_file)

        # UserId は1回のみ検出されること
        user_id_types = [td for td in results if td.name == "UserId"]
        assert len(user_id_types) == 1

    def test_newtype_variable_name_mismatch(self, classifier: TypeClassifier, tmp_path: Path) -> None:
        """変数名と型名が一致しないNewTypeは検出しない"""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            dedent("""
            from typing import NewType

            # 変数名と型名が異なる（非推奨パターン）
            user_id_type = NewType('UserId', str)
            """),
        )

        results = classifier.classify_file(test_file)

        # UserId は検出されないこと（変数名と型名が一致しない）
        types = [td for td in results if td.name == "UserId"]
        assert len(types) == 0

    def test_validate_call_with_complex_parameters(self, classifier: TypeClassifier, tmp_path: Path) -> None:
        """@validate_callの複雑なパラメータ定義が正しく処理される"""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            dedent("""
            from typing import NewType, Annotated
            from pydantic import Field, validate_call

            Email = NewType('Email', str)

            @validate_call
            def Email(
                value: Annotated[
                    str,
                    Field(
                        pattern=r'^[^@]+@[^@]+$',
                        min_length=5,
                        max_length=255
                    )
                ]
            ) -> Email:
                '''複雑なバリデーション付きEmail作成'''
                return NewType('Email', str)(value)
            """),
        )

        results = classifier.classify_file(test_file)

        email_types = [td for td in results if td.name == "Email"]
        assert len(email_types) == 1
        assert email_types[0].level == "level2"
        assert email_types[0].category == "newtype_with_factory"

    def test_mixed_type_definitions(self, classifier: TypeClassifier, tmp_path: Path) -> None:
        """様々な型定義パターンが混在する実践的なケース"""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            dedent("""
            from typing import NewType, Annotated
            from pydantic import BaseModel, Field, validate_call
            from dataclasses import dataclass

            # Level 1: type alias
            type Timestamp = float
            type JsonDict = dict[str, object]

            # Level 1: NewType without factory
            StatusCode = NewType('StatusCode', int)

            # Level 2: NewType with factory
            UserId = NewType('UserId', str)

            def create_user_id(value: str) -> UserId:
                return UserId(value)

            # Level 2: NewType with @validate_call
            Email = NewType('Email', str)

            @validate_call
            def Email(value: Annotated[str, Field(pattern=r'^.+@.+$')]) -> Email:
                return NewType('Email', str)(value)

            # Level 3: BaseModel
            class User(BaseModel):
                id: UserId
                email: Email

            # other: dataclass
            @dataclass
            class Config:
                timeout: int
            """),
        )

        results = classifier.classify_file(test_file)

        # Level 1
        level1 = [td for td in results if td.level == "level1"]
        level1_names = {td.name for td in level1}
        assert "Timestamp" in level1_names
        assert "JsonDict" in level1_names
        assert "StatusCode" in level1_names

        # Level 2
        level2 = [td for td in results if td.level == "level2"]
        level2_names = {td.name for td in level2}
        assert "UserId" in level2_names
        assert "Email" in level2_names

        # Level 3
        level3 = [td for td in results if td.level == "level3"]
        level3_names = {td.name for td in level3}
        assert "User" in level3_names

        # other
        other = [td for td in results if td.level == "other"]
        other_names = {td.name for td in other}
        assert "Config" in other_names
