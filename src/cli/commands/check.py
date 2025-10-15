"""
プロジェクト品質チェックコマンド

型定義レベル、type-ignore、品質チェックを統合した診断コマンド。
"""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from ...core.analyzer.quality_checker import QualityChecker
from ...core.analyzer.type_ignore_analyzer import TypeIgnoreAnalyzer
from ...core.analyzer.type_level_analyzer import TypeLevelAnalyzer
from ...core.schemas.pylay_config import PylayConfig

console = Console()


def _load_config() -> PylayConfig:
    """設定を読み込む

    Returns:
        PylayConfig: プロジェクト設定（pyproject.tomlが存在しない場合はデフォルト設定）

    Raises:
        なし（エラー時はデフォルト設定にフォールバック）
    """
    try:
        # from_pyproject_toml の引数は project_root であり、pyproject.toml のパスではない
        # None を渡すとカレントディレクトリから自動探索される
        return PylayConfig.from_pyproject_toml()
    except FileNotFoundError:
        return PylayConfig()
    except Exception:
        # 設定ファイルの解析に失敗した場合はデフォルト設定にフォールバック
        return PylayConfig()


@click.command("check")
@click.argument("target", type=click.Path(exists=True), required=False)
@click.option(
    "--focus",
    type=click.Choice(["types", "ignore", "quality"], case_sensitive=False),
    default=None,
    help="特定のチェックのみ実行(未指定の場合は全チェック)",
)
@click.option("-v", "--verbose", is_flag=True, help="詳細なログを出力")
def check(
    target: str | None,
    focus: str | None,
    verbose: bool,
) -> None:
    """プロジェクトの品質をチェックし、改善提案を表示します。

    型定義レベル、type-ignore診断、品質チェックを統合した診断コマンドです。

    Args:
        target: 解析対象のディレクトリまたはファイル（デフォルト: カレントディレクトリ）
        focus: 特定のチェックのみ実行（types/ignore/quality、デフォルト: None=全チェック）
        verbose: 詳細なログを出力（デフォルト: False）

    Returns:
        None

    Examples:
        # 全てのチェックを実行（デフォルト）
        uv run pylay check

        # 型定義レベル統計のみ
        uv run pylay check --focus types

        # type-ignore 診断のみ
        uv run pylay check --focus ignore

        # 品質チェックのみ
        uv run pylay check --focus quality

        # 特定のディレクトリをチェック
        uv run pylay check src/core

        # 詳細情報を表示
        uv run pylay check -v
    """
    config = _load_config()

    # 引数が指定されていない場合はconfig.target_dirsを使用
    target_paths: list[Path]
    if target:
        target_paths = [Path(target)]
    else:
        # config.target_dirsが複数ある場合は、すべてのディレクトリを処理
        target_paths = [Path(d) for d in config.target_dirs] if config.target_dirs else [Path.cwd()]

    # 除外パターンをconfigから取得（空リストの場合は None に変換）
    exclude_patterns = config.exclude_patterns or None

    # 複数のターゲットディレクトリがある場合は通知
    if len(target_paths) > 1:
        console.print(f"[cyan]INFO: {len(target_paths)}個のターゲットディレクトリを処理します[/cyan]")
        console.print()

    # 各ターゲットディレクトリに対してチェックを実行
    for idx, target_path in enumerate(target_paths, 1):
        if len(target_paths) > 1:
            console.print(f"[bold cyan]📁 ターゲット {idx}/{len(target_paths)}: {target_path}[/bold cyan]")
            console.print()

        if focus is None:
            # 全てのチェックを実行
            console.print()
            console.rule("[bold cyan]🔍 Project Quality Check[/bold cyan]")
            console.print()

            # 1. 型定義レベル統計
            console.print("[bold blue]1/3: 型定義レベル統計[/bold blue]")
            console.print()
            _run_type_analysis(target_path, verbose=verbose, exclude_patterns=exclude_patterns)

            console.print()
            console.rule()
            console.print()

            # 2. type-ignore 診断
            console.print("[bold yellow]2/3: type-ignore 診断[/bold yellow]")
            console.print()
            _run_type_ignore_analysis(target_path, verbose=verbose, exclude_patterns=exclude_patterns)

            console.print()
            console.rule()
            console.print()

            # 3. 品質チェック
            console.print("[bold green]3/3: 品質チェック[/bold green]")
            console.print()
            _run_quality_check(target_path, config, verbose=verbose, exclude_patterns=exclude_patterns)

            console.print()
            console.rule("[bold cyan]✅ Check Complete[/bold cyan]")
            console.print()

        elif focus == "types":
            _run_type_analysis(target_path, verbose=verbose, exclude_patterns=exclude_patterns)

        elif focus == "ignore":
            _run_type_ignore_analysis(target_path, verbose=verbose, exclude_patterns=exclude_patterns)

        elif focus == "quality":
            _run_quality_check(target_path, config, verbose=verbose, exclude_patterns=exclude_patterns)


def _run_type_analysis(target_path: Path, verbose: bool, exclude_patterns: list[str] | None = None) -> None:
    """型定義レベル統計を実行

    Args:
        target_path: 解析対象のパス
        verbose: 詳細情報を表示するかどうか
        exclude_patterns: 除外するパターン（glob形式）

    Returns:
        None
    """
    from ...core.analyzer.type_reporter import TypeReporter

    console.print(f"🔍 解析中: {target_path}")

    analyzer: TypeLevelAnalyzer = TypeLevelAnalyzer()

    if target_path.is_file():
        report = analyzer.analyze_file(target_path)
    else:
        report = analyzer.analyze_directory(
            target_path, include_upgrade_recommendations=verbose, exclude_patterns=exclude_patterns
        )

    # 対象ディレクトリを決定（詳細表示用）
    target_dirs: list[str]
    target_dirs = [str(target_path.parent)] if target_path.is_file() else [str(target_path)]

    reporter: TypeReporter = TypeReporter(target_dirs=target_dirs)
    reporter.generate_detailed_report(report, show_details=verbose, show_stats=True)

    # 推奨事項を条件付きで表示
    if verbose and report.upgrade_recommendations:
        console.print()
        console.print(reporter.generate_upgrade_recommendations_report(report.upgrade_recommendations))

    if verbose and report.docstring_recommendations:
        console.print()
        console.print(reporter.generate_docstring_recommendations_report(report.docstring_recommendations))


def _run_type_ignore_analysis(target_path: Path, verbose: bool, exclude_patterns: list[str] | None = None) -> None:
    """type-ignore 診断を実行

    Args:
        target_path: 解析対象のパス
        verbose: 詳細情報（解決策）を表示するかどうか
        exclude_patterns: 除外パターンのリスト（省略時はpyproject.tomlから読み込み）

    Returns:
        None
    """
    from ...core.analyzer.type_ignore_reporter import TypeIgnoreReporter

    console.print(f"🔍 解析中: {target_path}")

    analyzer: TypeIgnoreAnalyzer = TypeIgnoreAnalyzer()

    if target_path.is_file():
        issues = analyzer.analyze_file(str(target_path))
    else:
        issues = analyzer.analyze_project(target_path, exclude_patterns=exclude_patterns)

    # サマリー情報を生成
    summary = analyzer.generate_summary(issues)

    reporter: TypeIgnoreReporter = TypeIgnoreReporter()
    reporter.generate_console_report(issues, summary, show_solutions=verbose)


def _run_quality_check(
    target_path: Path, config: PylayConfig, verbose: bool, exclude_patterns: list[str] | None = None
) -> None:
    """品質チェックを実行

    Args:
        target_path: 解析対象のパス
        config: プロジェクト設定
        verbose: 詳細情報を表示するかどうか
        exclude_patterns: 除外するパターン（glob形式）

    Returns:
        None
    """
    from ...core.analyzer.code_locator import CodeLocator
    from ...core.analyzer.quality_reporter import QualityReporter

    console.print(f"🔍 解析中: {target_path}")

    # 型レベル解析を実行
    analyzer: TypeLevelAnalyzer = TypeLevelAnalyzer()

    target_dirs: list[str]
    if target_path.is_file():
        report = analyzer.analyze_file(target_path)
        target_dirs = [str(target_path.parent)]
    else:
        report = analyzer.analyze_directory(target_path, exclude_patterns=exclude_patterns)
        target_dirs = [str(target_path)]

    # 品質チェッカーを初期化
    checker: QualityChecker = QualityChecker(config)
    checker.code_locator = CodeLocator([Path(d) for d in target_dirs])

    # 品質チェックを実行
    check_result = checker.check_quality(report)

    # レポートを生成
    reporter: QualityReporter = QualityReporter(target_dirs=target_dirs)
    reporter.generate_console_report(check_result, report, show_details=verbose)
