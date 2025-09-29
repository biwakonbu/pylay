"""
出力ファイル管理モジュール

PylayConfig を基に統一的な出力パスを生成します。
すべての出力ファイル（YAML, Markdown, グラフ）のパス管理を一元化。
"""

from pathlib import Path
from typing import Optional

from .schemas.pylay_config import PylayConfig


class OutputPathManager:
    """
    出力ファイルのパスを統一的に管理するマネージャー

    PylayConfig を基に、YAML型情報、Markdownドキュメント、
    依存関係グラフなどの出力パスを生成します。
    """

    def __init__(self, config: PylayConfig, project_root: Optional[Path] = None):
        """
        初期化

        Args:
            config: pylay設定
            project_root: プロジェクトルートディレクトリ（デフォルト: カレントディレクトリ）
        """
        self.config = config
        self.project_root = project_root or Path.cwd()
        self.config.ensure_output_structure(self.project_root)

    def get_yaml_path(self, source_file: Path) -> Path:
        """
        YAML型情報ファイルのパスを生成

        Args:
            source_file: ソースPythonファイルのパス

        Returns:
            YAML出力パス（例: docs/pylay-types/src/cli/main.types.yaml）
        """
        base_output_dir = self.config.get_absolute_paths(self.project_root)[
            "output_dir"
        ]
        relative_path = source_file.relative_to(self.project_root)

        # ソースファイルの場所に基づいて出力ディレクトリを決定
        # target_dirs に含まれるディレクトリの場合は、その構造を模倣
        # target_dirs の値からスラッシュを除去して比較
        normalized_target_dirs = [d.rstrip("/") for d in self.config.target_dirs]
        if relative_path.parts[0] in normalized_target_dirs:
            output_dir = (
                base_output_dir
                / relative_path.parts[0]
                / Path(*relative_path.parts[1:-1])
            )
        else:
            output_dir = base_output_dir

        yaml_file = (
            output_dir / f"{source_file.stem}.types.yaml"
        )  # _types を削除し、.types.yaml に変更
        yaml_file.parent.mkdir(parents=True, exist_ok=True)
        return yaml_file

    def get_markdown_path(
        self, source_file: Optional[Path] = None, filename: Optional[str] = None
    ) -> Path:
        """
        Markdownドキュメントファイルのパスを生成

        Args:
            source_file: ソースPythonファイルのパス（ファイル別生成時）
            filename: 固定ファイル名（例: "yaml_docs.md"）

        Returns:
            Markdown出力パス（例: docs/pylay-types/documents/main_docs.md）
        """
        documents_dir = self.config.get_documents_output_dir(self.project_root)

        if source_file:
            # ファイル別生成（project_analyze 用）
            # ソースファイルの場所に基づいて出力ディレクトリを決定
            # target_dirs に含まれるディレクトリの場合は、その構造を模倣
            # target_dirs の値からスラッシュを除去して比較
            relative_path = source_file.relative_to(self.project_root)
            normalized_target_dirs = [d.rstrip("/") for d in self.config.target_dirs]
            if relative_path.parts[0] in normalized_target_dirs:
                output_dir = (
                    documents_dir
                    / relative_path.parts[0]
                    / Path(*relative_path.parts[1:-1])
                )
            else:
                output_dir = documents_dir

            md_file = output_dir / f"{source_file.stem}_docs.md"
        elif filename:
            # 固定ファイル名（CLI generate 用）
            md_file = documents_dir / filename
        else:
            raise ValueError("source_file または filename のいずれかを指定してください")

        md_file.parent.mkdir(parents=True, exist_ok=True)
        return md_file

    def get_dependency_graph_path(self, filename: str = "dependency_graph.png") -> Path:
        """
        依存関係グラフファイルのパスを生成

        Args:
            filename: グラフファイル名（デフォルト: "dependency_graph.png"）

        Returns:
            グラフ出力パス（例: docs/pylay-types/dependency_graph.png）
        """
        output_dir = self.config.get_absolute_paths(self.project_root)["output_dir"]
        graph_file = output_dir / filename
        graph_file.parent.mkdir(parents=True, exist_ok=True)
        return graph_file

    def get_output_structure(self) -> dict[str, Path]:
        """
        出力構造の概要を返す

        Returns:
            出力ディレクトリの辞書（"yaml", "markdown", "graph"）
        """
        base_dir = self.config.get_absolute_paths(self.project_root)["output_dir"]
        return {
            "yaml": base_dir,
            "markdown": self.config.get_documents_output_dir(self.project_root),
            "graph": base_dir,
        }
