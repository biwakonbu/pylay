"""
型変換モジュールのプロトコル定義

このモジュールでは、型変換機能で使用するProtocolインターフェースを定義します。
主に以下のカテゴリのプロトコルを定義します：

1. 型変換関連のプロトコル
2. YAML出力関連のプロトコル
3. モジュール解析関連のプロトコル
4. 依存関係抽出関連のプロトコル
"""

from abc import abstractmethod
from typing import Any, Protocol

from src.core.schemas.graph import TypeDependencyGraph
from src.core.schemas.yaml_spec import TypeSpec

from .types import (
    CodeString,
    ConversionResult,
    DependencyResult,
    ExtractionResult,
    ModulePath,
    OutputPath,
    TypeName,
    YamlString,
)


class TypeConverterProtocol(Protocol):
    """
    型変換機能の基本プロトコル

    このプロトコルは、型変換機能の基本的なインターフェースを定義します。
    """

    @abstractmethod
    def convert_type_to_spec(self, typ: type[Any]) -> TypeSpec:
        """
        Python型をTypeSpecに変換します。

        Args:
            typ: 変換対象のPython型

        Returns:
            TypeSpec形式の型仕様
        """
        ...

    @abstractmethod
    def convert_type_to_yaml(
        self, typ: type[Any], output_file: OutputPath = None, as_root: bool = True
    ) -> YamlString | dict[str, Any]:
        """
        Python型をYAML文字列に変換します。

        Args:
            typ: 変換対象のPython型
            output_file: 出力ファイルパス（Noneの場合、文字列として返す）
            as_root: ルートレベルで出力するか

        Returns:
            YAML形式の文字列または辞書
        """
        ...

    @abstractmethod
    def convert_types_to_yaml(
        self, types: dict[TypeName, type[Any]], output_file: OutputPath = None
    ) -> YamlString:
        """
        複数のPython型をYAML文字列に変換します。

        Args:
            types: 型名と型の辞書
            output_file: 出力ファイルパス（Noneの場合、文字列として返す）

        Returns:
            YAML形式の文字列
        """
        ...


class YamlConverterProtocol(Protocol):
    """
    YAML変換機能のプロトコル

    このプロトコルは、YAML関連の変換機能のインターフェースを定義します。
    """

    @abstractmethod
    def convert_yaml_to_spec(
        self, yaml_str: YamlString, root_key: TypeName | None = None
    ) -> TypeSpec | Any:
        """
        YAML文字列からTypeSpecを生成します。

        Args:
            yaml_str: YAML形式の文字列
            root_key: ルートキーの名前（Noneの場合、自動検出）

        Returns:
            TypeSpecまたはその他のオブジェクト
        """
        ...

    @abstractmethod
    def validate_with_spec(
        self,
        spec: TypeSpec | str,
        data: Any,
        max_depth: int = 10,
        current_depth: int = 0,
    ) -> bool:
        """
        TypeSpecに基づいてデータをバリデーションします。

        Args:
            spec: バリデーションに使用するTypeSpecまたは参照文字列
            data: バリデーション対象のデータ
            max_depth: 最大再帰深さ
            current_depth: 現在の再帰深さ

        Returns:
            バリデーション結果（True/False）
        """
        ...

    @abstractmethod
    def generate_pydantic_model(
        self, spec: TypeSpec, model_name: str = "DynamicModel"
    ) -> CodeString:
        """
        TypeSpecからPydanticモデルコードを生成します。

        Args:
            spec: コード生成元のTypeSpec
            model_name: 生成するモデル名

        Returns:
            Pydanticモデルコードの文字列
        """
        ...


class ModuleExtractorProtocol(Protocol):
    """
    モジュール解析機能のプロトコル

    このプロトコルは、Pythonモジュールからの型抽出機能のインターフェースを定義します。
    """

    @abstractmethod
    def extract_types_from_module(self, module_path: ModulePath) -> YamlString | None:
        """
        Pythonモジュールから型を抽出してYAML形式で返します。

        Args:
            module_path: Pythonモジュールのパス

        Returns:
            YAML形式の型定義文字列、または型定義がない場合None
        """
        ...

    @abstractmethod
    def extract_dependencies_from_code(self, code: CodeString) -> TypeDependencyGraph:
        """
        コードから依存関係を抽出します。

        Args:
            code: 解析対象のPythonコード

        Returns:
            型依存関係グラフ
        """
        ...

    @abstractmethod
    def extract_dependencies_from_file(
        self, file_path: ModulePath
    ) -> TypeDependencyGraph:
        """
        ファイルから依存関係を抽出します。

        Args:
            file_path: Pythonファイルのパス

        Returns:
            型依存関係グラフ
        """
        ...


class GraphConverterProtocol(Protocol):
    """
    グラフ変換機能のプロトコル

    このプロトコルは、依存関係グラフの変換・処理機能のインターフェースを定義します。
    """

    @abstractmethod
    def convert_graph_to_yaml_spec(
        self,
        graph: TypeDependencyGraph,
    ) -> dict[str, Any]:
        """
        依存グラフをYAML型仕様に変換します。

        Args:
            graph: 依存関係のグラフ

        Returns:
            YAML型仕様の辞書
        """
        ...

    @abstractmethod
    def visualize_dependencies(
        self, graph: TypeDependencyGraph, output_path: OutputPath = "deps.png"
    ) -> None:
        """
        依存関係を視覚化します。

        Args:
            graph: 依存関係のグラフ
            output_path: 出力画像のパス
        """
        ...


class ResultHandlerProtocol(Protocol):
    """
    結果処理機能のプロトコル

    このプロトコルは、各種処理結果の処理機能のインターフェースを定義します。
    """

    @abstractmethod
    def handle_conversion_result(self, result: ConversionResult) -> None:
        """
        型変換結果を処理します。

        Args:
            result: 型変換処理の結果
        """
        ...

    @abstractmethod
    def handle_extraction_result(self, result: ExtractionResult) -> None:
        """
        抽出結果を処理します。

        Args:
            result: 型抽出処理の結果
        """
        ...

    @abstractmethod
    def handle_dependency_result(self, result: DependencyResult) -> None:
        """
        依存関係結果を処理します。

        Args:
            result: 依存関係抽出処理の結果
        """
        ...
