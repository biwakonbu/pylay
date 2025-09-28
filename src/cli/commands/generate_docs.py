"""Documentation generation command"""

import sys
from pathlib import Path

from rich.console import Console

from src.core.doc_generators.yaml_doc_generator import YamlDocGenerator
from src.core.converters.yaml_to_type import yaml_to_spec


def run_generate_docs(
    input_file: str, output_dir: str, format_type: str = "single"
) -> None:
    """Generate documentation from YAML specification

    Args:
        input_file: Path to input YAML file
        output_dir: Output directory for documentation
        format_type: Output format ("single" or "multiple")
    """
    console = Console()

    try:
        # Load YAML
        with open(input_file, "r", encoding="utf-8") as f:
            yaml_str = f.read()

        spec = yaml_to_spec(yaml_str)

        # Handle TypeRoot (multi-type) by using the first type
        if hasattr(spec, "types") and spec.types:
            spec = next(iter(spec.types.values()))

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate documentation
        generator = YamlDocGenerator()

        if format_type == "single":
            # Single file output
            output_file = output_path / "types.md"
            generator.generate(output_file, spec=spec)
        else:
            # Multiple files output (not implemented yet)
            console.print(
                "[yellow]Multiple file format not yet implemented, using single file[/yellow]"
            )
            output_file = output_path / "types.md"
            generator.generate(output_file, spec=spec)

        console.print(
            f"[green]Successfully generated documentation to {output_file}[/green]"
        )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
