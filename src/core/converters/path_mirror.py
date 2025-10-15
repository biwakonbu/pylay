"""パッケージ構造ミラーリング機能

入力ファイルのプロジェクト内での相対位置を保持したまま、
docs/pylay/ 配下に出力パスを生成する機能を提供します。
"""

from pathlib import Path
from typing import Annotated

from pydantic import Field, TypeAdapter

# ドメイン型定義
FileSuffix = Annotated[str, Field(pattern=r"^\..+")]


# 型アダプター（再利用可能）
_suffix_adapter = TypeAdapter(FileSuffix)


def mirror_package_path(
    input_path: Path, project_root: Path, output_base: Path, suffix: FileSuffix = ".lay.yaml"
) -> Path:
    """入力パスを docs/pylay/ 配下にミラーリングした出力パスを生成

    Args:
        input_path: 入力ファイルのパス
        project_root: プロジェクトルートディレクトリ
        output_base: 出力ベースディレクトリ（通常は docs/pylay）
        suffix: 出力ファイルの拡張子（.lay.yaml または .lay.py）

    Returns:
        ミラーリングされた出力パス

    Example:
        >>> input_path = Path("src/core/schemas/types.py")
        >>> project_root = Path(".")
        >>> output_base = Path("docs/pylay")
        >>> mirror_package_path(input_path, project_root, output_base, ".lay.yaml")
        PosixPath('docs/pylay/src/core/schemas/types.lay.yaml')
    """
    # suffixのバリデーション
    validated_suffix = _suffix_adapter.validate_python(suffix)

    # 絶対パスに変換
    input_abs = input_path.resolve()
    project_abs = project_root.resolve()

    # プロジェクトルートからの相対パスを取得
    try:
        rel_path = input_abs.relative_to(project_abs)
    except ValueError:
        # プロジェクト外のファイルの場合は入力ファイル名のみ使用
        rel_path = Path(input_path.name)

    # 拡張子を suffix に置き換え
    output_rel_path = rel_path.with_suffix(validated_suffix)

    # output_base 配下にミラーリング
    return output_base / output_rel_path


def ensure_output_directory(output_path: Path) -> None:
    """出力ファイルの親ディレクトリを確実に作成

    Args:
        output_path: 出力ファイルのパス
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)


def find_project_root(start_path: Path) -> Path | None:
    """pyproject.toml を検索してプロジェクトルートを特定

    Args:
        start_path: 検索開始パス（通常はカレントディレクトリ）

    Returns:
        プロジェクトルートのパス、見つからない場合は None
    """
    current = start_path.resolve()

    # 最大10階層まで遡る
    for _ in range(10):
        if (current / "pyproject.toml").exists():
            return current

        parent = current.parent
        if parent == current:  # ルートディレクトリに到達
            break
        current = parent

    return None
