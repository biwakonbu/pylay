"""Type to YAML conversion command"""

import sys
from pathlib import Path
from typing import Any

from rich.console import Console

from src.core.converters.type_to_yaml import type_to_yaml, types_to_yaml
from src.core.schemas.yaml_type_spec import TypeSpec
from enum import Enum


def run_type_to_yaml(
    input_file: str, output_file: str, root_key: str | None = None
) -> None:
    """Convert Python type to YAML specification

    Args:
        input_file: Path to Python module file
        output_file: Output YAML file path
        root_key: Root key for the YAML structure
    """
    console = Console()

    try:
        # Import the module
        sys.path.insert(0, str(Path(input_file).parent))
        module_name = Path(input_file).stem

        # Import the module dynamically
        import importlib

        module = importlib.import_module(module_name)

        # Find all type annotations in the module
        types_dict = {}
        for name, obj in module.__dict__.items():
            # Filter for user-defined classes: Pydantic models or Enums defined in this module
            if isinstance(obj, type):
                # Check if it's a Pydantic model (BaseModel subclass with annotations)
                is_pydantic_model = (
                    hasattr(obj, "__annotations__")
                    and hasattr(obj, "__pydantic_core_schema__")  # Pydantic v2
                )
                is_enum = issubclass(obj, Enum)
                is_user_defined = getattr(obj, "__module__", None) == module_name

                if (is_pydantic_model or is_enum) and is_user_defined:
                    try:
                        types_dict[name] = obj
                    except Exception as e:
                        console.print(
                            f"[yellow]Warning: Failed to process {name}: {e}[/yellow]"
                        )

        if not types_dict:
            console.print("[red]No convertible types found in the module[/red]")
            return

        # Convert types to YAML
        types_to_yaml(types_dict, output_file)

        console.print(f"[green]Successfully converted types to {output_file}[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
