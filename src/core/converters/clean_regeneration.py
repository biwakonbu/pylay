"""クリーン再生成機能

古い .lay.* ファイルを削除してから新しいファイルを生成する機能を提供します。
"""

from pathlib import Path


def is_lay_generated_file(file_path: Path) -> bool:
    """ファイルがpylayによって生成されたものかどうかを判定

    警告ヘッダーの有無で判定します。

    Args:
        file_path: 判定対象のファイルパス

    Returns:
        pylayが生成したファイルの場合True、手動実装ファイルの場合False
    """
    if not file_path.exists():
        return False

    try:
        content = file_path.read_text(encoding="utf-8")

        # 警告ヘッダーのキーワードで判定
        return (
            "pylay自動生成ファイル" in content
            and "このファイルを直接編集しないでください" in content
        )

    except (OSError, UnicodeDecodeError):
        # ファイル読み込みに失敗した場合は手動ファイルとして扱う（安全策）
        return False


def clean_lay_files(target_dir: Path, lay_suffix: str = ".lay.py") -> list[Path]:
    """指定ディレクトリ内の古い .lay.* ファイルを削除

    Args:
        target_dir: 対象ディレクトリ
        lay_suffix: 削除対象の拡張子（.lay.py または .lay.yaml）

    Returns:
        削除されたファイルのリスト
    """
    if not target_dir.exists() or not target_dir.is_dir():
        return []

    deleted_files: list[Path] = []

    # 対象ディレクトリ内の .lay.* ファイルを検索
    for file_path in target_dir.glob(f"*{lay_suffix}"):
        if is_lay_generated_file(file_path):
            try:
                file_path.unlink()
                deleted_files.append(file_path)
            except OSError:
                # 削除に失敗した場合はスキップ
                pass

    return deleted_files


def clean_lay_files_recursive(
    target_dir: Path, lay_suffix: str = ".lay.py"
) -> list[Path]:
    """指定ディレクトリ配下の古い .lay.* ファイルを再帰的に削除

    Args:
        target_dir: 対象ディレクトリ
        lay_suffix: 削除対象の拡張子（.lay.py または .lay.yaml）

    Returns:
        削除されたファイルのリスト
    """
    if not target_dir.exists() or not target_dir.is_dir():
        return []

    deleted_files: list[Path] = []

    # 再帰的に .lay.* ファイルを検索
    for file_path in target_dir.rglob(f"*{lay_suffix}"):
        if is_lay_generated_file(file_path):
            try:
                file_path.unlink()
                deleted_files.append(file_path)
            except OSError:
                # 削除に失敗した場合はスキップ
                pass

    return deleted_files
