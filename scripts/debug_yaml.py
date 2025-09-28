#!/usr/bin/env python3

import yaml
from src.core.converters.yaml_to_type import yaml_to_spec

yaml_example = """
TestDict:
  type: dict
  properties:
    key:
      type: str
"""

print("YAMLデータ:")
data = yaml.safe_load(yaml_example)
print(f"data = {data}")
print(f"type(data) = {type(data)}")

print("\nyaml_to_specの結果:")
spec = yaml_to_spec(yaml_example)
print(f"spec = {spec}")
print(f"type(spec) = {type(spec)}")
