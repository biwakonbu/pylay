"""
型変換モジュールのドメインモデル

このモジュールでは、型変換機能のビジネスロジックを含むドメインモデルを定義します。
主に以下のカテゴリのモデルを定義します：

1. 型変換処理のビジネスモデル
2. YAML処理のビジネスモデル
3. モジュール解析のビジネスモデル
4. 依存関係処理のビジネスモデル
"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.core.schemas.graph import TypeDependencyGraph
from src.core.schemas.yaml_spec import TypeSpec

from .types import (
    ConversionResult,
    DependencyResult,
    ExtractionResult,
    ModulePath,
    OutputPath,
    TypeName,
    YamlString,
)


class TypeConversionService(BaseModel):
    """
    型変換処理のサービスクラス

    このクラスは、型変換処理のビジネスロジックを実装します。
    """

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
        # ここでは簡易的な実装を提供
        # 実際の実装は実装ファイルに委譲する形になる
        spec = self._convert_type_to_spec(typ)
        yaml_data = self._spec_to_yaml_data(spec, as_root)

        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            import ruamel.yaml

            yaml_parser = ruamel.yaml.YAML()
            yaml_parser.preserve_quotes = True
            with open(output_path, "w", encoding="utf-8") as f:
                if as_root:
                    yaml_parser.dump({self._get_type_name(typ): yaml_data}, f)
                else:
                    yaml_parser.dump(yaml_data, f)

        return {self._get_type_name(typ): yaml_data} if as_root else yaml_data

    def _convert_type_to_spec(self, typ: type[Any]) -> TypeSpec:
        """型をTypeSpecに変換する内部メソッド"""
        # 簡易的な実装（実際はより複雑な処理が必要）
        from src.core.schemas.yaml_spec import TypeSpec as TypeSpecModel

        return TypeSpecModel(
            type=self._get_basic_type_str(typ),
            name=self._get_type_name(typ),
            description="",
            required=True,
        )

    def _spec_to_yaml_data(self, spec: TypeSpec, as_root: bool) -> dict[str, Any]:
        """TypeSpecをYAMLデータに変換する内部メソッド"""
        # 簡易的な実装（実際はより複雑な処理が必要）
        return {"type": spec.type}

    def _get_type_name(self, typ: type[Any]) -> str:
        """型の名前を取得する内部メソッド"""
        if hasattr(typ, "__name__"):
            return typ.__name__
        return str(typ)

    def _get_basic_type_str(self, typ: type[Any]) -> str:
        """基本型の型文字列を取得する内部メソッド"""
        basic_type_mapping = {
            str: "str",
            int: "int",
            float: "float",
            bool: "bool",
        }
        return basic_type_mapping.get(typ, "any")


class YamlProcessingService(BaseModel):
    """
    YAML処理のサービスクラス

    このクラスは、YAML関連の処理のビジネスロジックを実装します。
    """

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
        # 簡易的な実装（実際はより複雑な処理が必要）
        import ruamel.yaml

        yaml_parser = ruamel.yaml.YAML(typ="safe")
        data = yaml_parser.load(yaml_str)

        if isinstance(data, dict):
            if not root_key and len(data) == 1:
                root_key = list(data.keys())[0]
                data = data[root_key]

            from src.core.schemas.yaml_spec import TypeSpec as TypeSpecModel

            return TypeSpecModel(
                type=data.get("type", "unknown"),
                name=root_key or "Unknown",
                description=data.get("description"),
                required=data.get("required", True),
            )

        return data

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
        if current_depth > max_depth:
            return False

        try:
            if isinstance(spec, str):
                # 参照文字列の場合は常にTrue（実際の解決は別途）
                return True

            if isinstance(spec, TypeSpec):
                return self._validate_basic_type(spec, data)

            return False
        except Exception:
            return False

    def _validate_basic_type(self, spec: TypeSpec, data: Any) -> bool:
        """基本型のバリデーションを行う内部メソッド"""
        type_map = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
        }

        expected_type = type_map.get(spec.type)
        if expected_type is None:
            return spec.type == "any"

        return isinstance(data, expected_type)


class ModuleExtractionService(BaseModel):
    """
    モジュール解析のサービスクラス

    このクラスは、Pythonモジュールからの型抽出処理のビジネスロジックを実装します。
    """

    def extract_types_from_module(self, module_path: ModulePath) -> YamlString | None:
        """
        Pythonモジュールから型を抽出してYAML形式で返します。

        Args:
            module_path: Pythonモジュールのパス

        Returns:
            YAML形式の型定義文字列、または型定義がない場合None
        """
        try:
            path = Path(module_path)
            if not path.exists():
                return None

            # 簡易的な実装（実際はAST解析が必要）
            # ここではファイルサイズと更新時間をチェックする簡易版
            stat = path.stat()
            if stat.st_size > 10 * 1024 * 1024:  # 10MB以上はスキップ
                return None

            # 実際の実装ではAST解析で型定義を抽出する
            import ast

            with open(path, encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source)
            type_definitions = {}

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_name = node.name
                    type_definitions[class_name] = {
                        "type": "class",
                        "docstring": ast.get_docstring(node),
                    }

            if type_definitions:
                import ruamel.yaml

                yaml_parser = ruamel.yaml.YAML()
                yaml_parser.preserve_quotes = True

                from io import StringIO

                output = StringIO()
                yaml_parser.dump(type_definitions, output)
                return output.getvalue().strip()

            return None

        except Exception:
            return None


class DependencyProcessingService(BaseModel):
    """
    依存関係処理のサービスクラス

    このクラスは、依存関係の抽出・処理・可視化のビジネスロジックを実装します。
    """

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
        # 簡易的な実装（実際はより複雑なAST解析が必要）
        from src.core.converters.extract_deps import extract_dependencies_from_file

        return extract_dependencies_from_file(file_path)

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
        # 簡易的な実装（実際はより複雑な処理が必要）
        from src.core.converters.extract_deps import convert_graph_to_yaml_spec

        return convert_graph_to_yaml_spec(graph)

    def visualize_dependencies(
        self, graph: TypeDependencyGraph, output_path: OutputPath = "deps.png"
    ) -> None:
        """
        依存関係を視覚化します。

        Args:
            graph: 依存関係のグラフ
            output_path: 出力画像のパス
        """
        # 簡易的な実装（実際はより複雑な処理が必要）
        from src.core.converters.extract_deps import visualize_dependencies

        # OutputPathをstrに変換
        output_str = str(output_path) if output_path else "deps.png"
        visualize_dependencies(graph, output_str)


class ProcessingResult(BaseModel):
    """
    処理結果の集約モデル

    このクラスは、複数の処理結果をまとめて管理します。
    """

    conversion_results: list[ConversionResult] = Field(
        default_factory=list, description="型変換結果のリスト"
    )
    extraction_results: list[ExtractionResult] = Field(
        default_factory=list, description="抽出結果のリスト"
    )
    dependency_results: list[DependencyResult] = Field(
        default_factory=list, description="依存関係結果のリスト"
    )
    total_processing_time_ms: float = Field(description="総処理時間（ミリ秒）")
    start_time: float = Field(description="処理開始時間")

    @field_validator("total_processing_time_ms")
    @classmethod
    def validate_processing_time(cls, v: float) -> float:
        """処理時間を検証するバリデーター"""
        if v < 0:
            raise ValueError("処理時間は0以上である必要があります")
        return v

    def add_conversion_result(self, result: ConversionResult) -> None:
        """型変換結果を追加します。"""
        self.conversion_results.append(result)

    def add_extraction_result(self, result: ExtractionResult) -> None:
        """抽出結果を追加します。"""
        self.extraction_results.append(result)

    def add_dependency_result(self, result: DependencyResult) -> None:
        """依存関係結果を追加します。"""
        self.dependency_results.append(result)

    def get_success_rate(self) -> float:
        """成功率を計算します。"""
        total = (
            len(self.conversion_results)
            + len(self.extraction_results)
            + len(self.dependency_results)
        )
        if total == 0:
            return 0.0

        successful = sum(
            1
            for result in self.conversion_results
            + self.extraction_results
            + self.dependency_results
            if result.success
        )
        return successful / total
