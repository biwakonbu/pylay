"""
IOヘルパーユーティリティ

一時ファイル作成やコード処理の共通機能を管理します。
"""

import tempfile
import os
from pathlib import Path

from src.core.schemas.analyzer_types import TempFileConfig


def create_temp_file(config: TempFileConfig) -> Path:
    """
    一時ファイルを作成します。

    Args:
        config: 一時ファイルの設定（コード、suffix、mode）

    Returns:
        作成された一時ファイルのパス

    Raises:
        OSError: ファイル作成に失敗した場合
    """
    try:
        with tempfile.NamedTemporaryFile(
            mode=config["mode"], suffix=config["suffix"], delete=False
        ) as f:
            f.write(config["code"])
            temp_path = Path(f.name)
        return temp_path
    except OSError as e:
        raise OSError(f"一時ファイル作成エラー: {e}")


def cleanup_temp_file(file_path: Path) -> None:
    """
    一時ファイルを削除します。

    Args:
        file_path: 削除するファイルのパス
    """
    try:
        if file_path.exists():
            os.unlink(file_path)
    except OSError:
        # 削除失敗は無視（一時ファイルなので）
        pass


def read_file_content(file_path: Path) -> str:
    """
    ファイルの内容を読み込みます。

    Args:
        file_path: 読み込むファイルのパス

    Returns:
        ファイルの内容

    Raises:
        FileNotFoundError: ファイルが存在しない場合
        UnicodeDecodeError: エンコーディングエラー
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")
    except UnicodeDecodeError as e:
        raise UnicodeDecodeError(
            e.encoding, e.object, e.start, e.end, f"エンコーディングエラー: {file_path}"
        )
