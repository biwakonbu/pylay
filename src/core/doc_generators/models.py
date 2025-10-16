"""
ドキュメント生成モジュールのドメインモデル

このモジュールでは、ドキュメント生成機能のビジネスロジックを含むドメインモデルを定義します。
主に以下のカテゴリのモデルを定義します：

1. ドキュメント生成のビジネスモデル
2. 型検査のビジネスモデル
3. マークダウン生成のビジネスモデル
4. ファイルシステム操作のビジネスモデル
"""

import time
from pathlib import Path
from typing import Any, TypedDict

from pydantic import BaseModel, Field

from .types import (
    BatchGenerationConfig,
    BatchGenerationResult,
    DocumentConfig,
    DocumentStructure,
    FileSystemConfig,
    GenerationResult,
    MarkdownGenerationConfig,
    MarkdownSectionInfo,
    PydanticSchemaInfo,
    TemplateConfig,
    TypeInspectionConfig,
    TypeInspectionResult,
    TypeName,
    create_empty_metadata,
)

# デフォルトの出力パス(成功時と例外時で一貫して使用)
DEFAULT_OUTPUT_PATH = "./docs"


class DocumentGeneratorKwargs(TypedDict, total=False):
    """
    DocumentGeneratorService.generate_documentのキーワード引数型定義

    将来の拡張機能で具体的なパラメータが追加される際に使用されます。
    現在は空のTypedDictとして定義し、型安全性を確保します。
    """

    # 将来の拡張機能用のフィールドをここに定義


class DocumentGeneratorService(BaseModel):
    """
    ドキュメント生成のサービスクラス

    このクラスは、ドキュメント生成処理のビジネスロジックを実装します。
    """

    # DocumentGeneratorProtocolとの互換性を確保（objectを使用）
    def generate_document(self, config: DocumentConfig, **_kwargs: DocumentGeneratorKwargs) -> GenerationResult:
        """
        ドキュメントを生成します。

        Args:
            config: ドキュメント生成設定
            **_kwargs: 追加の設定パラメータ (DocumentGeneratorProtocolとの互換性のため保持)

        Returns:
            生成結果
        """
        start_time = time.time()

        try:
            # 簡易的な実装(実際はより複雑な処理が必要)
            output_path = Path(config.output_path) if config.output_path else Path(DEFAULT_OUTPUT_PATH)

            # 出力ディレクトリの作成
            output_path.mkdir(parents=True, exist_ok=True)

            # ドキュメント構造の作成(簡易版)
            structure = DocumentStructure(
                title="Generated Documentation",
                sections=[],
                metadata=create_empty_metadata(),
                generation_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            )

            # マークダウン生成 (簡易版)
            markdown_content = f"# {structure.title}\n\nGenerated at: {structure.generation_timestamp}"

            # ファイル出力(簡易版)
            output_file = output_path / "index.md"
            output_file.write_text(markdown_content, encoding=config.encoding)

            processing_time = (time.time() - start_time) * 1000

            return GenerationResult(
                success=True,
                output_path=str(output_path),
                generated_files=[str(output_file)],
                generation_time_ms=processing_time,
                files_count=1,
            )

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            return GenerationResult(
                success=False,
                output_path=(str(config.output_path) if config.output_path else DEFAULT_OUTPUT_PATH),
                generation_time_ms=processing_time,
                error_message=str(e),
                files_count=0,
            )


class TypeInspectorService(BaseModel):
    """
    型検査のサービスクラス

    このクラスは、型検査処理のビジネスロジックを実装します。
    """

    def inspect_type(self, type_cls: type[Any], config: TypeInspectionConfig | None = None) -> TypeInspectionResult:
        """
        指定された型を検査します。

        Args:
            type_cls: 検査対象の型クラス
            config: 検査設定（Noneの場合、デフォルト設定を使用）

        Returns:
            検査結果
        """
        start_time = time.time()
        config = config or TypeInspectionConfig()

        try:
            # 型名の取得
            type_name = getattr(type_cls, "__name__", str(type_cls))

            # docstringの取得
            docstring = self._get_docstring(type_cls)
            has_docstring = docstring is not None

            # コードブロックの抽出
            code_blocks = self._extract_code_blocks(docstring or "")

            # Pydanticモデルかどうかのチェック
            is_pydantic_model = self._is_pydantic_model(type_cls)

            # Pydanticスキーマ情報の取得
            schema_info = None
            if is_pydantic_model:
                schema_info = self._get_pydantic_schema(type_cls)

            processing_time = (time.time() - start_time) * 1000

            return TypeInspectionResult(
                type_name=type_name,
                is_pydantic_model=is_pydantic_model,
                has_docstring=has_docstring,
                docstring_content=docstring,
                code_blocks=code_blocks,
                schema_info=schema_info,
                inspection_time_ms=processing_time,
            )

        except Exception:
            processing_time = (time.time() - start_time) * 1000
            return TypeInspectionResult(
                type_name=getattr(type_cls, "__name__", str(type_cls)),
                is_pydantic_model=False,
                has_docstring=False,
                inspection_time_ms=processing_time,
            )

    def _get_docstring(self, type_cls: type[Any]) -> str | None:
        """型クラスのdocstringを取得する内部メソッド"""
        return getattr(type_cls, "__doc__", None)

    def _extract_code_blocks(self, docstring: str) -> list[str]:
        """docstringからコードブロックを抽出する内部メソッド"""
        # 簡易的な実装(実際はより複雑な処理が必要)
        lines = docstring.split("\n")
        code_blocks: list[str] = []

        current_block: list[str] = []
        in_code_block = False

        for line in lines:
            if line.strip().startswith("```"):
                if in_code_block:
                    # コードブロック終了
                    code_blocks.append("\n".join(current_block))
                    current_block = []
                    in_code_block = False
                else:
                    # コードブロック開始
                    in_code_block = True
            elif in_code_block:
                current_block.append(line)

        return code_blocks

    def _is_pydantic_model(self, type_cls: type[Any]) -> bool:
        """Pydanticモデルかどうかをチェックする内部メソッド"""
        try:
            from pydantic import BaseModel

            if not isinstance(type_cls, type):
                return False
            return issubclass(type_cls, BaseModel)
        except Exception:
            return False

    def _get_pydantic_schema(self, type_cls: type[Any]) -> PydanticSchemaInfo | None:
        """Pydanticモデルのスキーマ情報を取得する内部メソッド"""
        try:
            if self._is_pydantic_model(type_cls):
                # Pydantic v2ではmodel_json_schema()がdict[str, Any]を返すと宣言されているため、
                # 静的型システムではPydanticSchemaInfoとの一致を保証できない
                return type_cls.model_json_schema()  # type: ignore[return-value]
        except Exception:
            pass
        return None


class MarkdownBuilderService(BaseModel):
    """
    マークダウン生成のサービスクラス

    このクラスは、マークダウン生成処理のビジネスロジックを実装します。
    """

    def build_document(
        self,
        structure: DocumentStructure,
        config: MarkdownGenerationConfig | None = None,
    ) -> str:
        """
        ドキュメント構造からマークダウン文字列を生成します。

        Args:
            structure: ドキュメント構造
            config: マークダウン生成設定（Noneの場合、デフォルト設定を使用）

        Returns:
            生成されたマークダウン文字列
        """
        config = config or MarkdownGenerationConfig()

        lines = []

        # タイトル
        lines.append(f"{'#' * config.section_level} {structure.title}")
        lines.append("")

        # メタデータ
        if structure.metadata:
            lines.append("**Metadata:**")
            for key, value in structure.metadata.items():
                lines.append(f"- {key}: {value}")
            lines.append("")

        # セクション
        for section in structure.sections:
            section_content = self._build_section_recursive(section, config)
            lines.append(section_content)

        # 目次(設定されている場合)
        if config.include_toc and structure.toc:
            lines.append("## Table of Contents")
            lines.append("")
            for item in structure.toc:
                anchor = item.title.lower().replace(" ", "-")
                lines.append(f"{'  ' * (item.level - 1)}* [{item.title}](#{anchor})")
            lines.append("")

        return "\n".join(lines)

    def _build_section_recursive(
        self,
        section: MarkdownSectionInfo,
        config: MarkdownGenerationConfig,
        current_level: int = 1,
    ) -> str:
        """セクションを再帰的に構築する内部メソッド"""
        lines = []

        # セクションヘッダー
        header_level = min(config.section_level + current_level - 1, 6)
        lines.append(f"{'#' * header_level} {section.title}")
        lines.append("")

        # コンテンツ
        lines.append(section.content)
        lines.append("")

        # コードブロック
        for code_block in section.code_blocks:
            if config.include_code_syntax:
                lines.append(f"```{config.code_language}")
                lines.append(code_block)
                lines.append("```")
                lines.append("")

        # サブセクション
        for subsection in section.subsections:
            subsection_content = self._build_section_recursive(subsection, config, current_level + 1)
            lines.append(subsection_content)

        return "\n".join(lines)


class FileSystemService(BaseModel):
    """
    ファイルシステム操作のサービスクラス

    このクラスは、ファイルシステム操作のビジネスロジックを実装します。
    """

    config: FileSystemConfig = Field(default_factory=FileSystemConfig)

    # TODO: プロトコル更新時にbooleanパラメータをキーワード専用引数に変換 (parents, exist_ok)
    def mkdir(self, path: str | Path, parents: bool = True, exist_ok: bool = True) -> None:
        """
        ディレクトリを作成します。

        Args:
            path: 作成するディレクトリのパス
            parents: 親ディレクトリも作成するかどうか
            exist_ok: 既に存在する場合にエラーを発生させないかどうか
        """
        Path(path).mkdir(parents=parents, exist_ok=exist_ok)

    # TODO: プロトコル更新時にbooleanパラメータをキーワード専用引数に変換 (encoding)
    def write_text(self, path: str | Path, content: str, encoding: str = "utf-8") -> None:
        """
        テキストファイルに書き込みます。

        Args:
            path: 書き込み先のパス
            content: 書き込む内容
            encoding: エンコーディング
        """
        path_obj = Path(path)

        # バックアップ処理(設定されている場合)
        if self.config.backup_existing and path_obj.exists():
            backup_path = path_obj.with_suffix(f"{path_obj.suffix}.backup")
            import shutil

            shutil.copy2(path_obj, backup_path)

        # 上書き確認(設定されている場合)
        if not self.config.overwrite_existing and path_obj.exists():
            raise FileExistsError(f"ファイルが既に存在します: {path}")

        # ディレクトリ作成
        if self.config.create_directories:
            path_obj.parent.mkdir(parents=True, exist_ok=True)

        # ファイル書き込み
        path_obj.write_text(content, encoding=encoding)

    def read_text(self, path: str | Path, encoding: str = "utf-8") -> str:
        """
        テキストファイルを読み込みます。

        Args:
            path: 読み込み元のパス
            encoding: エンコーディング

        Returns:
            ファイルの内容
        """
        return Path(path).read_text(encoding=encoding)

    def exists(self, path: str | Path) -> bool:
        """
        パスが存在するかどうかを確認します。

        Args:
            path: 確認対象のパス

        Returns:
            存在する場合はTrue、そうでない場合はFalse
        """
        return Path(path).exists()

    def is_file(self, path: str | Path) -> bool:
        """
        パスがファイルかどうかを確認します。

        Args:
            path: 確認対象のパス

        Returns:
            ファイルの場合はTrue、そうでない場合はFalse
        """
        return Path(path).is_file()


class TemplateProcessorService(BaseModel):
    """
    テンプレート処理のサービスクラス

    このクラスは、テンプレート処理のビジネスロジックを実装します。
    """

    def load_template(self, template_name: str) -> str:
        """
        テンプレートを読み込みます。

        Args:
            template_name: テンプレート名

        Returns:
            テンプレートの内容
        """
        # 簡易的な実装(実際はテンプレートファイルから読み込む)
        templates = {
            "default": "# {{title}}\n\n{{content}}",
            "api": "# API Documentation\n\n## {{type_name}}\n\n{{description}}",
        }

        return templates.get(template_name, templates["default"])

    def process_template(
        self,
        template_content: str,
        variables: dict[str, Any],  # TODO: Any required for TemplateProcessorProtocol
        config: TemplateConfig | None = None,
    ) -> str:
        """
        テンプレートを処理します。

        Args:
            template_content: テンプレートの内容
            variables: テンプレート変数
            config: テンプレート設定（Noneの場合、デフォルト設定を使用）

        Returns:
            処理されたテンプレート文字列
        """
        # 簡易的なテンプレート処理(実際はより高度なテンプレートエンジンを使用)
        result = template_content

        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value))

        return result

    def render_document(
        self,
        template_name: str,
        variables: dict[str, Any],  # TODO: Any required for TemplateProcessorProtocol
        output_path: str | Path,
        config: DocumentConfig | None = None,
    ) -> None:
        """
        テンプレートからドキュメントをレンダリングして保存します。

        Args:
            template_name: テンプレート名
            variables: テンプレート変数
            output_path: 出力パス
            config: ドキュメント設定（Noneの場合、デフォルト設定を使用）
        """
        # テンプレートの読み込み
        template_content = self.load_template(template_name)

        # テンプレートの処理(DocumentConfigからTemplateConfigを作成)
        template_config = (
            TemplateConfig(
                template_name=config.template_name or "default",
                variables=variables,
            )
            if config
            else None
        )
        processed_content = self.process_template(template_content, variables, template_config)

        # ファイル出力
        Path(output_path).write_text(processed_content, encoding=config.encoding if config else "utf-8")


class BatchProcessorService(BaseModel):
    """
    バッチ処理のサービスクラス

    このクラスは、バッチ処理のビジネスロジックを実装します。
    """

    def process_batch(self, config: BatchGenerationConfig) -> BatchGenerationResult:
        """
        バッチ処理を実行します。

        Args:
            config: バッチ生成設定

        Returns:
            バッチ処理結果
        """
        start_time = time.time()
        results: list[GenerationResult] = []
        successful_files = 0
        failed_files = 0
        error_summary: dict[str, int] = {}

        try:
            # 出力ディレクトリの作成
            output_dir_path = config.output_path
            output_dir = Path(output_dir_path)
            output_dir.mkdir(parents=True, exist_ok=True)

            # 各入力ファイルの処理
            for input_path in config.input_paths:
                try:
                    input_file_path = str(input_path) if input_path else ""
                    input_file = Path(input_file_path)

                    # 基本的なファイル処理(簡易版)
                    # 実際の実装では各ファイルの種類に応じた処理が必要
                    content = input_file.read_text(encoding="utf-8")
                    output_file = output_dir / f"{input_file.stem}_processed.md"

                    # 簡易的な処理(実際はより複雑な処理が必要)
                    processed_content = f"# Processed: {input_file.name}\n\n{content}"
                    output_file.write_text(processed_content, encoding="utf-8")

                    results.append(
                        GenerationResult(
                            success=True,
                            output_path=str(output_file),
                            generation_time_ms=0,
                            files_count=1,
                        )
                    )
                    successful_files += 1

                except Exception as e:
                    error_msg = str(e)
                    results.append(
                        GenerationResult(
                            success=False,
                            output_path=str(input_path),
                            generation_time_ms=0,
                            error_message=error_msg,
                            files_count=0,
                        )
                    )
                    failed_files += 1

                    # エラータイプの集計
                    error_type = type(e).__name__
                    error_summary[error_type] = error_summary.get(error_type, 0) + 1

            total_time = (time.time() - start_time) * 1000

            return BatchGenerationResult(
                success=failed_files == 0,
                total_files=len(config.input_paths),
                successful_files=successful_files,
                failed_files=failed_files,
                total_generation_time_ms=total_time,
                results=results,
                error_summary=error_summary,
            )

        except Exception:
            total_time = (time.time() - start_time) * 1000
            return BatchGenerationResult(
                success=False,
                total_files=len(config.input_paths),
                successful_files=successful_files,
                failed_files=failed_files + 1,
                total_generation_time_ms=total_time,
                results=results,
                error_summary={"BatchProcessingError": 1},
            )

    def process_directory(
        self,
        input_directory: str | Path,
        output_path: str | Path,
        _config: DocumentConfig | None = None,  # 将来の拡張機能用に予約済みパラメータ
    ) -> BatchGenerationResult:
        """
        ディレクトリ内のファイルを一括処理します。

        Args:
            input_directory: 入力ディレクトリ
            output_path: 出力ディレクトリ
            _config: ドキュメント設定（将来の拡張機能用に予約済み、現在未使用）

        Returns:
            バッチ処理結果
        """
        input_dir = Path(input_directory)
        output_dir = Path(output_path)

        # 入力ディレクトリ内のPythonファイルを取得
        if not input_dir.exists():
            return BatchGenerationResult(
                success=False,
                total_files=0,
                successful_files=0,
                failed_files=0,
                total_generation_time_ms=0,
                error_summary={"InputDirectoryNotFound": 1},
            )

        # Pythonファイルのみを対象とする
        input_files = list(input_dir.rglob("*.py"))

        # バッチ処理設定を作成
        batch_config = BatchGenerationConfig(
            input_paths=[str(f) for f in input_files],
            output_path=str(output_dir),
            parallel_processing=False,  # 簡易版では並列処理なし
            continue_on_error=True,
        )

        return self.process_batch(batch_config)


class DocumentationOrchestrator(BaseModel):
    """
    ドキュメント生成のオーケストレータークラス

    このクラスは、複数のサービスを統合してドキュメント生成を統制します。
    """

    document_generator: DocumentGeneratorService = Field(default_factory=DocumentGeneratorService)
    type_inspector: TypeInspectorService = Field(default_factory=TypeInspectorService)
    markdown_builder: MarkdownBuilderService = Field(default_factory=MarkdownBuilderService)
    file_system: FileSystemService = Field(default_factory=FileSystemService)
    template_processor: TemplateProcessorService = Field(default_factory=TemplateProcessorService)
    batch_processor: BatchProcessorService = Field(default_factory=BatchProcessorService)

    def generate_comprehensive_documentation(
        self,
        types: dict[TypeName, type[Any]],
        output_path: str | Path,
        _config: DocumentConfig | None = None,  # 将来の拡張機能用に予約済みパラメータ
    ) -> GenerationResult:
        """
        包括的なドキュメントを生成します。

        Args:
            types: 型定義の辞書
            output_path: 出力パス
            config: ドキュメント設定（Noneの場合、デフォルト設定を使用）

        Returns:
            生成結果
        """
        start_time = time.time()

        try:
            # 型検査の実行
            inspection_results = []
            for _, type_cls in types.items():
                result = self.type_inspector.inspect_type(type_cls)
                inspection_results.append(result)

            # ドキュメント構造の構築
            sections = []
            for result in inspection_results:
                if result.has_docstring and result.docstring_content:
                    section = MarkdownSectionInfo(
                        title=result.type_name,
                        level=2,
                        content=result.docstring_content or "",
                        code_blocks=result.code_blocks,
                    )
                    sections.append(section)

            structure = DocumentStructure(
                title="Type Documentation",
                sections=sections,
                metadata=create_empty_metadata(),
                generation_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            )

            # マークダウン生成
            markdown_content = self.markdown_builder.build_document(structure)

            # ファイル出力
            output_file = Path(output_path) / "types.md"
            self.file_system.write_text(output_file, markdown_content)

            processing_time = (time.time() - start_time) * 1000

            return GenerationResult(
                success=True,
                output_path=str(output_path),
                generated_files=[str(output_file)],
                generation_time_ms=processing_time,
                files_count=1,
            )

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            return GenerationResult(
                success=False,
                output_path=str(output_path),
                generation_time_ms=processing_time,
                error_message=str(e),
                files_count=0,
            )
