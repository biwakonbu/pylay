"""
アナライザーカスタム例外定義

解析エラーを構造化して扱うための例外クラスを提供します。
"""

from src.core.schemas.types import CyclePath, FilePath, Message


class AnalysisError(Exception):
    """
    解析エラーの基底クラス

    すべてのアナライザー例外の親クラスです。
    """

    def __init__(self, message: Message, file_path: FilePath | None = None) -> None:
        """
        解析エラーを初期化します。

        Args:
            message: エラーメッセージ
            file_path: エラーが発生したファイルパス(オプション)
        """
        self.message = message
        self.file_path = file_path
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """フォーマット済みエラーメッセージを生成"""
        if self.file_path:
            return f"{self.message} (ファイル: {self.file_path})"
        return self.message


class MypyExecutionError(AnalysisError):
    """
    mypy実行エラー

    mypy型推論の実行に失敗した場合に発生します。
    """

    def __init__(
        self,
        message: str,
        return_code: int,
        stdout: str = "",
        stderr: str = "",
        file_path: str | None = None,
    ) -> None:
        """
        mypy実行エラーを初期化します。

        Args:
            message: エラーメッセージ
            return_code: mypy終了コード
            stdout: 標準出力
            stderr: 標準エラー
            file_path: エラーが発生したファイルパス(オプション)
        """
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(message, file_path)

    def _format_message(self) -> str:
        """詳細なエラーメッセージを生成"""
        base_msg = super()._format_message()
        details = f"{base_msg}\n終了コード: {self.return_code}"
        if self.stderr:
            limit = 200
            if len(self.stderr) > limit:
                details += f"\n標準エラー: {self.stderr[:limit]}..."
            else:
                details += f"\n標準エラー: {self.stderr}"
        return details


class ASTParseError(AnalysisError):
    """
    AST解析エラー

    Pythonコードの構文解析に失敗した場合に発生します。
    """

    def __init__(self, message: str, line_number: int | None = None, file_path: str | None = None) -> None:
        """
        AST解析エラーを初期化します。

        Args:
            message: エラーメッセージ
            line_number: エラーが発生した行番号(オプション)
            file_path: エラーが発生したファイルパス(オプション)
        """
        self.line_number = line_number
        super().__init__(message, file_path)

    def _format_message(self) -> str:
        """行番号を含むエラーメッセージを生成"""
        base_msg = super()._format_message()
        if self.line_number:
            return f"{base_msg} (行: {self.line_number})"
        return base_msg


class DependencyExtractionError(AnalysisError):
    """
    依存関係抽出エラー

    依存関係の抽出処理に失敗した場合に発生します。
    """

    def __init__(self, message: Message, file_path: FilePath | None = None) -> None:
        """
        依存関係抽出エラーを初期化します。

        Args:
            message: エラーメッセージ
            file_path: エラーが発生したファイルパス(オプション)
        """
        super().__init__(message, file_path)


class TypeInferenceError(AnalysisError):
    """
    型推論エラー

    型推論処理に失敗した場合に発生します。
    """

    def __init__(
        self,
        message: str,
        variable_name: str | None = None,
        file_path: str | None = None,
    ) -> None:
        """
        型推論エラーを初期化します。

        Args:
            message: エラーメッセージ
            variable_name: エラーが発生した変数名(オプション)
            file_path: エラーが発生したファイルパス(オプション)
        """
        self.variable_name = variable_name
        super().__init__(message, file_path)

    def _format_message(self) -> str:
        """変数名を含むエラーメッセージを生成"""
        base_msg = super()._format_message()
        if self.variable_name:
            return f"{base_msg} (変数: {self.variable_name})"
        return base_msg


class CircularDependencyError(AnalysisError):
    """
    循環依存エラー

    循環依存が検出された場合に発生します(厳密モードのみ)。
    """

    def __init__(self, message: Message, cycle: CyclePath, file_path: FilePath | None = None) -> None:
        """
        循環依存エラーを初期化します。

        Args:
            message: エラーメッセージ
            cycle: 循環パス(ノード名のリスト)
            file_path: エラーが発生したファイルパス(オプション)
        """
        self.cycle = cycle
        super().__init__(message, file_path)

    def _format_message(self) -> str:
        """循環パスを含むエラーメッセージを生成"""
        base_msg = super()._format_message()
        cycle_str = " -> ".join(self.cycle)
        return f"{base_msg}\n循環パス: {cycle_str}"


class ConfigurationError(AnalysisError):
    """
    設定エラー

    無効な設定が指定された場合に発生します。
    """

    pass


class InputValidationError(ValueError):
    """
    入力検証エラー

    ValueError を継承してPythonの標準エラーハイアラキーに統合し、
    入力値の型や形式が不正な場合にキャッチされるようにします。
    """

    def __init__(self, validation_error: Exception) -> None:
        """
        InputValidationErrorを初期化します。

        Args:
            validation_error: 元のバリデーションエラー
        """
        super().__init__(f"入力の検証に失敗しました: {validation_error}")


class InvalidAnalysisModeError(ValueError):
    """
    無効な解析モードエラー

    ValueError を継承してPythonの標準エラーハイアラキーに統合し、
    指定された解析モードが無効な場合にキャッチされるようにします。
    """

    def __init__(self, mode: str, valid_modes: list[str]) -> None:
        """
        InvalidAnalysisModeErrorを初期化します。

        Args:
            mode: 指定された無効なモード
            valid_modes: 有効なモードのリスト
        """
        super().__init__(f"無効な解析モード: {mode}. {', '.join(valid_modes)} のいずれかを指定してください。")


class InvalidInputTypeError(TypeError):
    """
    無効な入力型エラー

    TypeError を継承してPythonの標準エラーハイアラキーに統合し、
    入力値の型が予期されない場合にキャッチされるようにします。
    """

    def __init__(self, received_type: type) -> None:
        """
        InvalidInputTypeErrorを初期化します。

        Args:
            received_type: 受け取った型
        """
        super().__init__(f"input_pathはPathまたはstrである必要があります。受け取った型: {received_type.__name__}")
