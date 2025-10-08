"""
プロジェクト解析コマンド

pyproject.tomlの設定に基づいて、ディレクトリ全体のPythonファイルを
解析し、型情報、依存関係、ドキュメントを生成します。
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click
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
from rich.tree import Tree

from src.cli.utils import load_config

if TYPE_CHECKING:
    from src.core.schemas.pylay_config import PylayConfig

from ...core.analyzer.type_inferrer import TypeInferenceAnalyzer
from ...core.converters.extract_deps import extract_dependencies_from_file
from ...core.converters.type_to_yaml import extract_types_from_module
from ...core.converters.yaml_to_type import yaml_to_spec
from ...core.output_manager import OutputPathManager
from ...core.project_scanner import ProjectScanner

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
@click.option(
    "--clean", is_flag=True, help="（非推奨）このオプションは効果がありません"
)
def project_analyze(
    config_path: str | None, dry_run: bool, verbose: bool, clean: bool
) -> None:
    """
    プロジェクト全体を解析し、統計情報と品質指標を表示します。

    pyproject.tomlの[tool.pylay]セクションの設定に基づいて、
    指定されたディレクトリのPythonファイルを解析し、以下の統計情報を収集します:

    - 型定義の数（ファイル別、合計）
    - 依存関係の数（ファイル別、合計）
    - 型推論結果の数（オプション）

    注意:
        YAML生成とドキュメント生成は `pylay yaml` コマンドで実行してください。
        このコマンドは統計情報の収集と表示のみを行います。

    使用例:
        # プロジェクト全体の統計を表示
        uv run pylay project-analyze

        # 詳細情報を表示
        uv run pylay project-analyze -v

        # 対象ファイルのみ表示（実行なし）
        uv run pylay project-analyze --dry-run
    """
    try:
        # 設定の読み込み（共通ユーティリティを使用）
        config = load_config(config_path)
        # プロジェクトルートを取得（config読み込み後に決定）
        project_root = Path.cwd()

        # OutputPathManager を初期化（統一パス管理）
        output_manager = OutputPathManager(config, project_root)

        if verbose:
            console.print("[bold blue]Configuration loaded:[/bold blue]")
            console.print(f"  Target directories: {config.target_dirs}")
            console.print(f"  Output directory: {config.output_dir}")
            console.print(f"  Markdown generation: {config.generate_markdown}")
            console.print(f"  Dependency extraction: {config.extract_deps}")
            console.print(f"  Auto cleanup: {config.clean_output_dir}")
            structure = output_manager.get_output_structure()
            console.print(f"  YAML output: {structure['yaml']}")
            console.print(f"  Markdown output: {structure['markdown']}")
            console.print(f"  Graph output: {structure['graph']}")
            console.print()

        # dry-runの場合は実際の処理をスキップ
        if dry_run:
            # プロジェクトスキャナーを作成
            scanner = ProjectScanner(config)

            # パスの検証
            validation = scanner.validate_paths()
            if not validation["valid"]:
                error_panel = Panel(
                    "\n".join([f"• {error}" for error in validation["errors"]]),
                    title="[bold red]❌ Configuration Error[/bold red]",
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
                title="[bold yellow]⚠️  Warning[/bold yellow]",
                border_style="yellow",
            )
            console.print(warning_panel)

        # 解析対象ファイルの取得
        python_files = scanner.get_python_files()

        if not python_files:
            console.print(
                "[bold yellow]⚠️  No Python files found to analyze[/bold yellow]"
            )
            return

        if dry_run:
            console.print(
                f"[bold blue]Target files ({len(python_files)} files):[/bold blue]"
            )
            for file_path in python_files:
                console.print(f"  {file_path}")
            return

        # 開始メッセージをPanelで表示
        start_panel = Panel(
            f"[bold cyan]Target:[/bold cyan] {len(python_files)} Python files\n"
            f"[bold cyan]Output:[/bold cyan] {config.output_dir}",
            title="[bold green]🚀 Project Analysis[/bold green]",
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
            title="[bold red]❌ Configuration File Error[/bold red]",
            border_style="red",
        )
        console.print(error_panel)
    except ValueError as e:
        error_panel = Panel(
            str(e),
            title="[bold red]❌ Configuration Loading Error[/bold red]",
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
            title="[bold red]❌ Unexpected Error[/bold red]",
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
    プロジェクトの非同期解析を実行します（統計・品質分析のみ）。

    Args:
        config: pylay設定
        python_files: 解析対象ファイル一覧
        verbose: 詳細出力フラグ
        output_manager: 出力パス管理（未使用だが互換性のため保持）

    Returns:
        解析結果の辞書（統計情報）

    Note:
        YAML生成とドキュメント生成は `pylay yaml` コマンドで実行してください。
        このコマンドは統計情報の収集と品質分析のみを行います。
    """
    results = {
        "files_processed": 0,
        "total_types": 0,
        "total_dependencies": 0,
        "total_inferred_types": 0,
        "files_with_types": 0,
        "files_with_deps": 0,
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
        task = progress.add_task("Analyzing project...", total=len(python_files))

        for file_path in python_files:
            try:
                file_result = await _analyze_file_async(
                    config, file_path, verbose, output_manager
                )
                results["file_results"][str(file_path)] = file_result
                results["files_processed"] += 1

                # 統計情報の集計
                if file_result.get("types_count", 0) > 0:
                    results["files_with_types"] += 1
                    results["total_types"] += file_result["types_count"]

                if file_result.get("dependencies_count", 0) > 0:
                    results["files_with_deps"] += 1
                    results["total_dependencies"] += file_result["dependencies_count"]

                if file_result.get("inferred_types_count", 0) > 0:
                    results["total_inferred_types"] += file_result[
                        "inferred_types_count"
                    ]

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
    単一ファイルの非同期解析を実行します（統計・品質分析のみ）。

    Args:
        config: pylay設定
        file_path: 解析対象ファイル
        verbose: 詳細出力フラグ
        output_manager: 出力パス管理（未使用だが互換性のため保持）

    Returns:
        ファイル解析結果（統計情報）

    Note:
        YAML生成とドキュメント生成は `pylay yaml` コマンドで実行してください。
        このコマンドは統計情報の収集と品質分析のみを行います。
    """
    result = {
        "types_count": 0,
        "dependencies_count": 0,
        "inferred_types_count": 0,
        "stats": {},
    }

    # 型情報の統計収集（YAML生成なし）
    try:
        types_yaml = extract_types_from_module(file_path)
        if types_yaml is not None:
            # YAMLをパースして型の数をカウント
            from src.core.schemas.yaml_spec import TypeRoot

            spec = yaml_to_spec(types_yaml)
            if spec is not None and isinstance(spec, TypeRoot) and spec.types:
                result["types_count"] = len(spec.types)

            if verbose:
                console.print(f"  ✓ 型情報抽出完了: {result['types_count']} 個の型定義")
        else:
            if verbose:
                console.print(f"  ℹ️  型定義なし: {file_path}")

    except Exception as e:
        if verbose:
            console.print(f"  ✗ 型情報抽出エラー ({file_path}): {e}")

    # 依存関係の抽出（統計のみ）
    if config.extract_deps:
        try:
            dep_graph = extract_dependencies_from_file(file_path)
            nodes_list = list(dep_graph.nodes)
            result["dependencies_count"] = len(nodes_list)

            if verbose and nodes_list:
                console.print(
                    f"  ✓ 依存関係抽出完了: {result['dependencies_count']} ノード"
                )

        except Exception as e:
            if verbose:
                console.print(f"  ✗ 依存関係抽出エラー ({file_path}): {e}")

    # 型推論の実行（統計のみ）
    if config.infer_level != "none":
        try:
            analyzer = TypeInferenceAnalyzer(config)
            inferred_types = analyzer.infer_types_from_file(str(file_path))
            result["inferred_types_count"] = (
                len(inferred_types) if inferred_types else 0
            )

            if verbose and inferred_types:
                console.print(f"  ✓ 型推論完了: {result['inferred_types_count']} 項目")

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
    解析結果を出力します（統計情報のみ）。

    Args:
        config: pylay設定
        results: 解析結果（統計情報）
        verbose: 詳細出力フラグ
        output_manager: OutputPathManager インスタンス（未使用）

    Note:
        YAML生成とドキュメント生成は `pylay yaml` コマンドで実行してください。
        このコマンドは統計情報の表示のみを行います。
    """
    console.print()

    # 結果サマリーをTableで表示（統計情報のみ）
    summary_table = Table(
        title="Project Statistics",
        show_header=True,
        border_style="green",
        header_style="",
        box=SIMPLE,
    )
    summary_table.add_column("Item", style="cyan", no_wrap=True)
    summary_table.add_column("Count", justify="right", style="green")

    summary_table.add_row("Files Processed", str(results["files_processed"]))
    summary_table.add_row(
        "Files with Type Definitions", str(results["files_with_types"])
    )
    summary_table.add_row("Total Type Definitions", str(results["total_types"]))
    summary_table.add_row("Files with Dependencies", str(results["files_with_deps"]))
    summary_table.add_row("Total Dependencies", str(results["total_dependencies"]))

    if config.infer_level != "none":
        summary_table.add_row(
            "Total Inferred Types", str(results["total_inferred_types"])
        )

    console.print(summary_table)
    console.print()

    # 使用方法のヒント
    hint_panel = Panel(
        "[bold cyan]YAML生成:[/bold cyan] uv run pylay yaml\n"
        "[bold cyan]ドキュメント生成:[/bold cyan] uv run pylay docs -i <yaml_file>",
        title="[bold blue]💡 Next Steps[/bold blue]",
        border_style="blue",
    )
    console.print(hint_panel)

    # エラー情報
    if results["errors"]:
        console.print()
        error_count = len(results["errors"])
        error_panel = Panel(
            "\n".join([f"• {error}" for error in results["errors"]]),
            title=f"[bold yellow]⚠️  Errors: {error_count}[/bold yellow]",
            border_style="yellow",
        )
        console.print(error_panel)

    # 詳細ファイルリスト（verbose時）
    if verbose and results["file_results"]:
        console.print()
        file_tree = Tree("[bold blue]📊 Analysis Details[/bold blue]")
        for file_path, file_result in results["file_results"].items():
            file_name = Path(file_path).name
            types_count = file_result.get("types_count", 0)
            deps_count = file_result.get("dependencies_count", 0)
            inferred_count = file_result.get("inferred_types_count", 0)

            if types_count > 0 or deps_count > 0 or inferred_count > 0:
                file_node = file_tree.add(f"[cyan]{file_name}[/cyan]")
                if types_count > 0:
                    file_node.add(f"[green]Types:[/green] {types_count}")
                if deps_count > 0:
                    file_node.add(f"[yellow]Dependencies:[/yellow] {deps_count}")
                if inferred_count > 0:
                    file_node.add(f"[blue]Inferred:[/blue] {inferred_count}")
        console.print(file_tree)

    console.print()
    console.print("[bold green]✅ Project analysis completed.[/bold green]")
