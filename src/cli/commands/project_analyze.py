"""
プロジェクト解析コマンド

pyproject.tomlの設定に基づいて、ディレクトリ全体のPythonファイルを
解析し、型情報、依存関係、ドキュメントを生成します。
"""

import asyncio
from pathlib import Path
from typing import Any

import click
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
from rich.tree import Tree

from ...core.analyzer.type_inferrer import TypeInferenceAnalyzer
from ...core.converters.extract_deps import extract_dependencies_from_file
from ...core.converters.type_to_yaml import extract_types_from_module
from ...core.converters.yaml_to_type import yaml_to_spec
from ...core.doc_generators.yaml_doc_generator import YamlDocGenerator
from ...core.output_manager import OutputPathManager
from ...core.project_scanner import ProjectScanner
from ...core.schemas.pylay_config import PylayConfig

console = Console()


@click.command("project-analyze")
@click.option(
    "--config-path",
    type=click.Path(exists=True),
    help="pyproject.tomlのパス（デフォルト: 自動検出）",
)
@click.option(
    "--dry-run", is_flag=True, help="実際の処理を行わず、解析対象ファイルのみ表示"
)
@click.option("--verbose", "-v", is_flag=True, help="詳細なログを出力")
@click.option("--clean", is_flag=True, help="出力ディレクトリを削除してから再生成")
def project_analyze(
    config_path: str | None, dry_run: bool, verbose: bool, clean: bool
) -> None:
    """
    プロジェクト全体を解析し、型情報、依存関係、ドキュメントを生成します。

    pyproject.tomlの[tool.pylay]セクションの設定に基づいて、
    指定されたディレクトリのPythonファイルを解析し、

    - 型情報のYAMLエクスポート
    - 依存関係の抽出とグラフ化
    - Markdownドキュメントの生成

    を一括実行します。
    """
    try:
        # 設定の読み込み
        if config_path:
            project_root = Path(config_path).parent
            config = PylayConfig.from_pyproject_toml(project_root)
        else:
            config = PylayConfig.from_pyproject_toml()
            project_root = Path.cwd()

        # OutputPathManager を初期化（統一パス管理）
        output_manager = OutputPathManager(config, project_root)

        if verbose:
            console.print("[bold blue]設定読み込み完了:[/bold blue]")
            console.print(f"  対象ディレクトリ: {config.target_dirs}")
            console.print(f"  出力ディレクトリ: {config.output_dir}")
            console.print(f"  Markdown生成: {config.generate_markdown}")
            console.print(f"  依存関係抽出: {config.extract_deps}")
            console.print(f"  クリーンアップ: {config.clean_output_dir}")
            structure = output_manager.get_output_structure()
            console.print(f"  YAML出力: {structure['yaml']}")
            console.print(f"  Markdown出力: {structure['markdown']}")
            console.print(f"  グラフ出力: {structure['graph']}")
            console.print()

        # cleanフラグの決定
        # （コマンドラインオプションが優先、未指定の場合は設定値を使用）
        effective_clean = clean or config.clean_output_dir

        # dry-runの場合は実際の処理をスキップ
        if dry_run:
            # プロジェクトスキャナーを作成
            scanner = ProjectScanner(config)

            # パスの検証
            validation = scanner.validate_paths()
            if not validation["valid"]:
                error_panel = Panel(
                    "\n".join([f"• {error}" for error in validation["errors"]]),
                    title="[bold red]❌ 設定エラー[/bold red]",
                    border_style="red",
                )
                console.print(error_panel)
                return

            # 解析対象ファイルの取得
            python_files = scanner.get_python_files()

            console.print(
                f"[bold blue]解析対象ファイル ({len(python_files)}個):[/bold blue]"
            )
            for file_path in python_files:
                console.print(f"  {file_path}")
            return

        # cleanオプションが指定された場合、出力ディレクトリを削除
        # （OutputPathManager 使用）
        if effective_clean:
            if verbose:
                if clean:
                    console.print(
                        "[yellow]🗑️  --clean オプションにより"
                        "出力ディレクトリ（docs/pylay-types/全体）を削除します"
                        "[/yellow]"
                    )
                else:
                    console.print(
                        "[yellow]🗑️  設定により"
                        "出力ディレクトリ（docs/pylay-types/全体）を削除します"
                        "[/yellow]"
                    )
            output_dir = output_manager.get_output_structure()["yaml"]
            if output_dir.exists():
                import shutil

                shutil.rmtree(output_dir)
                console.print(
                    f"[yellow]🗑️  出力ディレクトリを削除しました: {output_dir}"
                    "（src/, documents/ 等含む）[/yellow]"
                )
            else:
                console.print(
                    f"[yellow]ℹ️  出力ディレクトリが存在しないため"
                    f"削除をスキップ: {output_dir}[/yellow]"
                )

        # プロジェクトスキャナーを作成
        scanner = ProjectScanner(config)

        # パスの検証
        validation = scanner.validate_paths()
        if not validation["valid"]:
            error_panel = Panel(
                "\n".join([f"• {error}" for error in validation["errors"]]),
                title="[bold red]❌ 設定エラー[/bold red]",
                border_style="red",
            )
            console.print(error_panel)
            return

        if validation["warnings"]:
            warning_panel = Panel(
                "\n".join([f"• {warning}" for warning in validation["warnings"]]),
                title="[bold yellow]⚠️  警告[/bold yellow]",
                border_style="yellow",
            )
            console.print(warning_panel)

        # 解析対象ファイルの取得
        python_files = scanner.get_python_files()

        if not python_files:
            console.print(
                "[bold yellow]⚠️  解析対象のPythonファイルが"
                "見つかりませんでした[/bold yellow]"
            )
            return

        if dry_run:
            console.print(
                f"[bold blue]解析対象ファイル ({len(python_files)}個):[/bold blue]"
            )
            for file_path in python_files:
                console.print(f"  {file_path}")
            return

        # 開始メッセージをPanelで表示
        start_panel = Panel(
            f"[bold cyan]解析対象:[/bold cyan] {len(python_files)} 個のPythonファイル\n"
            f"[bold cyan]出力先:[/bold cyan] {config.output_dir}",
            title="[bold green]🚀 プロジェクト解析開始[/bold green]",
            border_style="green",
        )
        console.print(start_panel)

        # 解析の実行
        results = asyncio.run(
            _analyze_project_async(config, python_files, verbose, output_manager)
        )

        # 結果の出力
        _output_results(config, results, verbose, output_manager)

    except FileNotFoundError as e:
        error_panel = Panel(
            str(e),
            title="[bold red]❌ 設定ファイルエラー[/bold red]",
            border_style="red",
        )
        console.print(error_panel)
    except ValueError as e:
        error_panel = Panel(
            str(e),
            title="[bold red]❌ 設定読み込みエラー[/bold red]",
            border_style="red",
        )
        console.print(error_panel)
    except Exception as e:
        error_content = str(e)
        if verbose:
            import traceback

            error_content += f"\n\n[dim]{traceback.format_exc()}[/dim]"
        error_panel = Panel(
            error_content,
            title="[bold red]❌ 予期しないエラー[/bold red]",
            border_style="red",
        )
        console.print(error_panel)


async def _analyze_project_async(
    config: PylayConfig,
    python_files: list[Path],
    verbose: bool,
    output_manager: OutputPathManager,
) -> dict[str, Any]:
    """
    プロジェクトの非同期解析を実行します。

    Args:
        config: pylay設定
        python_files: 解析対象ファイル一覧
        verbose: 詳細出力フラグ

    Returns:
        解析結果の辞書
    """
    results = {
        "files_processed": 0,
        "types_extracted": 0,
        "dependencies_found": 0,
        "docs_generated": 0,
        "errors": [],
        "file_results": {},
    }

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("プロジェクト解析中...", total=len(python_files))

        for file_path in python_files:
            try:
                file_result = await _analyze_file_async(
                    config, file_path, verbose, output_manager
                )
                results["file_results"][str(file_path)] = file_result
                results["files_processed"] += 1

                if file_result.get("types_extracted"):
                    results["types_extracted"] += 1
                if file_result.get("dependencies_found"):
                    results["dependencies_found"] += 1
                if file_result.get("docs_generated"):
                    results["docs_generated"] += 1

            except Exception as e:
                error_msg = f"{file_path}: {e}"
                results["errors"].append(error_msg)
                if verbose:
                    console.print(f"[red]エラー: {error_msg}[/red]")

            progress.advance(task)

    return results


async def _analyze_file_async(
    config: PylayConfig,
    file_path: Path,
    verbose: bool,
    output_manager: OutputPathManager,
) -> dict[str, Any]:
    """
    単一ファイルの非同期解析を実行します。

    Args:
        config: pylay設定
        file_path: 解析対象ファイル
        verbose: 詳細出力フラグ

    Returns:
        ファイル解析結果
    """
    result = {
        "types_extracted": False,
        "dependencies_found": False,
        "docs_generated": False,
        "outputs": {},
    }

    # 型情報の抽出
    try:
        types_yaml = extract_types_from_module(file_path)
        if types_yaml is not None:  # Noneの場合（型定義なし）をスキップ
            result["types_extracted"] = True

            # YAMLファイルに出力（OutputPathManager 使用）
            yaml_file = output_manager.get_yaml_path(file_path)
            with open(yaml_file, "w", encoding="utf-8") as f:
                f.write(types_yaml)

            result["outputs"]["yaml"] = str(yaml_file)

            if verbose:
                console.print(f"  ✓ 型情報抽出完了: {yaml_file}")

            # Markdownドキュメント生成（OutputPathManager 使用）
            if config.generate_markdown:
                try:
                    spec = yaml_to_spec(types_yaml)

                    # TypeRoot の場合、最初の型を使用
                    from src.core.schemas.yaml_spec import TypeRoot

                    if spec is not None and isinstance(spec, TypeRoot) and spec.types:
                        spec = next(iter(spec.types.values()))

                    md_file = output_manager.get_markdown_path(source_file=file_path)

                    generator = YamlDocGenerator()
                    generator.generate(md_file, spec=spec)

                    result["docs_generated"] = True
                    result["outputs"]["markdown"] = str(md_file)

                    if verbose:
                        console.print(f"  ✓ Markdownドキュメント生成完了: {md_file}")
                except Exception as e:
                    if verbose:
                        console.print(f"  ✗ Markdown生成エラー ({file_path}): {e}")
        else:
            if verbose:
                console.print(f"  ℹ️  型定義なしのためスキップ: {file_path}")

    except Exception as e:
        if verbose:
            console.print(f"  ✗ 型情報抽出エラー ({file_path}): {e}")

    # 依存関係の抽出
    if config.extract_deps:
        try:
            dep_graph = extract_dependencies_from_file(file_path)
            nodes_list = list(dep_graph.nodes)
            if nodes_list:
                result["dependencies_found"] = True

                if verbose:
                    console.print(f"  ✓ 依存関係抽出完了: {len(nodes_list)} ノード")

        except Exception as e:
            if verbose:
                console.print(f"  ✗ 依存関係抽出エラー ({file_path}): {e}")

    # 型推論の実行
    if config.infer_level != "none":
        try:
            analyzer = TypeInferenceAnalyzer(config)
            inferred_types = analyzer.infer_types_from_file(str(file_path))
            if inferred_types:
                if verbose:
                    console.print(f"  ✓ 型推論完了: {len(inferred_types)} 項目")

        except Exception as e:
            if verbose:
                console.print(f"  ✗ 型推論エラー ({file_path}): {e}")

    return result


def _output_results(
    config: PylayConfig,
    results: dict[str, Any],
    verbose: bool,
    output_manager: OutputPathManager,
) -> None:
    """
    解析結果を出力します。

    Args:
        config: pylay設定
        results: 解析結果
        verbose: 詳細出力フラグ
        output_manager: OutputPathManager インスタンス
    """
    structure = output_manager.get_output_structure()

    console.print()

    # 結果サマリーをTableで表示
    summary_table = Table(
        title="解析結果サマリー", show_header=True, border_style="green", width=80
    )
    summary_table.add_column("項目", style="cyan", no_wrap=True, width=40)
    summary_table.add_column("件数", justify="right", style="green", width=20)

    summary_table.add_row("処理ファイル数", str(results["files_processed"]))
    summary_table.add_row("型情報抽出", f"{results['types_extracted']} ファイル")
    summary_table.add_row("依存関係発見", f"{results['dependencies_found']} ファイル")
    summary_table.add_row("ドキュメント生成", f"{results['docs_generated']} ファイル")

    console.print(summary_table)
    console.print()

    # 出力先情報をPanelで表示
    output_panel = Panel(
        f"[bold cyan]YAML出力:[/bold cyan] {structure['yaml']}\n"
        f"[bold cyan]Markdown出力:[/bold cyan] {structure['markdown']}",
        title="[bold blue]📁 出力ディレクトリ[/bold blue]",
        border_style="blue",
    )
    console.print(output_panel)

    # エラー情報
    if results["errors"]:
        console.print()
        error_count = len(results["errors"])
        error_panel = Panel(
            "\n".join([f"• {error}" for error in results["errors"]]),
            title=f"[bold yellow]⚠️  エラー発生: {error_count} 件[/bold yellow]",
            border_style="yellow",
        )
        console.print(error_panel)

    # 詳細ファイルリスト（verbose時）
    if verbose and results["file_results"]:
        console.print()
        file_tree = Tree("[bold blue]📄 生成ファイル詳細[/bold blue]")
        for file_path, file_result in results["file_results"].items():
            outputs = file_result.get("outputs", {})
            if outputs:
                file_node = file_tree.add(f"[cyan]{Path(file_path).name}[/cyan]")
                for output_type, output_path in outputs.items():
                    file_node.add(f"[dim]{output_type}:[/dim] {output_path}")
        console.print(file_tree)

    console.print()
    console.print("[bold green]✅ プロジェクト解析が完了しました。[/bold green]")
