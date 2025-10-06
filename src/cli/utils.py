"""
CLIコマンド共通ユーティリティ

全コマンドで共通の設定ファイル読み込みとターゲットディレクトリ解決のロジックを提供します。
"""

from pathlib import Path

from src.core.schemas.pylay_config import PylayConfig


def load_config(config_path: str | None = None) -> PylayConfig:
    """
    設定ファイルを読み込みます。

    Args:
        config_path: 設定ファイルまたはディレクトリのパス
            - None: カレントディレクトリから親を遡ってpyproject.tomlを探索
            - ファイルパス: そのファイルを直接読み込み
            - ディレクトリパス: そのディレクトリ内のpyproject.tomlを読み込み

    Returns:
        設定オブジェクト

    Raises:
        FileNotFoundError: 設定ファイルが見つからない場合
        ValueError: 設定ファイルのパースに失敗した場合
    """
    if config_path is None:
        # configが指定されていない場合、親ディレクトリを遡って探索
        return PylayConfig.from_pyproject_toml(None)

    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Config path not found: {config_path}")

    if path.is_file():
        # ファイルが直接指定された場合、その親ディレクトリを使用
        project_root = path.parent
    elif path.is_dir():
        # ディレクトリが指定された場合、そのディレクトリを使用
        project_root = path
    else:
        raise ValueError(f"Invalid config path: {config_path}")

    return PylayConfig.from_pyproject_toml(project_root)


def resolve_target_path(target: str | None, config: PylayConfig) -> Path:
    """
    解析対象のパスを解決します。

    Args:
        target: コマンドラインで指定されたターゲットパス（Noneの場合は設定から取得）
        config: 設定オブジェクト

    Returns:
        解析対象のパス

    Note:
        優先順位:
        1. コマンドライン引数で指定されたtarget
        2. pyproject.tomlのtarget_dirs[0]
        3. カレントディレクトリ
    """
    if target is not None:
        return Path(target)

    # TARGET未指定の場合、pyproject.tomlのtarget_dirsを使用
    if config.target_dirs:
        # target_dirsの最初のディレクトリを使用
        return Path(config.target_dirs[0])

    # target_dirsも未設定の場合はカレントディレクトリ
    return Path.cwd()
