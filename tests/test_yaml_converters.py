import pytest
from typing import List, Dict, Union
import tempfile
import os

from src.converters.type_to_yaml import type_to_yaml, type_to_spec
from src.converters.yaml_to_type import yaml_to_spec, validate_with_spec
from src.doc_generators.yaml_doc_generator import generate_yaml_docs
from schemas.yaml_type_spec import TypeSpec, DictTypeSpec

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname

def test_type_to_yaml():
    Users = List[Dict[str, str]]
    yaml_str = type_to_yaml(Users)
    assert "name: List" in yaml_str
    assert "type: list" in yaml_str

def test_yaml_to_spec_and_validate():
    yaml_example = """
    name: TestDict
    type: dict
    properties:
        key:
            name: key
            type: str
    """
    spec = yaml_to_spec(yaml_example)
    assert isinstance(spec, DictTypeSpec)
    valid_data = {"key": "value"}
    invalid_data = {"key": 123}
    assert validate_with_spec(spec, valid_data) is True
    assert validate_with_spec(spec, invalid_data) is False

def test_roundtrip(temp_dir):
    from src.converters.yaml_to_type import generate_pydantic_model

    # 型 -> yaml -> spec -> md
    TestType = List[str]
    yaml_str = type_to_yaml(TestType)  # ファイル出力なし

    # YAMLファイルに書き込み
    yaml_file_path = os.path.join(temp_dir, "test.yaml")
    with open(yaml_file_path, 'w') as f:
        f.write(yaml_str)

    spec = yaml_to_spec(yaml_str)
    generate_yaml_docs(spec, temp_dir)

    md_path = os.path.join(temp_dir, "List.md")
    assert os.path.exists(md_path)
    with open(md_path, 'r') as f:
        md_content = f.read()
    assert "型仕様: List" in md_content
