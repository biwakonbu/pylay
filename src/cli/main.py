"""pylay のコマンドラインインターフェース"""

import importlib.metadata
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ..core.converters.extract_deps import extract_dependencies_from_file
from ..core.converters.type_to_yaml import extract_types_from_module
from ..core.converters.yaml_to_type import yaml_to_spec
from ..core.doc_generators.test_catalog_generator import CatalogGenerator
from ..core.doc_generators.type_doc_generator import LayerDocGenerator
from ..core.doc_generators.yaml_doc_generator import YamlDocGenerator
from ..core.output_manager import OutputPathManager
from ..core.schemas.pylay_config import PylayConfig
from .commands.analyze_types import analyze_types
from .commands.diagnose_type_ignore import diagnose_type_ignore
from .commands.docs import run_docs
from .commands.project_analyze import project_analyze
from .commands.quality import quality
from .commands.types import run_types
from .commands.yaml import run_yaml


def get_version() -> str:
    """パッケージのバージョンを取得する"""
    return importlib.metadata.version("pylay")


class PylayCLI:
    """pylay CLIツールのメインクラス"""

    def __init__(self) -> None:
        """CLIツールを初期化する"""
        self.console = Console()

    def show_success_message(self, message: str, details: dict[str, str]) -> None:
        """成功メッセージを表示する"""
        table = Table(title=f"✅ {message}", show_header=False, box=None)
        table.add_column("項目", style="cyan", width=12)
        table.add_column("値", style="white")

        for key, value in details.items():
            table.add_row(key, value)

        self.console.print(table)

    def show_error_message(self, message: str, error: str) -> None:
        """エラーメッセージを表示する"""
        self.console.print(f"[red]❌ エラー: {message}[/red]")
        self.console.print(f"[red]詳細: {error}[/red]")


cli_instance = PylayCLI()


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=get_version())
@click.option("--verbose", is_flag=True, help="詳細ログを出力")
@click.option(
    "--config", type=click.Path(exists=True), help="設定ファイルのパス (YAML)"
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool, config: str | None) -> None:
    """pylay: 型解析、自動型生成、ドキュメント生成ツール

    使用例:
        pylay generate type-docs --input module.py --output docs.md
        pylay analyze types --input module.py
        pylay convert to-yaml --input module.py --output types.yaml
        pylay convert to-type --input types.yaml --output model.py
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["config"] = config
    if verbose:
        click.echo("pylay CLI 開始 (verbose モード)")
    if config:
        click.echo(f"設定ファイル読み込み: {config}")


@cli.group()
def generate() -> None:
    """ドキュメント/型生成コマンド"""


@generate.command("type-docs")
@click.argument("input", type=click.Path(exists=True))
@click.option(
    "--output",
    type=click.Path(),
    default="docs/type_docs.md",
    help="出力 Markdown ファイル",
)
def generate_type_docs(input: str, output: str) -> None:
    """Python 型から Markdown ドキュメントを生成

    Pythonの型定義からMarkdown形式のドキュメントを生成します。
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=cli_instance.console,
        ) as progress:
            task = progress.add_task("📝 型ドキュメント生成中...", total=None)
            generator = LayerDocGenerator()
            docs = generator.generate(Path(input))
            progress.update(task, description="💾 ファイル出力中...")

        if output == "docs/type_docs.md":
            # デフォルト出力先の場合はディレクトリを作成
            Path(output).parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            f.write(docs or "")

        cli_instance.show_success_message(
            "型ドキュメント生成が完了しました",
            {"入力": input, "出力": output},
        )
    except Exception as e:
        cli_instance.show_error_message("型ドキュメント生成に失敗しました", str(e))


@generate.command("yaml-docs")
@click.argument("input", type=click.Path(exists=True))
@click.option(
    "--output",
    type=click.Path(),
    help="出力 Markdown ファイル（デフォルト: 設定ファイルに基づく）",
)
def generate_yaml_docs(input: str, output: str | None) -> None:
    """YAML 型仕様から Markdown ドキュメントを生成"""
    try:
        config = PylayConfig.from_pyproject_toml()
        output_manager = OutputPathManager(config)
        default_output = str(output_manager.get_markdown_path(filename="yaml_docs.md"))
    except Exception:
        # 設定ファイルがない場合はデフォルト値を使用
        default_output = "docs/pylay-types/documents/yaml_docs.md"

    if output is None:
        output = default_output

    try:
        with open(input, encoding="utf-8") as f:
            yaml_str = f.read()

        spec = yaml_to_spec(yaml_str)
        if spec is None:
            raise ValueError(f"Failed to parse spec from {input}")
        generator = YamlDocGenerator()
        generator.generate(Path(output), spec=spec)

        cli_instance.show_success_message(
            "YAMLドキュメント生成が完了しました",
            {"入力": input, "出力": output},
        )
    except Exception as e:
        cli_instance.show_error_message("YAMLドキュメント生成に失敗しました", str(e))


@generate.command("test-catalog")
@click.argument("input_dir", type=click.Path(exists=True))
@click.option(
    "--output",
    type=click.Path(),
    default="docs/test_catalog.md",
    help="出力 Markdown ファイル",
)
def generate_test_catalog(input_dir: str, output: str) -> None:
    """テストカタログを生成"""
    click.echo(f"テストカタログ生成: {input_dir} -> {output}")
    generator = CatalogGenerator()
    catalog = generator.generate(Path(input_dir))
    if output == "docs/test_catalog.md":
        # デフォルト出力先の場合はディレクトリを作成
        Path(output).parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        f.write(catalog or "")
    click.echo(f"生成完了: {output}")


@generate.command("dependency-graph")
@click.argument("input_dir", type=click.Path(exists=True))
@click.option(
    "--output",
    type=click.Path(),
    default="docs/dependency_graph.png",
    help="出力グラフファイル (PNG)",
)
def generate_dependency_graph(input_dir: str, output: str) -> None:
    """依存関係グラフを生成 (NetworkX + matplotlib)"""
    click.echo(f"依存グラフ生成: {input_dir} -> {output}")
    try:
        dep_graph = extract_dependencies_from_file(Path(input_dir))
        # matplotlibでグラフを生成
        import matplotlib.pyplot as plt
        import networkx as nx

        # TypeDependencyGraph.to_networkx() を使用してNetworkXグラフに変換
        nx_graph = dep_graph.to_networkx()

        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(nx_graph)
        nx.draw(
            nx_graph,
            pos,
            with_labels=True,
            node_color="lightblue",
            node_size=2000,
            font_size=10,
            font_weight="bold",
            arrowsize=20,
        )
        plt.title("Type Dependencies")
        plt.axis("off")

        if output == "docs/dependency_graph.png":
            # デフォルト出力先の場合はディレクトリを作成
            Path(output).parent.mkdir(parents=True, exist_ok=True)

        plt.savefig(output, dpi=300, bbox_inches="tight")
        plt.close()
        click.echo(f"生成完了: {output}")
    except ImportError:
        click.echo("エラー: matplotlibまたはnetworkxがインストールされていません。")
        click.echo("インストール: pip install matplotlib networkx")
    except Exception as e:
        click.echo(f"エラー: {e}")


@cli.group()
def convert() -> None:
    """型と YAML の相互変換"""


@convert.command("to-yaml")
@click.argument("input_module", type=click.Path(exists=True))
@click.option(
    "--output",
    type=click.Path(),
    default="-",
    help="出力 YAML ファイル (デフォルト: stdout)",
)
def convert_to_yaml(input_module: str, output: str) -> None:
    """Python 型を YAML に変換

    Pythonの型定義をYAML形式に変換します。
    """
    try:
        yaml_str = extract_types_from_module(Path(input_module))

        if output == "-":
            cli_instance.console.print("[bold green]YAML出力:[/bold green]")
            cli_instance.console.print(yaml_str if yaml_str is not None else "")
        else:
            with open(output, "w", encoding="utf-8") as f:
                f.write(yaml_str if yaml_str is not None else "")
            cli_instance.show_success_message(
                "型→YAML変換が完了しました",
                {"入力": input_module, "出力": output},
            )
    except Exception as e:
        cli_instance.show_error_message("型→YAML変換に失敗しました", str(e))


@convert.command("to-type")
@click.argument("input_yaml", type=click.Path(exists=True))
@click.option("--output-py", type=click.Path(), help="出力 Python コード (BaseModel)")
def convert_to_type(input_yaml: str, output_py: str | None) -> None:
    """YAML を Pydantic BaseModel に変換"""
    try:
        with open(input_yaml, encoding="utf-8") as f:
            yaml_str = f.read()

        spec = yaml_to_spec(yaml_str)
        type_names = [
            t.__name__ if hasattr(t, "__name__") else str(t)
            for t in spec.__class__.__mro__
            if t is not object
        ]
        model_code = f"""from pydantic import BaseModel
from typing import {", ".join(type_names)}

# 生成されたPydanticモデル
class GeneratedModel(BaseModel):
    pass
"""

        if output_py:
            with open(output_py, "w") as f:
                f.write(model_code)
            cli_instance.show_success_message(
                "YAML→型変換が完了しました",
                {"入力": input_yaml, "出力": output_py},
            )
        else:
            cli_instance.console.print(
                "[bold green]生成されたPythonコード:[/bold green]"
            )
            cli_instance.console.print(model_code)
    except Exception as e:
        cli_instance.show_error_message("YAML→型変換に失敗しました", str(e))


# project-analyze コマンドを追加
cli.add_command(project_analyze)


@cli.group()
def analyze() -> None:
    """型解析・依存関係分析コマンド"""


# analyze-typesコマンドを登録
# トップレベルにも登録して `pylay analyze-types` で呼び出せるようにする
cli.add_command(analyze_types)
analyze.add_command(analyze_types)

# diagnose-type-ignoreコマンドを登録
cli.add_command(diagnose_type_ignore)
analyze.add_command(diagnose_type_ignore)

# qualityコマンドを登録
cli.add_command(quality)
analyze.add_command(quality)


# 新しい1語コマンドを登録
@cli.command("yaml")
@click.argument("target", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="出力YAMLファイルのパス (デフォルト: stdout)",
)
@click.option("--root-key", help="YAML構造のルートキー")
def yaml(target: str, output: str | None, root_key: str | None) -> None:
    """Python型からYAML仕様を生成

    Pythonモジュールの型定義をYAML形式に変換します。

    使用例:
        pylay yaml src/core/schemas/types.py
        pylay yaml src/core/schemas/types.py -o types.yaml
    """
    if output is None:
        output = "-"  # stdout
    run_yaml(target, output, root_key)


@cli.command("types")
@click.argument("yaml_file", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="出力Pythonファイルのパス (デフォルト: stdout)",
)
@click.option("--root-key", help="変換するYAMLのルートキー")
def types(yaml_file: str, output: str | None, root_key: str | None) -> None:
    """YAML仕様からPython型を生成

    YAML型仕様をPydantic BaseModelに変換します。

    使用例:
        pylay types specs/api.yaml
        pylay types specs/api.yaml -o generated/models.py
    """
    if output is None:
        output = "-"  # stdout
    run_types(yaml_file, output, root_key)


@cli.command("docs")
@click.option(
    "--input",
    "-i",
    "input_file",
    type=click.Path(exists=True),
    help="入力YAMLファイル",
)
@click.option(
    "--output",
    "-o",
    "output_dir",
    type=click.Path(),
    default="docs/api",
    help="出力ディレクトリ",
)
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["single", "multiple"]),
    default="single",
    help="出力フォーマット",
)
def docs(input_file: str | None, output_dir: str, format_type: str) -> None:
    """ドキュメント生成

    YAML型仕様からMarkdownドキュメントを生成します。

    使用例:
        pylay docs
        pylay docs -i specs/api.yaml -o docs/api
        pylay docs --format markdown
    """
    if input_file is None:
        # デフォルトの入力ファイルを探す
        default_inputs = ["types.yaml", "specs/types.yaml", "docs/types.yaml"]
        for default_input in default_inputs:
            if Path(default_input).exists():
                input_file = default_input
                break
        if input_file is None:
            cli_instance.show_error_message(
                "入力ファイルが指定されていません",
                "YAMLファイルを --input オプションで指定してください",
            )
            return
    run_docs(input_file, output_dir, format_type)


@analyze.command("infer-deps")
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--visualize", "-v", is_flag=True, help="Graphvizで依存関係を視覚化")
@click.pass_context
def analyze_infer_deps(ctx: click.Context, input_file: str, visualize: bool) -> None:
    """型推論と依存関係抽出を実行"""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=cli_instance.console,
        ) as progress:
            task = progress.add_task("🔍 型推論と依存関係抽出中...", total=None)

            # 型推論と依存関係抽出を実行
            graph = extract_dependencies_from_file(Path(input_file))

            progress.update(task, description="📊 結果を表示中...")

            # 推論された型の情報を表示
            if graph.nodes:
                table = Table(title="🔍 推論された型情報", show_header=True)
                table.add_column("モジュール", style="cyan", width=30)
                table.add_column("型", style="white")

                for node in graph.nodes:
                    if node.attributes and "inferred_type" in node.attributes:
                        table.add_row(node.name, str(node.attributes["inferred_type"]))
                cli_instance.console.print(table)

            cli_instance.console.print("\n[bold green]✅ 依存関係抽出完了[/bold green]")
            cli_instance.console.print(f"ノード数: {len(graph.nodes)}")
            cli_instance.console.print(f"エッジ数: {len(graph.edges)}")
            if graph.metadata and "cycles" in graph.metadata:
                cycles_value = graph.metadata["cycles"]
                if cycles_value and isinstance(cycles_value, list):
                    cli_instance.console.print(f"循環数: {len(cycles_value)}")

            # 視覚化オプション
            if visualize:
                progress.update(task, description="🎨 視覚化中...")
                from ..core.analyzer.graph_processor import GraphProcessor

                output_image = f"{input_file}.deps.png"
                processor = GraphProcessor()
                processor.visualize_graph(graph, output_image)
                cli_instance.console.print(
                    f"📊 依存関係グラフを {output_image} に保存しました"
                )

        # 結果を表示
        cli_instance.show_success_message(
            "型推論と依存関係抽出が完了しました",
            {
                "入力": input_file,
                "ノード数": str(len(graph.nodes)),
                "エッジ数": str(len(graph.edges)),
                "視覚化": "実行" if visualize else "スキップ",
            },
        )

    except Exception as e:
        cli_instance.show_error_message("型推論と依存関係抽出に失敗しました", str(e))


if __name__ == "__main__":
    cli()
