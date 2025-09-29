"""pylay のコマンドラインインターフェース"""

import click
from pathlib import Path
from typing import Optional

from ..core.converters.type_to_yaml import extract_types_from_module
from ..core.converters.yaml_to_type import yaml_to_spec
from ..core.doc_generators.type_doc_generator import LayerDocGenerator
from ..core.doc_generators.yaml_doc_generator import YamlDocGenerator
from ..core.doc_generators.test_catalog_generator import CatalogGenerator
from ..core.converters.extract_deps import extract_dependencies_from_file
from ..core.schemas.pylay_config import PylayConfig
from ..core.output_manager import OutputPathManager
import mypy.api
from .commands.project_analyze import project_analyze


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version="0.1.0")
@click.option("--verbose", is_flag=True, help="詳細ログを出力")
@click.option(
    "--config", type=click.Path(exists=True), help="設定ファイルのパス (YAML)"
)
def cli(verbose: bool, config: Optional[str]) -> None:
    """pylay: 型解析、自動型生成、ドキュメント生成ツール

    使用例:
        pylay generate type-docs --input module.py --output docs.md
        pylay analyze types --input module.py
    """
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
    """Python 型から Markdown ドキュメントを生成"""
    click.echo(f"型ドキュメント生成: {input} -> {output}")
    generator = LayerDocGenerator()
    docs = generator.generate(Path(input))
    if output == "docs/type_docs.md":
        # デフォルト出力先の場合はディレクトリを作成
        Path(output).parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        f.write(docs)
    click.echo(f"生成完了: {output}")


@generate.command("yaml-docs")
@click.argument("input", type=click.Path(exists=True))
@click.option(
    "--output",
    type=click.Path(),
    help="出力 Markdown ファイル（デフォルト: 設定ファイルに基づく）",
)
def generate_yaml_docs(input: str, output: Optional[str]) -> None:
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

    click.echo(f"YAML ドキュメント生成: {input} -> {output}")
    with open(input, "r", encoding="utf-8") as f:
        yaml_str = f.read()

    spec = yaml_to_spec(yaml_str)
    generator = YamlDocGenerator()
    generator.generate(output, spec=spec)
    click.echo(f"生成完了: {output}")


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
        f.write(catalog)
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
        graph = extract_dependencies_from_file(str(Path(input_dir)))
        # matplotlibでグラフを生成
        import matplotlib.pyplot as plt
        import networkx as nx

        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(graph)
        nx.draw(
            graph,
            pos,
            with_labels=True,
            node_color="lightblue",
            node_size=2000,
            font_size=10,
            font_weight="bold",
            arrows=True,
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
def analyze() -> None:
    """静的解析コマンド (mypy + AST 型推論/依存抽出)"""


@analyze.command("types")
@click.argument("input", type=click.Path(exists=True))
@click.option("--output-yaml", type=click.Path(), help="型を YAML にエクスポート")
@click.option("--infer", is_flag=True, help="mypy で型推論を実行")
def analyze_types(input: str, output_yaml: Optional[str], infer: bool) -> None:
    """モジュールから型を解析/推論し、YAML 出力可能"""
    click.echo(f"型解析: {input}")
    if infer:
        result = mypy.api.run([str(input), "--infer", "--check"])
        click.echo(f"mypy 出力: {result}")
        if "error" in result.lower():
            raise click.Abort("mypy エラー: 型推論失敗")

    types_yaml = extract_types_from_module(Path(input))
    if output_yaml:
        with open(output_yaml, "w") as f:
            f.write(types_yaml)
        click.echo(f"YAML 出力: {output_yaml}")
    else:
        click.echo(types_yaml)


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
    """Python 型を YAML に変換"""
    click.echo(f"型 -> YAML 変換: {input_module}")
    yaml_str = extract_types_from_module(Path(input_module))
    if output == "-":
        click.echo(yaml_str)
    else:
        with open(output, "w") as f:
            f.write(yaml_str)
        click.echo(f"出力: {output}")


@convert.command("to-type")
@click.argument("input_yaml", type=click.Path(exists=True))
@click.option("--output-py", type=click.Path(), help="出力 Python コード (BaseModel)")
def convert_to_type(input_yaml: str, output_py: Optional[str]) -> None:
    """YAML を Pydantic BaseModel に変換"""
    click.echo(f"YAML -> 型変換: {input_yaml}")
    with open(input_yaml, "r", encoding="utf-8") as f:
        yaml_str = f.read()

    spec = yaml_to_spec(yaml_str)
    model_code = f"""from pydantic import BaseModel
from typing import {", ".join([t.__name__ if hasattr(t, "__name__") else str(t) for t in spec.__class__.__mro__ if t != object])}

# 生成されたPydanticモデル
class GeneratedModel(BaseModel):
    pass
"""
    if output_py:
        with open(output_py, "w") as f:
            f.write(model_code)
        click.echo(f"出力: {output_py}")
    else:
        click.echo(model_code)


# project-analyze コマンドを追加
cli.add_command(project_analyze)


if __name__ == "__main__":
    cli()
