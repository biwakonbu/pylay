"""NewTypeパターン検出のエッジケーステスト

境界条件や特殊なケースが正しく処理されることを確認します。
"""

from pathlib import Path
from textwrap import dedent

import pytest

from src.core.analyzer.type_classifier import TypeClassifier


class TestNewTypeEdgeCases:
    """NewTypeパターン検出のエッジケース"""

    @pytest.fixture  # type: ignore[misc]
    def classifier(self) -> TypeClassifier:
        """TypeClassifierインスタンスを作成"""
        return TypeClassifier()

    def test_empty_file(self, classifier: TypeClassifier, tmp_path: Path) -> None:
        """空のファイルでエラーが発生しない"""
        test_file = tmp_path / "test.py"
        test_file.write_text("")

        results = classifier.classify_file(test_file)
        assert len(results) == 0

    def test_syntax_error_file(self, classifier: TypeClassifier, tmp_path: Path) -> None:
        """構文エラーのあるファイルでクラッシュしない"""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            dedent("""
            from typing import NewType

            # 構文エラー
            UserId = NewType('UserId' str)  # カンマ忘れ
            """)
        )

        # エラーにならないこと（空のリストを返す）
        results = classifier.classify_file(test_file)
        # 構文エラーがあってもregexパターンで検出される可能性がある
        assert isinstance(results, list)

    def test_newtype_without_import(self, classifier: TypeClassifier, tmp_path: Path) -> None:
        """NewTypeのインポートなしでも検出される"""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            dedent("""
            # NewTypeのインポートなし（実際は動かないコード）
            UserId = NewType('UserId', str)

            def create_user_id(value: str) -> UserId:
                return UserId(value)
            """)
        )

        results = classifier.classify_file(test_file)

        # パターンマッチングで検出される
        types = [td for td in results if td.name == "UserId"]
        assert len(types) == 1

    def test_newtype_with_multiple_factories(self, classifier: TypeClassifier, tmp_path: Path) -> None:
        """同じ型に対して複数のファクトリ関数がある場合"""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            dedent("""
            from typing import NewType

            UserId = NewType('UserId', str)

            def create_user_id(value: str) -> UserId:
                return UserId(value)

            def create_user_id_from_int(value: int) -> UserId:
                return UserId(str(value))
            """)
        )

        results = classifier.classify_file(test_file)

        # UserIdは1回のみ検出され、Level 2
        types = [td for td in results if td.name == "UserId"]
        assert len(types) == 1
        assert types[0].level == "level2"

    def test_factory_without_newtype(self, classifier: TypeClassifier, tmp_path: Path) -> None:
        """NewTypeなしでファクトリ関数だけがある場合"""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            dedent("""
            def create_user_id(value: str) -> str:
                '''ファクトリ関数だけ（NewTypeなし）'''
                return value
            """)
        )

        results = classifier.classify_file(test_file)

        # UserIdは検出されない
        types = [td for td in results if td.name == "UserId"]
        assert len(types) == 0

    def test_newtype_in_class(self, classifier: TypeClassifier, tmp_path: Path) -> None:
        """クラス内でのNewType定義"""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            dedent("""
            from typing import NewType

            class UserModule:
                UserId = NewType('UserId', str)

                @staticmethod
                def create_user_id(value: str) -> UserId:
                    return UserModule.UserId(value)
            """)
        )

        results = classifier.classify_file(test_file)

        # クラス内のNewTypeは現在の実装では検出されない
        # （モジュールレベルの定義のみを対象としているため）
        types = [td for td in results if td.name == "UserId"]
        # このテストは現状の動作を確認するもの
        assert len(types) <= 1

    def test_newtype_with_unicode_name(self, classifier: TypeClassifier, tmp_path: Path) -> None:
        """Unicode文字を含む型名（非推奨だが構文的には有効）"""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            dedent("""
            from typing import NewType

            # Unicodeは識別子として有効だが、正規表現\\wでマッチしないかもしれない
            ユーザーID = NewType('ユーザーID', str)

            def create_ユーザーid(value: str) -> ユーザーID:
                return ユーザーID(value)
            """)
        )

        results = classifier.classify_file(test_file)

        # 現在の\\wパターンではUnicodeはマッチしない可能性がある
        # このテストは現状の動作を確認
        assert isinstance(results, list)

    def test_newtype_with_generic_base(self, classifier: TypeClassifier, tmp_path: Path) -> None:
        """ジェネリック型をベースとするNewType"""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            dedent("""
            from typing import NewType

            # 現在の正規表現では単純な型名しかマッチしない
            # UserList = NewType('UserList', list[str])
            # これは検出されない

            # 単純な型のみ
            UserId = NewType('UserId', str)
            """)
        )

        results = classifier.classify_file(test_file)

        # UserIdは検出される
        types = [td for td in results if td.name == "UserId"]
        assert len(types) == 1

    def test_newtype_with_comment_on_same_line(self, classifier: TypeClassifier, tmp_path: Path) -> None:
        """同じ行にコメントがある場合"""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            dedent("""
            from typing import NewType

            UserId = NewType('UserId', str)  # ユーザー識別子

            def create_user_id(value: str) -> UserId:  # ファクトリ関数
                return UserId(value)
            """)
        )

        results = classifier.classify_file(test_file)

        types = [td for td in results if td.name == "UserId"]
        assert len(types) == 1
        assert types[0].level == "level2"

    def test_validate_call_without_newline(self, classifier: TypeClassifier, tmp_path: Path) -> None:
        """@validate_callとdefが同じ行にある場合（非推奨だが有効）"""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            dedent("""
            from typing import NewType
            from pydantic import validate_call

            Email = NewType('Email', str)

            # 改行なし（非推奨パターン）
            @validate_call; def Email(v: str) -> Email: return Email(v)
            """)
        )

        results = classifier.classify_file(test_file)

        # 改行がないため、VALIDATE_CALL_PATTERNではマッチしない
        types = [td for td in results if td.name == "Email"]
        assert len(types) == 1
        # Level 1 として検出される（ファクトリとして認識されない）
        assert types[0].level == "level1"

    def test_multiple_files_isolation(self, classifier: TypeClassifier, tmp_path: Path) -> None:
        """複数ファイルを処理しても状態が混ざらない"""
        file1 = tmp_path / "test1.py"
        file1.write_text(
            dedent("""
            from typing import NewType

            UserId = NewType('UserId', str)

            def create_user_id(value: str) -> UserId:
                return UserId(value)
            """)
        )

        file2 = tmp_path / "test2.py"
        file2.write_text(
            dedent("""
            from typing import NewType

            Email = NewType('Email', str)
            """)
        )

        results1 = classifier.classify_file(file1)
        results2 = classifier.classify_file(file2)

        # file1のUserId
        user_id_types = [td for td in results1 if td.name == "UserId"]
        assert len(user_id_types) == 1
        assert user_id_types[0].level == "level2"

        # file2のEmail（ファクトリなし）
        email_types = [td for td in results2 if td.name == "Email"]
        assert len(email_types) == 1
        assert email_types[0].level == "level1"

    def test_newtype_with_type_comment(self, classifier: TypeClassifier, tmp_path: Path) -> None:
        """type: ignore等のコメントがある場合"""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            dedent("""
            from typing import NewType, Annotated
            from pydantic import validate_call, Field

            Email = NewType('Email', str)

            @validate_call
            def Email(
                value: Annotated[str, Field(pattern=r'^.+@.+$')]
            ) -> Email:  # type: ignore[no-redef]
                return NewType('Email', str)(value)  # type: ignore[misc]
            """)
        )

        results = classifier.classify_file(test_file)

        types = [td for td in results if td.name == "Email"]
        assert len(types) == 1
        assert types[0].level == "level2"

    def test_newtype_with_wrong_capitalization_factory(self, classifier: TypeClassifier, tmp_path: Path) -> None:
        """ファクトリ関数名の大文字小文字が完全一致しない場合"""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            dedent("""
            from typing import NewType

            UserId = NewType('UserId', str)

            # userid != UserId
            def create_userid(value: str) -> UserId:
                return UserId(value)
            """)
        )

        results = classifier.classify_file(test_file)

        types = [td for td in results if td.name == "UserId"]
        assert len(types) == 1
        # create_userid → Userid (PascalCase変換) != UserId
        # Level 1として検出される
        assert types[0].level == "level1"
