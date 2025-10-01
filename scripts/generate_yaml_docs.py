from pathlib import Path

from src.core.converters.yaml_to_type import yaml_to_spec
from src.core.doc_generators.yaml_doc_generator import generate_yaml_docs
from src.core.schemas.pylay_config import PylayConfig


def generate_yaml_docs_from_file(yaml_file: str, output_dir: str | None = None) -> None:
    """YAMLファイルから型仕様を読み込み、ドキュメント生成"""
    with open(yaml_file, encoding="utf-8") as f:
        yaml_str = f.read()

    spec = yaml_to_spec(yaml_str)
    if hasattr(spec, "types"):
        # TypeRootの場合、最初の型を使用
        first_type = next(iter(spec.types.values()))
        generate_yaml_docs(first_type, output_dir)
    else:
        generate_yaml_docs(spec, output_dir)


def generate_yaml_docs_from_file_with_config(
    yaml_file: str, config_path: str | None = None
) -> None:
    """YAMLファイルから型仕様を読み込み、設定ファイルに基づいてドキュメント生成"""
    if config_path is None:
        # デフォルト設定ファイルを使用
        try:
            config = PylayConfig.from_pyproject_toml()
            config.ensure_output_structure(Path.cwd())
            documents_dir = config.get_documents_output_dir(Path.cwd())
            generate_yaml_docs_from_file(yaml_file, str(documents_dir))
        except Exception:
            # 設定ファイルがない場合はデフォルト値を使用
            generate_yaml_docs_from_file(yaml_file)
    else:
        # 指定された設定ファイルを使用
        config = PylayConfig.from_pyproject_toml(Path(config_path).parent)
        config.ensure_output_structure(Path(config_path).parent)
        documents_dir = config.get_documents_output_dir(Path(config_path).parent)
        generate_yaml_docs_from_file(yaml_file, str(documents_dir))


if __name__ == "__main__":
    # サンプルYAMLファイルからドキュメント生成
    import os
    import tempfile

    sample_yaml = """
name: SampleUser
type: dict
description: サンプルユーザータイプ
properties:
  id:
    name: id
    type: int
    description: ユーザーID
    required: true
  name:
    name: name
    type: str
    description: ユーザー名
    required: true
  age:
    name: age
    type: int
    description: 年齢
    required: false
"""

    # 一時ファイルにYAMLを書き込み
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        f.write(sample_yaml)
        yaml_file = f.name

    try:
        generate_yaml_docs_from_file(yaml_file)
        print("✅ サンプルドキュメントを生成しました")
    finally:
        os.unlink(yaml_file)
