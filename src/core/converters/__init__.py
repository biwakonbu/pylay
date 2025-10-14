"""
型抽出モジュールのパッケージ初期化。

このモジュールは、型変換機能を提供します。
主な機能：
- Python型からYAMLへの変換
- YAMLからPython型への変換
- 依存関係の抽出とグラフ化
- ドキュメント生成支援
"""

# 型定義のエクスポート
# 既存の実装関数
from .extract_deps import (
    convert_graph_to_yaml_spec,
    extract_dependencies_from_code,
    extract_dependencies_from_file,
)

# モデルのエクスポート
from .models import (
    DependencyProcessingService,
    ModuleExtractionService,
    ProcessingResult,
    TypeConversionService,
    YamlProcessingService,
)

# プロトコルのエクスポート
from .protocols import (
    GraphConverterProtocol,
    ModuleExtractorProtocol,
    ResultHandlerProtocol,
    TypeConverterProtocol,
    YamlConverterProtocol,
)
from .type_to_yaml import (
    extract_types_from_module,
    graph_to_yaml,
    type_to_spec,
    type_to_yaml,
    types_to_yaml,
)
from .types import (
    CodeString,
    ConversionResult,
    DependencyGraphConfig,
    DependencyResult,
    ExtractionResult,
    MaxDepth,
    ModuleExtractionConfig,
    # 型エイリアス
    ModulePath,
    OutputPath,
    PositiveInt,
    TypeConversionConfig,
    TypeName,
    ValidatedModulePath,
    VisualizationConfig,
    YamlOutputConfig,
    YamlString,
)
from .yaml_to_type import (
    generate_pydantic_model,
    validate_with_spec,
    yaml_to_spec,
)

# 実装クラスのエクスポート

__all__ = [
    "CodeString",
    # 型定義
    "ConversionResult",
    "DependencyGraphConfig",
    "DependencyProcessingService",
    "DependencyResult",
    "ExtractionResult",
    "GraphConverterProtocol",
    "MaxDepth",
    "ModuleExtractionConfig",
    "ModuleExtractionService",
    "ModuleExtractorProtocol",
    # 型エイリアス
    "ModulePath",
    "OutputPath",
    "PositiveInt",
    "ProcessingResult",
    "ResultHandlerProtocol",
    "TypeConversionConfig",
    # モデル
    "TypeConversionService",
    # プロトコル
    "TypeConverterProtocol",
    "TypeName",
    "ValidatedModulePath",
    "VisualizationConfig",
    "YamlConverterProtocol",
    "YamlOutputConfig",
    "YamlProcessingService",
    "YamlString",
    "convert_graph_to_yaml_spec",
    # 実装関数
    "extract_dependencies_from_code",
    "extract_dependencies_from_file",
    "extract_types_from_module",
    "generate_pydantic_model",
    "graph_to_yaml",
    "type_to_spec",
    "type_to_yaml",
    "types_to_yaml",
    "validate_with_spec",
    "yaml_to_spec",
]
