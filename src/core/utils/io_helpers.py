"""
IOヘルパーユーティリティ

一時ファイル作成やコード処理の共通機能を管理します。
"""

import fnmatch
import os
import tempfile
from pathlib import Path

from src.core.analyzer.models import TempFileConfig


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
        with tempfile.NamedTemporaryFile(mode=config.mode, suffix=config.suffix, delete=False) as f:
            f.write(config.code)
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
        with open(file_path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")
    except UnicodeDecodeError as e:
        raise UnicodeDecodeError(
            e.encoding,
            e.object,
            e.start,
            e.end,
            f"エンコーディングエラー: {file_path} - {e.reason}",
        ) from e


def collect_python_files(directory: Path, exclude_patterns: list[str] | None = None) -> list[Path]:
    """
    指定されたディレクトリからPythonファイルを収集します。

    Args:
        directory: 検索対象のディレクトリ
        exclude_patterns: 除外するパターン(glob形式)

    Returns:
        収集されたPythonファイルのパスリスト
    """
    # すべての.pyファイルを収集
    all_py_files = list(directory.rglob("*.py"))

    # 除外パターンを適用
    py_files = []
    for py_file in all_py_files:
        # ファイルパスをPOSIX形式に変換(Windows環境対応)
        try:
            relative_path = py_file.relative_to(directory).as_posix()
        except ValueError:
            # directoryの外のファイルの場合は絶対パスを使用
            relative_path = py_file.as_posix()

        # 両方の形式でチェック(絶対パスと相対パスの両方を考慮)
        absolute_path = py_file.as_posix()

        # 除外パターンにマッチするかチェック(相対パスと絶対パスの両方)
        should_exclude = False
        if exclude_patterns:
            for pattern in exclude_patterns:
                if fnmatch.fnmatch(relative_path, pattern) or fnmatch.fnmatch(absolute_path, pattern):
                    should_exclude = True
                    break

        if not should_exclude:
            py_files.append(py_file)

    return py_files
