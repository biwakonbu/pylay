"""pylay init コマンド

プロジェクトに pylay の設定を追加するコマンドです。
"""

from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from src.core.schemas.pylay_config import PylayConfig


def run_init(force: bool = False) -> None:
    """pylay の設定を pyproject.toml に追加

    Args:
        force: 既存の設定を上書きするかどうか
    """
    console = Console()

    try:
        # カレントディレクトリで pyproject.toml を検索
        pyproject_path = Path.cwd() / "pyproject.toml"

        if not pyproject_path.exists():
            console.print(
                Panel(
                    "[red]pyproject.toml が見つかりませんでした[/red]\n\n"
                    "[dim]このコマンドはプロジェクトのルートディレクトリで実行してください[/dim]",
                    title="[bold red]❌ エラー[/bold red]",
                    border_style="red",
                )
            )
            return

        # 既存の pyproject.toml を読み込み
        content = pyproject_path.read_text(encoding="utf-8")

        # 既に [tool.pylay] セクションが存在するかチェック
        if "[tool.pylay]" in content and not force:
            console.print(
                Panel(
                    (
                        "[yellow]pyproject.toml に既に [tool.pylay] "
                        "セクションが存在します[/yellow]\n\n"
                        "[dim]上書きする場合は --force "
                        "オプションを使用してください[/dim]"
                    ),
                    title="[bold yellow]⚠️  警告[/bold yellow]",
                    border_style="yellow",
                )
            )
            return

        # デフォルト設定を生成
        default_config = PylayConfig()

        # pyproject.toml に追加する設定テキストを生成
        config_text = _generate_config_text(default_config)

        # [tool.pylay] セクションが既に存在する場合は置き換え
        if "[tool.pylay]" in content:
            # 既存のセクションを削除
            import re

            # [tool.pylay] から次のセクション（または EOF）までを削除
            pattern = r"\[tool\.pylay\].*?(?=\n\[|\Z)"
            content = re.sub(pattern, "", content, flags=re.DOTALL)

        # ファイル末尾に追加
        if not content.endswith("\n"):
            content += "\n"

        content += "\n" + config_text

        # ファイルに書き込み
        pyproject_path.write_text(content, encoding="utf-8")

        # 成功メッセージ
        console.print(
            Panel(
                (
                    "[bold green]✅ pylay の設定を pyproject.toml "
                    "に追加しました[/bold green]\n\n"
                    f"[bold cyan]設定ファイル:[/bold cyan] {pyproject_path}\n\n"
                    "[dim]設定は [tool.pylay] "
                    "セクションで確認・編集できます[/dim]"
                ),
                title="[bold green]🎉 初期化完了[/bold green]",
                border_style="green",
            )
        )

    except Exception as e:
        console.print(
            Panel(
                f"[red]エラー: {e}[/red]",
                title="[bold red]❌ 処理エラー[/bold red]",
                border_style="red",
            )
        )


def _generate_config_text(config: PylayConfig) -> str:
    """PylayConfig から pyproject.toml の設定テキストを生成

    Args:
        config: PylayConfig インスタンス

    Returns:
        pyproject.toml に追加する設定テキスト
    """
    lines = [
        "[tool.pylay]",
        "# pylay の設定",
        "",
        "# スキャン対象ディレクトリ",
        f"target_dirs = {config.target_dirs}",
        "",
        "# 除外パターン",
        f"exclude_patterns = {config.exclude_patterns}",
        "",
        "# ファイル生成設定",
        "[tool.pylay.generation]",
        f'lay_suffix = "{config.generation.lay_suffix}"',
        f'lay_yaml_suffix = "{config.generation.lay_yaml_suffix}"',
        (
            f"add_generation_header = "
            f"{str(config.generation.add_generation_header).lower()}"
        ),
        (f"include_source_path = {str(config.generation.include_source_path).lower()}"),
        "",
        "# 出力設定",
        "[tool.pylay.output]",
        f'yaml_output_dir = "{config.output.yaml_output_dir}"',
        (
            f"mirror_package_structure = "
            f"{str(config.output.mirror_package_structure).lower()}"
        ),
        f"include_metadata = {str(config.output.include_metadata).lower()}",
        (f"preserve_docstrings = {str(config.output.preserve_docstrings).lower()}"),
        "",
        "# import設定",
        "[tool.pylay.imports]",
        f"use_relative_imports = {str(config.imports.use_relative_imports).lower()}",
    ]

    return "\n".join(lines)
