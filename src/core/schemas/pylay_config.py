"""
pylay設定管理モジュール

pyproject.toml の [tool.pylay] セクションから設定を読み込み、
バリデーションを行うPydanticモデルを提供します。
"""

import tomllib
from pathlib import Path
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field, field_validator

from src.core.schemas.types import (
    CleanOutputDirFlag,
    DirectoryPath,
    ExtractDepsFlag,
    GenerateMarkdownFlag,
    GlobPattern,
    InferLevel,
    MaxDepth,
)


class AbsolutePathsDict(TypedDict):
    """get_absolute_pathsの戻り値型定義"""

    target_dirs: list[Path]
    output_dir: Path


# 品質チェック関連のクラス定義(先に定義が必要)
class LevelThresholds(BaseModel):
    """型レベル閾値設定"""

    level1_max: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Level 1型エイリアスの最大比率(これを超えると警告)",
    )
    level2_min: float = Field(
        default=0.40,
        ge=0.0,
        le=1.0,
        description="Level 2制約付き型の最小比率(これを下回ると警告)",
    )
    level3_min: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Level 3 BaseModelの最小比率(これを下回ると警告)",
    )


class ErrorCondition(BaseModel):
    """エラー条件設定"""

    condition: str = Field(description="エラー判定のための条件式(例: 'level1_ratio > 0.20')")
    message: str = Field(description="エラー発生時のメッセージ")


class SeverityLevel(BaseModel):
    """深刻度レベル設定"""

    name: str = Field(description="深刻度レベルの名前(アドバイス、警告、エラー)")
    color: Literal["blue", "yellow", "red"] = Field(description="表示色(blue=アドバイス、yellow=警告、red=エラー)")
    threshold: float = Field(ge=0.0, le=1.0, description="このレベルに分類される閾値スコア")


class ImprovementGuidance(BaseModel):
    """改善プランのガイダンス設定"""

    level: str = Field(description="対象の改善レベル")
    suggestion: str = Field(description="改善のための具体的な提案")


class GenerationConfig(BaseModel):
    """ファイル生成設定"""

    lay_suffix: str = Field(
        default=".lay.py",
        description="pylayが生成するPythonファイルの拡張子",
    )
    lay_yaml_suffix: str = Field(
        default=".lay.yaml",
        description="pylayが生成するYAMLファイルの拡張子",
    )
    add_generation_header: bool = Field(
        default=True,
        description="生成ファイルの先頭に警告ヘッダーを追加するか",
    )
    include_source_path: bool = Field(
        default=True,
        description="生成ファイルに元のソースファイルパスを記録するか",
    )


class OutputConfig(BaseModel):
    """出力設定"""

    yaml_output_dir: str | None = Field(
        default=None,
        description="YAML出力先ディレクトリ(Noneの場合はPythonソースと同じディレクトリ)",
    )
    markdown_output_dir: str | None = Field(
        default=None,
        description="Markdown出力先ディレクトリ(Noneの場合はPythonソースと同じディレクトリ)",
    )
    mirror_package_structure: bool = Field(
        default=True,
        description="パッケージ構造をミラーリングするか",
    )
    include_metadata: bool = Field(
        default=True,
        description="YAMLに_metadataセクションを含めるか",
    )
    preserve_docstrings: bool = Field(
        default=True,
        description="Python→YAML変換時にdocstringを保持するか",
    )


class ImportsConfig(BaseModel):
    """import設定"""

    use_relative_imports: bool = Field(
        default=True,
        description="YAML→Python変換時に相対importを使用するか",
    )


class QualityCheckConfig(BaseModel):
    """品質チェック設定"""

    # 型レベル閾値設定(厳格モード)
    level_thresholds: LevelThresholds = Field(default_factory=LevelThresholds, description="型レベルの閾値設定")

    # エラーレベル判定基準
    error_conditions: list[ErrorCondition] = Field(default_factory=list, description="エラー判定のための条件リスト")

    # アドバイス・警告・エラーレベル設定
    severity_levels: list[SeverityLevel] = Field(
        default_factory=lambda: [
            SeverityLevel(name="error", color="red", threshold=0.0),
            SeverityLevel(name="warning", color="yellow", threshold=0.6),
            SeverityLevel(name="advice", color="blue", threshold=0.8),
        ],
        description="深刻度レベルの定義",
    )

    # 改善プランの詳細度設定
    improvement_guidance: list[ImprovementGuidance] = Field(
        default_factory=lambda: [
            ImprovementGuidance(
                level="level1_to_level2",
                suggestion="Annotated型で制約を追加してください",
            ),
            ImprovementGuidance(
                level="level2_to_level3",
                suggestion="BaseModelでビジネスロジックを追加してください",
            ),
            ImprovementGuidance(
                level="add_validation",
                suggestion="バリデーション関数を実装してください",
            ),
            ImprovementGuidance(
                level="add_documentation",
                suggestion="詳細なdocstringを追加してください",
            ),
            ImprovementGuidance(
                level="primitive_replacement",
                suggestion="ドメイン型に置き換えてください",
            ),
        ],
        description="改善プランのガイダンス設定",
    )


class PylayConfig(BaseModel):
    """
    pylayの設定を管理するPydanticモデル

    pyproject.tomlの[tool.pylay]セクションに対応します。
    """

    # 解析対象ディレクトリ
    target_dirs: list[str] = Field(
        default_factory=lambda: ["src"],
        description="解析対象のディレクトリパス(相対パス、末尾スラッシュは自動削除)",
    )

    # 出力ディレクトリ
    output_dir: DirectoryPath = Field(
        default_factory=lambda: DirectoryPath("docs"),
        description="出力ファイルの保存先ディレクトリ(末尾スラッシュは自動削除)",
    )

    # ドキュメント生成フラグ
    generate_markdown: GenerateMarkdownFlag = Field(default=True, description="Markdownドキュメントを生成するかどうか")

    # 依存関係抽出フラグ
    extract_deps: ExtractDepsFlag = Field(default=True, description="依存関係を抽出するかどうか")

    # 型推論レベル
    infer_level: InferLevel = Field(
        default="normal",
        description=("型推論の厳密さ(strict, normal, loose, none) - デフォルトは'normal'でバランス型"),
    )

    # 出力ディレクトリクリーンアップフラグ
    clean_output_dir: CleanOutputDirFlag = Field(
        default=True, description="実行時に出力ディレクトリをクリーンアップするかどうか"
    )

    # 除外パターン
    exclude_patterns: list[GlobPattern] = Field(
        default=[
            "**/tests/**",
            "**/*_test.py",
            "**/__pycache__/**",
        ],
        description="解析から除外するファイルパターン",
    )

    # 最大解析深度
    max_depth: MaxDepth = Field(default=MaxDepth(10), description="再帰解析の最大深度")

    # 新機能: 品質チェック設定(オプション)
    quality_check: QualityCheckConfig | None = Field(default=None, description="型品質チェックの設定(オプション)")

    # Issue #51: .lay.py / .lay.yaml 方式の設定
    generation: GenerationConfig = Field(
        default_factory=GenerationConfig,
        description="ファイル生成設定(.lay.py / .lay.yaml)",
    )
    output: OutputConfig = Field(
        default_factory=OutputConfig,
        description="出力設定(YAML出力先、ミラーリング等)",
    )
    imports: ImportsConfig = Field(
        default_factory=ImportsConfig,
        description="import設定(相対import等)",
    )

    @field_validator("target_dirs", mode="before")
    @classmethod
    def normalize_target_dirs(cls, v: Any) -> list[str]:
        """target_dirsの末尾スラッシュを削除"""
        if isinstance(v, list):
            return [s.rstrip("/") if isinstance(s, str) else s for s in v]
        return v

    @field_validator("output_dir", mode="before")
    @classmethod
    def normalize_output_dir(cls, v: Any) -> str:
        """output_dirの末尾スラッシュを削除"""
        if isinstance(v, str):
            return v.rstrip("/")
        return v

    @classmethod
    def from_pyproject_toml(cls, project_root: Path | None = None) -> "PylayConfig":
        """
        pyproject.tomlから設定を読み込みます。

        Args:
            project_root: プロジェクトルートディレクトリ
                （Noneの場合はカレントディレクトリから親を遡って探索）

        Returns:
            設定オブジェクト

        Raises:
            FileNotFoundError: pyproject.tomlが見つからない場合
            ValueError: TOMLパースエラーの場合
        """
        if project_root is None:
            # カレントディレクトリから親ディレクトリを遡ってpyproject.tomlを探索
            current = Path.cwd()
            pyproject_path = None

            # ルートディレクトリまで遡る
            for parent in [current, *current.parents]:
                candidate = parent / "pyproject.toml"
                if candidate.exists():
                    pyproject_path = candidate
                    break

            if pyproject_path is None:
                raise FileNotFoundError("pyproject.toml not found in current or parent directories")
        else:
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

        # ネストされた設定を抽出して処理
        pylay_section = pylay_section.copy()

        # quality_check設定の処理
        quality_check_data = pylay_section.get("quality_check")
        if quality_check_data and isinstance(quality_check_data, dict):
            del pylay_section["quality_check"]
            try:
                quality_check_config = QualityCheckConfig(**quality_check_data)
                pylay_section["quality_check"] = quality_check_config
            except Exception as e:
                raise ValueError(f"Failed to parse quality_check config: {e}")

        # generation設定の処理
        generation_data = pylay_section.get("generation")
        if generation_data and isinstance(generation_data, dict):
            del pylay_section["generation"]
            try:
                generation_config = GenerationConfig(**generation_data)
                pylay_section["generation"] = generation_config
            except Exception as e:
                raise ValueError(f"Failed to parse generation config: {e}")

        # output設定の処理
        output_data = pylay_section.get("output")
        if output_data and isinstance(output_data, dict):
            del pylay_section["output"]
            try:
                output_config = OutputConfig(**output_data)
                pylay_section["output"] = output_config
            except Exception as e:
                raise ValueError(f"Failed to parse output config: {e}")

        # imports設定の処理
        imports_data = pylay_section.get("imports")
        if imports_data and isinstance(imports_data, dict):
            del pylay_section["imports"]
            try:
                imports_config = ImportsConfig(**imports_data)
                pylay_section["imports"] = imports_config
            except Exception as e:
                raise ValueError(f"Failed to parse imports config: {e}")

        return cls(**pylay_section)

    def to_pyproject_section(self) -> dict[str, Any]:
        """
        設定をpyproject.tomlの[tool.pylay]セクション形式で返します。

        Returns:
            TOMLセクション形式の辞書
        """
        return self.model_dump()

    def get_absolute_paths(self, project_root: Path) -> AbsolutePathsDict:
        """
        相対パスを絶対パスに変換します。

        Args:
            project_root: プロジェクトルートディレクトリ

        Returns:
            絶対パスの辞書（target_dirs: list[Path], output_dir: Path）
        """
        absolute_target_dirs = [(project_root / target_dir).resolve() for target_dir in self.target_dirs]

        absolute_output_dir = (project_root / self.output_dir).resolve()

        return {
            "target_dirs": absolute_target_dirs,
            "output_dir": absolute_output_dir,
        }

    def get_output_subdirs(self, project_root: Path) -> dict[str, Path]:
        """
        出力ディレクトリのサブディレクトリ（types/, documents/ など）の
        絶対パスを取得します。

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

    def is_quality_check_enabled(self) -> bool:
        """
        品質チェック機能が有効かどうかを確認します。

        Returns:
            品質チェックが有効な場合はTrue、無効な場合はFalse
        """
        return self.quality_check is not None

    def get_quality_thresholds(self) -> LevelThresholds | None:
        """
        品質チェックの閾値設定を取得します。

        Returns:
            閾値設定（品質チェックが無効の場合はNone）
        """
        return self.quality_check.level_thresholds if self.quality_check else None

    def get_error_conditions(self) -> list[ErrorCondition]:
        """
        エラー判定条件を取得します。

        Returns:
            エラー判定条件のリスト
        """
        return self.quality_check.error_conditions if self.quality_check else []

    def get_severity_levels(self) -> list[SeverityLevel]:
        """
        深刻度レベル設定を取得します。

        Returns:
            深刻度レベル設定のリスト
        """
        if self.quality_check and self.quality_check.severity_levels:
            return self.quality_check.severity_levels

        # デフォルト値(error:0.0, warning:0.6, advice:0.8)
        return [
            SeverityLevel(name="error", color="red", threshold=0.0),
            SeverityLevel(name="warning", color="yellow", threshold=0.6),
            SeverityLevel(name="advice", color="blue", threshold=0.8),
        ]

    def get_improvement_guidance(self) -> list[ImprovementGuidance]:
        """
        改善プランのガイダンス設定を取得します。

        Returns:
            改善プランのガイダンス設定のリスト
        """
        return self.quality_check.improvement_guidance if self.quality_check else []
