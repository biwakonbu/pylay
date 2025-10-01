"""型からYAMLへの変換コマンド

Pythonの型定義をYAML形式に変換するCLIコマンドです。
"""

import sys
from enum import Enum
from pathlib import Path

from rich.console import Console

from src.core.converters.type_to_yaml import types_to_yaml


def run_type_to_yaml(
    input_file: str, output_file: str, root_key: str | None = None
) -> None:
    """Python型をYAML仕様に変換

    Args:
        input_file: Pythonモジュールファイルのパス
        output_file: 出力YAMLファイルのパス
        root_key: YAML構造のルートキー
    """
    console = Console()

    try:
        # モジュールをインポート
        sys.path.insert(0, str(Path(input_file).parent))
        module_name = Path(input_file).stem

        # モジュールをインポート dynamically
        import importlib

        module = importlib.import_module(module_name)

        # モジュール内の全型アノテーションを検索
        types_dict = {}
        for name, obj in module.__dict__.items():
            # ユーザ定義クラスをフィルタリング: このモジュールで定義されたPydanticモデルまたはEnum
            if isinstance(obj, type):
                # Pydanticモデルかどうかをチェック（BaseModelのサブクラスでアノテーションを持つ）
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

        # 型をYAMLに変換
        types_to_yaml(types_dict, output_file)

        console.print(f"[green]Successfully converted types to {output_file}[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
