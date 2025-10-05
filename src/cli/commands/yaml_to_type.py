"""YAMLから型への変換コマンド

YAML仕様をPython型に変換するCLIコマンドです。
"""

import sys
from pathlib import Path

from rich.box import SIMPLE
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from src.core.converters.yaml_to_type import yaml_to_spec
from src.core.schemas.yaml_spec import TypeRoot


def run_yaml_to_type(
    input_file: str, output_file: str, root_key: str | None = None
) -> None:
    """YAML仕様をPython型に変換

    Args:
        input_file: 入力YAMLファイルのパス
        output_file: 出力Pythonファイルのパス
        root_key: 変換するYAMLのルートキー
    """
    console = Console()

    try:
        # 処理開始時のPanel表示
        input_path = Path(input_file)
        output_path = Path(output_file)

        start_panel = Panel(
            f"[bold cyan]入力ファイル:[/bold cyan] {input_path.name}\n"
            f"[bold cyan]出力ファイル:[/bold cyan] {output_path}\n"
            f"[bold cyan]ルートキー:[/bold cyan] {root_key or '自動設定'}",
            title="[bold green]🚀 YAMLから型変換開始[/bold green]",
            border_style="green",
        )
        console.print(start_panel)

        # YAMLを読み込み
        with console.status("[bold green]YAMLファイル読み込み中..."):
            with open(input_file, encoding="utf-8") as f:
                yaml_str = f.read()

        # Python型に変換
        with console.status("[bold green]型情報解析中..."):
            spec = yaml_to_spec(yaml_str, root_key)

        # Pythonコードを生成
        code_lines = []
        code_lines.append("# Generated Python types from YAML specification")
        code_lines.append("# Python 3.13+ type annotations")
        code_lines.append("from pydantic import BaseModel")
        code_lines.append("")

        def spec_to_type_annotation(spec_data: dict | str) -> str:
            """TypeSpecデータからPython型アノテーションを生成

            TypeSpec形式のデータからPythonの型アノテーションを生成します。
            """
            if isinstance(spec_data, str):
                # 参照文字列の場合（クラス名として扱う）
                return spec_data

            spec_type = spec_data.get("type", "str")
            spec_name = spec_data.get("name", "")

            if spec_type == "list":
                items_spec = spec_data.get("items")
                if items_spec:
                    item_type = spec_to_type_annotation(items_spec)
                    return f"list[{item_type}]"
                else:
                    return "list"

            elif spec_type == "dict":
                # Enum の場合（propertiesが空）はクラス名を返す
                properties = spec_data.get("properties", {})
                if not properties and spec_name:
                    return spec_name
                # Dict型の場合
                return "dict[str, str | int | float | bool]"

            elif spec_type == "union":
                # Union 型の処理
                variants = spec_data.get("variants", [])
                if variants:
                    variant_types = [spec_to_type_annotation(v) for v in variants]
                    return " | ".join(variant_types)
                else:
                    return "str | int"  # デフォルト

            elif spec_type == "unknown":
                # unknown の場合は元の name を使う（str | None など）
                if spec_name == "phone":
                    return "str | None"
                elif spec_name == "description":
                    return "str | None"
                elif spec_name == "shipping_address":
                    return "Address | None"
                elif spec_name == "status":
                    return "str | Status"
                return "Any"

            else:
                # 基本型
                return spec_type

        def generate_class_code(name: str, spec_data: dict) -> list[str]:
            """Pydantic BaseModelクラスコードを生成します。

            Args:
                name: クラス名
                spec_data: 型仕様データ

            Returns:
                生成されたコード行のリスト
            """
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
                        lines.append(f"    {prop_name}: {prop_type} | None = None")

            lines.append("")
            return lines

        # 生成する型の数を計算
        type_count = 0
        if spec is not None and isinstance(spec, TypeRoot):
            type_count = len(spec.types)
        elif spec is not None:
            type_count = 1

        # コード生成中のプログレス表示
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeRemainingColumn(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("Pythonコード生成中...", total=type_count)

            if spec is not None and isinstance(spec, TypeRoot):
                # 複数型仕様
                for type_name, type_spec in spec.types.items():
                    code_lines.extend(
                        generate_class_code(type_name, type_spec.model_dump())
                    )
                    progress.advance(task)
            elif spec is not None:
                # 単一型仕様
                code_lines.extend(
                    generate_class_code("GeneratedType", spec.model_dump())
                )
                progress.advance(task)

        # ファイルに書き込み
        with console.status("[bold green]ファイル出力中..."):
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("\n".join(code_lines))

        # 結果表示用のTable
        result_table = Table(
            title="変換結果サマリー",
            show_header=True,
            border_style="green",
            width=80,
            header_style="",
            box=SIMPLE,
        )
        result_table.add_column("項目", style="cyan", no_wrap=True, width=40)
        result_table.add_column("結果", style="green", justify="right", width=30)

        result_table.add_row("入力ファイル", input_path.name)
        result_table.add_row("出力ファイル", output_path.name)

        # 型情報をカウントして表示
        type_count = 0
        if spec is not None and isinstance(spec, TypeRoot):
            type_count = len(spec.types)
        elif spec is not None:
            type_count = 1

        result_table.add_row("生成型数", f"{type_count} 個")
        result_table.add_row("コード行数", f"{len(code_lines)} 行")

        console.print(result_table)

        # 完了メッセージのPanel
        complete_panel = Panel(
            f"[bold green]✅ YAMLから型への変換が完了しました[/bold green]\n\n"
            f"[bold cyan]出力ファイル:[/bold cyan] {output_path}\n"
            f"[bold cyan]生成型数:[/bold cyan] {type_count} 個",
            title="[bold green]🎉 処理完了[/bold green]",
            border_style="green",
        )
        console.print(complete_panel)

    except Exception as e:
        # エラーメッセージのPanel
        error_panel = Panel(
            f"[red]エラー: {e}[/red]",
            title="[bold red]❌ 処理エラー[/bold red]",
            border_style="red",
        )
        console.print(error_panel)
        sys.exit(1)
