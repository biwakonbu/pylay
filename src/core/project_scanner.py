"""
プロジェクトスキャナーモジュール

指定されたディレクトリを走査し、Pythonファイルをフィルタリングして
解析対象のファイル一覧を返します。
"""

import fnmatch
from pathlib import Path
from collections.abc import Generator
from typing import Any

from .schemas.pylay_config import PylayConfig


class ProjectScanner:
    """
    プロジェクト内のPythonファイルを走査するクラス
    """

    def __init__(self, config: PylayConfig):
        """
        初期化

        Args:
            config: pylay設定オブジェクト
        """
        self.config = config
        self.project_root = Path.cwd()

    def scan_project(self) -> Generator[Path, None, None]:
        """
        プロジェクトを走査し、解析対象のPythonファイルを返します。

        Yields:
            解析対象のPythonファイルパス
        """
        absolute_paths = self.config.get_absolute_paths(self.project_root)

        for target_dir in absolute_paths["target_dirs"]:
            yield from self._scan_directory(target_dir, current_depth=0)

    def _scan_directory(
        self, directory: Path, current_depth: int = 0
    ) -> Generator[Path, None, None]:
        """
        ディレクトリを再帰的に走査します。

        Args:
            directory: 走査対象ディレクトリ
            current_depth: 現在の深度

        Yields:
            解析対象のPythonファイルパス
        """
        if current_depth >= self.config.max_depth:
            return

        try:
            for item in directory.iterdir():
                # 除外パターンチェック
                if self._is_excluded(item):
                    continue

                if item.is_file() and item.suffix == ".py":
                    # Pythonファイルの場合
                    yield item
                elif item.is_dir():
                    # ディレクトリの場合は再帰的に走査
                    yield from self._scan_directory(item, current_depth + 1)

        except (OSError, PermissionError) as e:
            # アクセスできないディレクトリはスキップ
            print(f"警告: {directory} の走査をスキップします: {e}")
            return

    def _is_excluded(self, path: Path) -> bool:
        """
        パスが除外パターンにマッチするかをチェックします。

        Args:
            path: チェック対象のパス

        Returns:
            除外対象の場合はTrue
        """
        # パスが相対パスの場合は絶対パスに変換
        if not path.is_absolute():
            path = self.project_root / path

        try:
            relative_path = path.relative_to(self.project_root)
        except ValueError:
            # パスがプロジェクトルートのサブパスではない場合は除外
            return True

        # パス自体が除外パターンにマッチするかをチェック
        for pattern in self.config.exclude_patterns:
            if fnmatch.fnmatch(str(relative_path), pattern):
                return True

        return False

    def get_python_files(self) -> list[Path]:
        """
        走査結果をリストとして取得します。

        Returns:
            解析対象のPythonファイルパスのリスト
        """
        return list(self.scan_project())

    def validate_paths(self) -> dict[str, Any]:
        """
        設定されたパスの有効性を検証します。

        Returns:
            検証結果の辞書
        """
        absolute_paths = self.config.get_absolute_paths(self.project_root)
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "stats": {
                "target_dirs_count": len(absolute_paths["target_dirs"]),
                "output_dir": str(absolute_paths["output_dir"]),
            },
        }

        # 対象ディレクトリの検証
        for target_dir in absolute_paths["target_dirs"]:
            if not target_dir.exists():
                validation_result["errors"].append(
                    f"対象ディレクトリが存在しません: {target_dir}"
                )
                validation_result["valid"] = False
            elif not target_dir.is_dir():
                validation_result["errors"].append(
                    f"対象パスがディレクトリではありません: {target_dir}"
                )
                validation_result["valid"] = False

        # 出力ディレクトリの検証
        output_dir = absolute_paths["output_dir"]
        if not output_dir.exists():
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                validation_result["warnings"].append(
                    f"出力ディレクトリを作成しました: {output_dir}"
                )
            except OSError as e:
                validation_result["errors"].append(
                    f"出力ディレクトリを作成できません: {output_dir} - {e}"
                )
                validation_result["valid"] = False
        elif not output_dir.is_dir():
            validation_result["errors"].append(
                f"出力パスがディレクトリではありません: {output_dir}"
            )
            validation_result["valid"] = False

        return validation_result
