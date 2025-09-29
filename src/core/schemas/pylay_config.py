"""
pylay設定管理モジュール

pyproject.toml の [tool.pylay] セクションから設定を読み込み、
バリデーションを行うPydanticモデルを提供します。
"""

import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class PylayConfig(BaseModel):
    """
    pylayの設定を管理するPydanticモデル

    pyproject.tomlの[tool.pylay]セクションに対応します。
    """

    # 解析対象ディレクトリ
    target_dirs: list[str] = Field(
        default=["src/"], description="解析対象のディレクトリパス（相対パス）"
    )

    # 出力ディレクトリ
    output_dir: str = Field(
        default="docs/", description="出力ファイルの保存先ディレクトリ"
    )

    # ドキュメント生成フラグ
    generate_markdown: bool = Field(
        default=True, description="Markdownドキュメントを生成するかどうか"
    )

    # 依存関係抽出フラグ
    extract_deps: bool = Field(default=True, description="依存関係を抽出するかどうか")

    # 型推論レベル
    infer_level: str = Field(
        default="strict", description="型推論の厳密さ（strict, normal, loose）"
    )

    # 出力ディレクトリクリーンアップフラグ
    clean_output_dir: bool = Field(
        default=True, description="実行時に出力ディレクトリをクリーンアップするかどうか"
    )

    # 除外パターン
    exclude_patterns: list[str] = Field(
        default=[
            "**/tests/**",
            "**/*_test.py",
            "**/__pycache__/**",
        ],
        description="解析から除外するファイルパターン",
    )

    # 最大解析深度
    max_depth: int = Field(default=10, description="再帰解析の最大深度")

    @classmethod
    def from_pyproject_toml(cls, project_root: Path | None = None) -> "PylayConfig":
        """
        pyproject.tomlから設定を読み込みます。

        Args:
            project_root: プロジェクトルートディレクトリ（Noneの場合はカレントディレクトリ）

        Returns:
            設定オブジェクト

        Raises:
            FileNotFoundError: pyproject.tomlが見つからない場合
            ValueError: TOMLパースエラーの場合
        """
        if project_root is None:
            project_root = Path.cwd()

        pyproject_path = project_root / "pyproject.toml"

        if not pyproject_path.exists():
            raise FileNotFoundError(f"pyproject.toml not found at {pyproject_path}")

        try:
            with open(pyproject_path, "rb") as f:
                toml_data = tomllib.load(f)
        except Exception as e:
            raise ValueError(f"Failed to parse pyproject.toml: {e}")

        # [tool.pylay] セクションを取得
        pylay_section = toml_data.get("tool", {}).get("pylay", {})

        return cls(**pylay_section)

    def to_pyproject_section(self) -> dict[str, Any]:
        """
        設定をpyproject.tomlの[tool.pylay]セクション形式で返します。

        Returns:
            TOMLセクション形式の辞書
        """
        return self.model_dump()

    def get_absolute_paths(self, project_root: Path) -> dict[str, list[Path]]:
        """
        相対パスを絶対パスに変換します。

        Args:
            project_root: プロジェクトルートディレクトリ

        Returns:
            絶対パスの辞書
        """
        absolute_target_dirs = [
            (project_root / target_dir).resolve() for target_dir in self.target_dirs
        ]

        absolute_output_dir = (project_root / self.output_dir).resolve()

        return {
            "target_dirs": absolute_target_dirs,
            "output_dir": absolute_output_dir,
        }

    def get_output_subdirs(self, project_root: Path) -> dict[str, Path]:
        """
        出力ディレクトリのサブディレクトリ（types/, documents/ など）の絶対パスを取得します。

        Args:
            project_root: プロジェクトルートディレクトリ

        Returns:
            サブディレクトリの絶対パスの辞書
        """
        base_output_dir = (project_root / self.output_dir).resolve()

        return {
            "base": base_output_dir,
            "types": base_output_dir / "types",
            "documents": base_output_dir / "documents",
        }

    def get_types_output_dir(self, project_root: Path) -> Path:
        """
        型データ出力ディレクトリの絶対パスを取得します。

        Args:
            project_root: プロジェクトルートディレクトリ

        Returns:
            型データ出力ディレクトリの絶対パス
        """
        return self.get_output_subdirs(project_root)["types"]

    def get_documents_output_dir(self, project_root: Path) -> Path:
        """
        ドキュメント出力ディレクトリの絶対パスを取得します。

        Args:
            project_root: プロジェクトルートディレクトリ

        Returns:
            ドキュメント出力ディレクトリの絶対パス
        """
        return self.get_output_subdirs(project_root)["documents"]

    def ensure_output_structure(self, project_root: Path) -> None:
        """
        出力ディレクトリの構造（types/, documents/ など）を作成します。

        Args:
            project_root: プロジェクトルートディレクトリ
        """
        subdirs = self.get_output_subdirs(project_root)

        for dir_path in subdirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
