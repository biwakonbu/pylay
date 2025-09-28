from src.core.converters.yaml_to_type import yaml_to_spec
from src.core.doc_generators.yaml_doc_generator import generate_yaml_docs


def generate_yaml_docs_from_file(
    yaml_file: str, output_dir: str = "docs/yaml_types"
) -> None:
    """YAMLファイルから型仕様を読み込み、ドキュメント生成"""
    with open(yaml_file, "r", encoding="utf-8") as f:
        yaml_str = f.read()

    spec = yaml_to_spec(yaml_str)
    if hasattr(spec, "types"):
        # TypeRootの場合、最初の型を使用
        first_type = next(iter(spec.types.values()))
        generate_yaml_docs(first_type, output_dir)
    else:
        generate_yaml_docs(spec, output_dir)


if __name__ == "__main__":
    # サンプルYAMLファイルからドキュメント生成
    import tempfile
    import os

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
