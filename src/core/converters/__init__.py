"""
型抽出モジュールのパッケージ初期化。

このモジュールは、型変換機能を提供します。
主な機能：
- Python型からYAMLへの変換
- YAMLからPython型への変換
- 依存関係の抽出とグラフ化
- ドキュメント生成支援

注意: このパッケージは最小限の安定した公開APIのみを提供します。
詳細な機能が必要な場合は、各モジュールを個別にインポートしてください。
"""

# 主要な公開APIのみエクスポート
from .extract_deps import extract_dependencies_from_file
from .type_to_yaml import extract_types_from_module, type_to_yaml, types_to_yaml
from .yaml_to_type import generate_pydantic_model, yaml_to_spec

__all__ = [
    # 依存関係抽出関数
    "extract_dependencies_from_file",
    # 主要な型変換関数
    "extract_types_from_module",
    "generate_pydantic_model",
    "type_to_yaml",
    "types_to_yaml",
    "yaml_to_spec",
]
