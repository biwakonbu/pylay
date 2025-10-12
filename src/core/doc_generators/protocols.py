"""
ドキュメント生成モジュールのプロトコル定義

このモジュールでは、ドキュメント生成機能で使用するProtocolインターフェースを定義します。
主に以下のカテゴリのプロトコルを定義します：

1. ドキュメント生成関連のプロトコル
2. 型検査関連のプロトコル
3. マークダウン生成関連のプロトコル
4. ファイルシステム関連のプロトコル
"""

from abc import abstractmethod
from pathlib import Path
from typing import Any, Protocol

from src.core.schemas.graph import TypeDependencyGraph

from .types import (
    BatchGenerationConfig,
    BatchGenerationResult,
    DocumentConfig,
    DocumentStructure,
    GenerationResult,
    MarkdownGenerationConfig,
    MarkdownSectionInfo,
    TemplateConfig,
    TypeInspectionConfig,
    TypeInspectionResult,
    TypeName,
)


class DocumentGeneratorProtocol(Protocol):
    """
    ドキュメント生成機能の基本プロトコル

    このプロトコルは、ドキュメント生成機能の基本的なインターフェースを定義します。
    """

    @abstractmethod
    def generate_document(self, config: DocumentConfig, **kwargs: Any) -> GenerationResult:
        """
        ドキュメントを生成します。

        Args:
            config: ドキュメント生成設定
            **kwargs: 追加の設定パラメータ

        Returns:
            生成結果
        """
        ...

    @abstractmethod
    def generate_from_types(
        self, types: dict[TypeName, type[Any]], output_path: str | Path, **kwargs: Any
    ) -> GenerationResult:
        """
        型定義からドキュメントを生成します。

        Args:
            types: 型定義の辞書
            output_path: 出力パス
            **kwargs: 追加の設定パラメータ

        Returns:
            生成結果
        """
        ...

    @abstractmethod
    def generate_from_graph(
        self, graph: TypeDependencyGraph, output_path: str | Path, **kwargs: Any
    ) -> GenerationResult:
        """
        依存関係グラフからドキュメントを生成します。

        Args:
            graph: 型依存関係グラフ
            output_path: 出力パス
            **kwargs: 追加の設定パラメータ

        Returns:
            生成結果
        """
        ...


class TypeInspectorProtocol(Protocol):
    """
    型検査機能のプロトコル

    このプロトコルは、型検査機能のインターフェースを定義します。
    """

    @abstractmethod
    def inspect_type(self, type_cls: type[Any], config: TypeInspectionConfig | None = None) -> TypeInspectionResult:
        """
        指定された型を検査します。

        Args:
            type_cls: 検査対象の型クラス
            config: 検査設定（Noneの場合、デフォルト設定を使用）

        Returns:
            検査結果
        """
        ...

    @abstractmethod
    def inspect_types_batch(
        self, type_classes: list[type[Any]], config: TypeInspectionConfig | None = None
    ) -> list[TypeInspectionResult]:
        """
        複数の型を一括で検査します。

        Args:
            type_classes: 検査対象の型クラスのリスト
            config: 検査設定（Noneの場合、デフォルト設定を使用）

        Returns:
            検査結果のリスト
        """
        ...

    @abstractmethod
    def extract_code_blocks(self, docstring: str) -> tuple[list[str], list[str]]:
        """
        docstringからコードブロックを抽出します。

        Args:
            docstring: 解析対象のdocstring

        Returns:
            (コードブロックのリスト, 説明テキストのリスト)のタプル
        """
        ...


class MarkdownBuilderProtocol(Protocol):
    """
    マークダウン生成機能のプロトコル

    このプロトコルは、マークダウン生成機能のインターフェースを定義します。
    """

    @abstractmethod
    def build_document(
        self,
        structure: DocumentStructure,
        config: MarkdownGenerationConfig | None = None,
    ) -> str:
        """
        ドキュメント構造からマークダウン文字列を生成します。

        Args:
            structure: ドキュメント構造
            config: マークダウン生成設定（Noneの場合、デフォルト設定を使用）

        Returns:
            生成されたマークダウン文字列
        """
        ...

    @abstractmethod
    def build_section(
        self,
        section_info: MarkdownSectionInfo,
        config: MarkdownGenerationConfig | None = None,
    ) -> str:
        """
        セクション情報からマークダウンセクションを生成します。

        Args:
            section_info: セクション情報
            config: マークダウン生成設定（Noneの場合、デフォルト設定を使用）

        Returns:
            生成されたマークダウンセクション文字列
        """
        ...

    @abstractmethod
    def build_type_documentation(
        self,
        type_name: TypeName,
        type_cls: type[Any],
        config: MarkdownGenerationConfig | None = None,
    ) -> str:
        """
        型定義からドキュメントを生成します。

        Args:
            type_name: 型名
            type_cls: 型クラス
            config: マークダウン生成設定（Noneの場合、デフォルト設定を使用）

        Returns:
            生成されたドキュメント文字列
        """
        ...


class FileSystemInterfaceProtocol(Protocol):
    """
    ファイルシステム操作機能のプロトコル

    このプロトコルは、ファイルシステム操作機能のインターフェースを定義します。
    """

    @abstractmethod
    def mkdir(self, path: str | Path, parents: bool = True, exist_ok: bool = True) -> None:
        """
        ディレクトリを作成します。

        Args:
            path: 作成するディレクトリのパス
            parents: 親ディレクトリも作成するかどうか
            exist_ok: 既に存在する場合にエラーを発生させないかどうか
        """
        ...

    @abstractmethod
    def write_text(self, path: str | Path, content: str, encoding: str = "utf-8") -> None:
        """
        テキストファイルに書き込みます。

        Args:
            path: 書き込み先のパス
            content: 書き込む内容
            encoding: エンコーディング
        """
        ...

    @abstractmethod
    def read_text(self, path: str | Path, encoding: str = "utf-8") -> str:
        """
        テキストファイルを読み込みます。

        Args:
            path: 読み込み元のパス
            encoding: エンコーディング

        Returns:
            ファイルの内容
        """
        ...

    @abstractmethod
    def exists(self, path: str | Path) -> bool:
        """
        パスが存在するかどうかを確認します。

        Args:
            path: 確認対象のパス

        Returns:
            存在する場合はTrue、そうでない場合はFalse
        """
        ...

    @abstractmethod
    def is_file(self, path: str | Path) -> bool:
        """
        パスがファイルかどうかを確認します。

        Args:
            path: 確認対象のパス

        Returns:
            ファイルの場合はTrue、そうでない場合はFalse
        """
        ...


class TemplateProcessorProtocol(Protocol):
    """
    テンプレート処理機能のプロトコル

    このプロトコルは、テンプレート処理機能のインターフェースを定義します。
    """

    @abstractmethod
    def load_template(self, template_name: str) -> str:
        """
        テンプレートを読み込みます。

        Args:
            template_name: テンプレート名

        Returns:
            テンプレートの内容
        """
        ...

    @abstractmethod
    def process_template(
        self,
        template_content: str,
        variables: dict[str, Any],
        config: TemplateConfig | None = None,
    ) -> str:
        """
        テンプレートを処理します。

        Args:
            template_content: テンプレートの内容
            variables: テンプレート変数
            config: テンプレート設定（Noneの場合、デフォルト設定を使用）

        Returns:
            処理されたテンプレート文字列
        """
        ...

    @abstractmethod
    def render_document(
        self,
        template_name: str,
        variables: dict[str, Any],
        output_path: str | Path,
        config: DocumentConfig | None = None,
    ) -> None:
        """
        テンプレートからドキュメントをレンダリングして保存します。

        Args:
            template_name: テンプレート名
            variables: テンプレート変数
            output_path: 出力パス
            config: ドキュメント設定（Noneの場合、デフォルト設定を使用）
        """
        ...


class BatchProcessorProtocol(Protocol):
    """
    バッチ処理機能のプロトコル

    このプロトコルは、バッチ処理機能のインターフェースを定義します。
    """

    @abstractmethod
    def process_batch(self, config: BatchGenerationConfig) -> BatchGenerationResult:
        """
        バッチ処理を実行します。

        Args:
            config: バッチ生成設定

        Returns:
            バッチ処理結果
        """
        ...

    @abstractmethod
    def process_directory(
        self,
        input_directory: str | Path,
        output_directory: str | Path,
        config: DocumentConfig | None = None,
    ) -> BatchGenerationResult:
        """
        ディレクトリ内のファイルを一括処理します。

        Args:
            input_directory: 入力ディレクトリ
            output_directory: 出力ディレクトリ
            config: ドキュメント設定（Noneの場合、デフォルト設定を使用）

        Returns:
            バッチ処理結果
        """
        ...
