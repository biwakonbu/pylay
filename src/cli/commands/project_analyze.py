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
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn

from ...core.project_scanner import ProjectScanner
from ...core.schemas.pylay_config import PylayConfig
from ...core.converters.type_to_yaml import extract_types_from_module
from ...core.converters.infer_types import infer_types_from_file
from ...core.converters.extract_deps import extract_dependencies_from_file
from ...core.doc_generators.type_doc_generator import LayerDocGenerator
from ...core.doc_generators.yaml_doc_generator import YamlDocGenerator


console = Console()


@click.command("project-analyze")
@click.option(
    "--config-path",
    type=click.Path(exists=True),
    help="pyproject.tomlのパス（デフォルト: 自動検出）"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="実際の処理を行わず、解析対象ファイルのみ表示"
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="詳細なログを出力"
)
@click.option(
    "--clean",
    is_flag=True,
    help="出力ディレクトリを削除してから再生成"
)
def project_analyze(config_path: str | None, dry_run: bool, verbose: bool, clean: bool) -> None:
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

        if verbose:
            console.print(f"[bold blue]設定読み込み完了:[/bold blue]")
            console.print(f"  対象ディレクトリ: {config.target_dirs}")
            console.print(f"  出力ディレクトリ: {config.output_dir}")
            console.print(f"  Markdown生成: {config.generate_markdown}")
            console.print(f"  依存関係抽出: {config.extract_deps}")
            console.print()

        # cleanオプションが指定された場合、出力ディレクトリを削除
        if clean:
            output_dir = config.get_absolute_paths(Path.cwd())["output_dir"]
            if output_dir.exists():
                import shutil
                shutil.rmtree(output_dir)
                console.print(f"[yellow]🗑️  出力ディレクトリを削除しました: {output_dir}[/yellow]")
            else:
                console.print(f"[yellow]ℹ️  出力ディレクトリが存在しないため削除をスキップ: {output_dir}[/yellow]")

        # プロジェクトスキャナーを作成
        scanner = ProjectScanner(config)

        # パスの検証
        validation = scanner.validate_paths()
        if not validation["valid"]:
            console.print("[bold red]❌ 設定エラー:[/bold red]")
            for error in validation["errors"]:
                console.print(f"  {error}")
            return

        if validation["warnings"]:
            console.print("[bold yellow]⚠️  警告:[/bold yellow]")
            for warning in validation["warnings"]:
                console.print(f"  {warning}")
            console.print()

        # 解析対象ファイルの取得
        python_files = scanner.get_python_files()

        if not python_files:
            console.print("[bold yellow]⚠️  解析対象のPythonファイルが見つかりませんでした[/bold yellow]")
            return

        if dry_run:
            console.print(f"[bold blue]解析対象ファイル ({len(python_files)}個):[/bold blue]")
            for file_path in python_files:
                console.print(f"  {file_path}")
            return

        console.print(f"[bold green]🚀 プロジェクト解析開始[/bold green]")
        console.print(f"解析対象: {len(python_files)} 個のPythonファイル")
        console.print()

        # 解析の実行
        results = asyncio.run(_analyze_project_async(config, python_files, verbose))

        # 結果の出力
        _output_results(config, results, verbose)

    except FileNotFoundError as e:
        console.print(f"[bold red]❌ 設定ファイルエラー:[/bold red] {e}")
    except ValueError as e:
        console.print(f"[bold red]❌ 設定読み込みエラー:[/bold red] {e}")
    except Exception as e:
        console.print(f"[bold red]❌ 予期しないエラー:[/bold red] {e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())


async def _analyze_project_async(
    config: PylayConfig,
    python_files: list[Path],
    verbose: bool
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
        "file_results": {}
    }

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=True
    ) as progress:

        task = progress.add_task(
            "プロジェクト解析中...",
            total=len(python_files)
        )

        for file_path in python_files:
            try:
                file_result = await _analyze_file_async(config, file_path, verbose)
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
    verbose: bool
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
        "outputs": {}
    }

    # 型情報の抽出
    try:
        types_yaml = extract_types_from_module(file_path)
        if types_yaml:
            result["types_extracted"] = True

            # YAMLファイルに出力
            if config.generate_markdown:
                base_output_dir = config.get_absolute_paths(Path.cwd())["output_dir"]

                # ファイルパスに基づいて適切な出力ディレクトリを決定
                try:
                    # プロジェクトルートからの相対パスを取得
                    project_root = Path.cwd()
                    relative_path = file_path.relative_to(project_root)

                    # src/ 内のファイルは src/ 配下に配置
                    if relative_path.parts[0] == "src":
                        output_dir = base_output_dir / "src" / Path(*relative_path.parts[1:-1])
                    # scripts/ 内のファイルは scripts/ 配下に配置
                    elif relative_path.parts[0] == "scripts":
                        output_dir = base_output_dir / "scripts" / Path(*relative_path.parts[1:-1])
                    else:
                        # その他のファイルはそのまま
                        output_dir = base_output_dir
                except ValueError:
                    # 相対パスが取得できない場合（ファイルがプロジェクト外の場合）
                    output_dir = base_output_dir

                yaml_file = output_dir / f"{file_path.stem}_types.yaml"
                yaml_file.parent.mkdir(parents=True, exist_ok=True)

                with open(yaml_file, "w", encoding="utf-8") as f:
                    f.write(types_yaml)

                result["outputs"]["yaml"] = str(yaml_file)

                if verbose:
                    console.print(f"  ✓ 型情報抽出完了: {yaml_file}")

    except Exception as e:
        if verbose:
            console.print(f"  ✗ 型情報抽出エラー ({file_path}): {e}")

    # 依存関係の抽出
    if config.extract_deps:
        try:
            dep_graph = extract_dependencies_from_file(str(file_path))
            if dep_graph and len(dep_graph.nodes()) > 0:
                result["dependencies_found"] = True

                if verbose:
                    console.print(f"  ✓ 依存関係抽出完了: {len(dep_graph.nodes())} ノード")

        except Exception as e:
            if verbose:
                console.print(f"  ✗ 依存関係抽出エラー ({file_path}): {e}")

    # 型推論の実行
    if config.infer_level != "none":
        try:
            # pyproject.tomlをmypy設定ファイルとして渡す
            config_file = Path.cwd() / "pyproject.toml" if (Path.cwd() / "pyproject.toml").exists() else None
            inferred_types = infer_types_from_file(str(file_path), str(config_file) if config_file else None)
            if inferred_types:
                if verbose:
                    console.print(f"  ✓ 型推論完了: {len(inferred_types)} 項目")

        except Exception as e:
            if verbose:
                console.print(f"  ✗ 型推論エラー ({file_path}): {e}")

    return result


def _output_results(config: PylayConfig, results: dict[str, Any], verbose: bool) -> None:
    """
    解析結果を出力します。

    Args:
        config: pylay設定
        results: 解析結果
        verbose: 詳細出力フラグ
    """
    output_dir = config.get_absolute_paths(Path.cwd())["output_dir"]

    console.print(f"\n[bold green]✅ 解析完了[/bold green]")
    console.print(f"処理ファイル数: {results['files_processed']}")
    console.print(f"型情報抽出: {results['types_extracted']} ファイル")
    console.print(f"依存関係発見: {results['dependencies_found']} ファイル")
    console.print(f"出力ディレクトリ: {output_dir}")

    if results["errors"]:
        console.print(f"\n[bold yellow]⚠️  エラー発生: {len(results['errors'])} 件[/bold yellow]")
        if verbose:
            for error in results["errors"]:
                console.print(f"  {error}")

    console.print(f"\n[bold blue]📁 生成ファイル[/bold blue]")
    if verbose and results["file_results"]:
        for file_path, file_result in results["file_results"].items():
            outputs = file_result.get("outputs", {})
            if outputs:
                console.print(f"  {Path(file_path).name}:")
                for output_type, output_path in outputs.items():
                    console.print(f"    {output_type}: {output_path}")

    console.print(f"\n[dim]プロジェクト解析が完了しました。[/dim]")
