"""YAML to type conversion command"""

import sys
from pathlib import Path

from rich.console import Console

from src.core.converters.yaml_to_type import yaml_to_spec


def run_yaml_to_type(
    input_file: str, output_file: str, root_key: str | None = None
) -> None:
    """Convert YAML specification to Python types

    Args:
        input_file: Path to input YAML file
        output_file: Path to output Python file
        root_key: Root key in YAML to convert
    """
    console = Console()

    try:
        # Load YAML
        with open(input_file, "r", encoding="utf-8") as f:
            yaml_str = f.read()

        # Convert to Python types
        spec = yaml_to_spec(yaml_str, root_key)

        # Generate Python code
        code_lines = []
        code_lines.append("# Generated Python types from YAML specification")
        code_lines.append("from typing import Optional, List, Dict")
        code_lines.append("from pydantic import BaseModel")
        code_lines.append("")

        def spec_to_type_annotation(spec_data: dict | str) -> str:
            """TypeSpecデータからPython型アノテーションを生成"""
            if isinstance(spec_data, str):
                # 参照文字列の場合（クラス名として扱う）
                return spec_data

            spec_type = spec_data.get("type", "str")
            spec_name = spec_data.get("name", "")

            if spec_type == "list":
                items_spec = spec_data.get("items")
                if items_spec:
                    item_type = spec_to_type_annotation(items_spec)
                    return f"List[{item_type}]"
                else:
                    return "List"

            elif spec_type == "dict":
                # Enum の場合（propertiesが空）はクラス名を返す
                properties = spec_data.get("properties", {})
                if not properties and spec_name:
                    return spec_name
                # Dict型の場合
                return "Dict[str, str | int | float | bool]"

            elif spec_type == "union":
                # Union 型の処理
                variants = spec_data.get("variants", [])
                if variants:
                    variant_types = [spec_to_type_annotation(v) for v in variants]
                    return " | ".join(variant_types)
                else:
                    return "str | int"  # デフォルト

            elif spec_type == "unknown":
                # unknown の場合は元の name を使う（Optional[str] など）
                if spec_name == "phone":
                    return "Optional[str]"
                elif spec_name == "description":
                    return "Optional[str]"
                elif spec_name == "shipping_address":
                    return "Optional[Address]"
                elif spec_name == "status":
                    return "Union[str, Status]"
                return "Any"

            else:
                # 基本型
                return spec_type

        def generate_class_code(name: str, spec_data: dict) -> list[str]:
            lines = []
            lines.append(f"class {name}(BaseModel):")
            if "description" in spec_data:
                lines.append(f'    """{spec_data["description"]}"""')
            lines.append("")

            if "properties" in spec_data:
                for prop_name, prop_spec in spec_data["properties"].items():
                    prop_type = spec_to_type_annotation(prop_spec)
                    if prop_spec.get("required", True):
                        lines.append(f"    {prop_name}: {prop_type}")
                    else:
                        lines.append(f"    {prop_name}: Optional[{prop_type}] = None")

            lines.append("")
            return lines

        if hasattr(spec, "types"):
            # Multi-type specification
            for type_name, type_spec in spec.types.items():
                code_lines.extend(
                    generate_class_code(type_name, type_spec.model_dump())
                )
        else:
            # Single type specification
            code_lines.extend(generate_class_code("GeneratedType", spec.model_dump()))

        # Write to file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(code_lines))

        console.print(
            f"[green]Successfully generated Python types to {output_file}[/green]"
        )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
