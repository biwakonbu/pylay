#!/usr/bin/env python3
"""pylay CLIツール

Pythonの型情報とドキュメントを相互変換するコマンドラインツール
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.core.converters.yaml_to_type import yaml_to_spec, generate_pydantic_model
from src.core.doc_generators.yaml_doc_generator import generate_yaml_docs
from src.core.schemas.yaml_type_spec import TypeSpec
from src.cli.commands.type_to_yaml import run_type_to_yaml
from src.cli.commands.yaml_to_type import run_yaml_to_type


class PylayCLI:
    """pylay CLIツールのメインクラス"""

    def __init__(self) -> None:
        """CLIツールを初期化する"""
        self.console = Console()
        self.parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        """コマンドライン引数パーサーを作成する

        Returns:
            設定済みのArgumentParserインスタンス
        """
        parser = argparse.ArgumentParser(
            prog="pylay",
            description="[bold blue]pylay[/bold blue] - Python の type hint と docstrings を利用した types <-> docs 間の透過的なジェネレータ",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
[bold cyan]使用例:[/bold cyan]
  pylay type-to-yaml --input src/my_module.py --output types.yaml
  pylay yaml-to-type --input types.yaml --output src/generated_types.py
  pylay generate-docs --input types.yaml --output docs/

[bold cyan]非対話モードのみ使用可能です[/bold cyan]
            """,
        )

        subparsers = parser.add_subparsers(dest="command", help="実行するコマンド")

        # type-to-yaml コマンド
        type_to_yaml_parser = subparsers.add_parser(
            "type-to-yaml",
            help="Python型定義をYAML型仕様に変換",
        )
        type_to_yaml_parser.add_argument(
            "--input",
            "-i",
            required=True,
            help="入力Pythonファイルのパス",
        )
        type_to_yaml_parser.add_argument(
            "--output",
            "-o",
            required=True,
            help="出力YAMLファイルのパス",
        )
        type_to_yaml_parser.add_argument(
            "--module-name",
            "-m",
            help="解析対象のモジュール名（指定しない場合はファイル名から自動判定）",
        )

        # yaml-to-type コマンド
        yaml_to_type_parser = subparsers.add_parser(
            "yaml-to-type",
            help="YAML型仕様をPython型定義に変換",
        )
        yaml_to_type_parser.add_argument(
            "--input",
            "-i",
            required=True,
            help="入力YAMLファイルのパス",
        )
        yaml_to_type_parser.add_argument(
            "--output",
            "-o",
            required=True,
            help="出力Pythonファイルのパス",
        )

        # generate-docs コマンド
        docs_parser = subparsers.add_parser(
            "generate-docs",
            help="YAML型仕様からMarkdownドキュメントを生成",
        )
        docs_parser.add_argument(
            "--input",
            "-i",
            required=True,
            help="入力YAMLファイルのパス",
        )
        docs_parser.add_argument(
            "--output",
            "-o",
            required=True,
            help="出力Markdownファイルまたはディレクトリのパス",
        )
        docs_parser.add_argument(
            "--format",
            choices=["single", "multiple"],
            default="single",
            help="出力形式（single: 単一ファイル, multiple: 複数ファイル）",
        )

        # infer-deps コマンド
        infer_deps_parser = subparsers.add_parser(
            "infer-deps",
            help="型推論と依存関係抽出を実行",
        )
        infer_deps_parser.add_argument(
            "--input",
            "-i",
            required=True,
            help="入力Pythonファイルのパス",
        )
        infer_deps_parser.add_argument(
            "--visualize",
            "-v",
            action="store_true",
            help="Graphvizで依存関係を視覚化",
        )

        return parser

    def run_type_to_yaml(
        self, input_path: str, output_path: str, module_name: Optional[str] = None
    ) -> None:
        """Python型定義をYAML型仕様に変換する

        Args:
            input_path: 入力Pythonファイルのパス
            output_path: 出力YAMLファイルのパス
            module_name: 解析対象のモジュール名
        """
        try:
            # 外部コマンドを呼び出す
            run_type_to_yaml(input_path, output_path, module_name)
            self._show_success_message(
                "型定義をYAMLに変換しました",
                {
                    "入力": input_path,
                    "出力": output_path,
                },
            )
        except Exception as e:
            self._show_error_message("型定義の変換に失敗しました", str(e))

    def run_yaml_to_type(self, input_path: str, output_path: str) -> None:
        """YAML型仕様をPython型定義に変換する

        Args:
            input_path: 入力YAMLファイルのパス
            output_path: 出力Pythonファイルのパス
        """
        try:
            # 外部コマンドを呼び出す
            run_yaml_to_type(input_path, output_path)
            self._show_success_message(
                "YAMLを型定義に変換しました",
                {
                    "入力": input_path,
                    "出力": output_path,
                },
            )
        except Exception as e:
            self._show_error_message("YAMLの変換に失敗しました", str(e))

    def run_generate_docs(
        self, input_path: str, output_path: str, format_type: str = "single"
    ) -> None:
        """YAML型仕様からMarkdownドキュメントを生成する

        Args:
            input_path: 入力YAMLファイルのパス
            output_path: 出力Markdownファイルまたはディレクトリのパス
            format_type: 出力形式（"single" または "multiple"）
        """
        try:
            input_file = Path(input_path)
            output_path_obj = Path(output_path)

            if not input_file.exists():
                self.console.print(
                    f"[red]❌ エラー: 入力ファイル '{input_path}' が存在しません[/red]"
                )
                sys.exit(1)

            # プログレス表示で処理中を示す
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
            ) as progress:
                task = progress.add_task("📖 YAMLファイルを解析中...", total=None)

                # YAMLファイルからTypeSpecを読み込み
                with open(input_file, "r", encoding="utf-8") as f:
                    yaml_str = f.read()
                type_spec = yaml_to_spec(yaml_str)
                if isinstance(type_spec, TypeSpec):
                    progress.update(task, description="📝 TypeSpecを検証中...")

                    # ドキュメント生成
                    generate_yaml_docs(
                        spec=type_spec,
                        output_dir=output_path,
                    )
                    progress.update(
                        task, description="📄 Markdownドキュメントを生成中..."
                    )
                elif hasattr(type_spec, "types") and type_spec.types:
                    # TypeRootの場合、最初の型を使用
                    first_spec = next(iter(type_spec.types.values()))
                    progress.update(
                        task, description="📝 TypeRootから最初のTypeSpecを抽出中..."
                    )

                    generate_yaml_docs(
                        spec=first_spec,
                        output_dir=output_path,
                    )
                    progress.update(
                        task, description="📄 Markdownドキュメントを生成中..."
                    )
                else:
                    progress.update(task, description="⚠️ 無効な型仕様...")

            # 結果を表示
            self._show_success_message(
                "Markdownドキュメントを生成しました",
                {"入力": input_path, "出力": output_path, "形式": format_type},
            )

        except Exception as e:
            self._show_error_message("ドキュメント生成に失敗しました", str(e))

    def run_infer_deps(self, input_path: str, visualize: bool = False) -> None:
        """型推論と依存関係抽出を実行する

        Args:
            input_path: 入力Pythonファイルのパス
            visualize: Graphviz視覚化を実行するかどうか
        """
        try:
            input_file = Path(input_path)

            if not input_file.exists():
                self.console.print(
                    f"[red]❌ エラー: 入力ファイル '{input_path}' が存在しません[/red]"
                )
                sys.exit(1)

            # プログレス表示で処理中を示す
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
            ) as progress:
                task = progress.add_task("🔍 型推論を実行中...", total=None)

                # 型推論を実行
                from src.core.converters.infer_types import (
                    infer_types_from_file,
                    extract_existing_annotations,
                    merge_inferred_types,
                )

                existing_annotations = extract_existing_annotations(input_path)
                inferred_types = infer_types_from_file(input_path)
                merged_types = merge_inferred_types(
                    existing_annotations, inferred_types
                )

                progress.update(task, description="📊 依存関係を抽出中...")

                # 依存関係抽出
                from src.core.converters.ast_dependency_extractor import (
                    ASTDependencyExtractor,
                )

                extractor = ASTDependencyExtractor()
                graph = extractor.extract_dependencies(input_path, include_mypy=True)

                progress.update(task, description="📄 結果を保存中...")

                # 結果を表示
                self.console.print(f"\n[bold green]✅ 型推論完了[/bold green]")
                if merged_types:
                    table = Table(title="推論された型", show_header=True)
                    table.add_column("変数名", style="cyan")
                    table.add_column("型", style="white")
                    for var, typ in merged_types.items():
                        table.add_row(var, str(typ))
                    self.console.print(table)

                self.console.print(f"\n[bold green]✅ 依存関係抽出完了[/bold green]")
                self.console.print(f"ノード数: {len(graph.nodes)}")
                self.console.print(f"エッジ数: {len(graph.edges)}")

                # 視覚化オプション
                if visualize:
                    progress.update(task, description="🎨 視覚化中...")
                    from src.core.extract_deps import visualize_dependencies

                    output_image = f"{input_path}.deps.png"
                    visualize_dependencies(graph, output_image)
                    self.console.print(
                        f"📊 依存関係グラフを {output_image} に保存しました"
                    )

            # 結果を表示
            self._show_success_message(
                "型推論と依存関係抽出が完了しました",
                {
                    "入力": input_path,
                    "ノード数": str(len(graph.nodes)),
                    "エッジ数": str(len(graph.edges)),
                    "視覚化": "実行" if visualize else "スキップ",
                },
            )

        except Exception as e:
            self._show_error_message("型推論と依存関係抽出に失敗しました", str(e))

    def _show_success_message(self, message: str, details: dict[str, str]) -> None:
        """成功メッセージを表示する"""
        table = Table(title=f"✅ {message}", show_header=False, box=None)
        table.add_column("項目", style="cyan", width=12)
        table.add_column("値", style="white")

        for key, value in details.items():
            table.add_row(key, value)

        self.console.print(table)

    def _show_error_message(self, message: str, error: str) -> None:
        """エラーメッセージを表示する"""
        self.console.print(f"[red]❌ エラー: {message}[/red]")
        self.console.print(f"[red]詳細: {error}[/red]")
        sys.exit(1)


def main() -> None:
    """メインエントリーポイント"""
    cli = PylayCLI()
    args = cli.parser.parse_args()

    if not args.command:
        cli.parser.print_help()
        sys.exit(1)

    try:
        if args.command == "type-to-yaml":
            cli.run_type_to_yaml(args.input, args.output, args.module_name)
        elif args.command == "yaml-to-type":
            cli.run_yaml_to_type(args.input, args.output)
        elif args.command == "generate-docs":
            cli.run_generate_docs(args.input, args.output, args.format)
        elif args.command == "infer-deps":
            cli.run_infer_deps(args.input, args.visualize)
        else:
            cli.parser.print_help()
            sys.exit(1)

    except KeyboardInterrupt:
        cli.console.print("\n[yellow]⚠️  処理が中断されました[/yellow]")
        sys.exit(1)
    except Exception as e:
        cli._show_error_message("予期しないエラーが発生しました", str(e))


if __name__ == "__main__":
    main()
