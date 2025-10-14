"""
自動ドキュメント生成用のドキュメントジェネレーターパッケージ。

このモジュールは、ドキュメント生成機能を提供します。
主な機能：
- 型定義からのドキュメント自動生成
- マークダウン形式のドキュメント出力
- テンプレートベースのドキュメント作成
- バッチ処理による複数ファイル処理
"""

# 型定義のエクスポート
# モデルのエクスポート
from .models import (
    BatchProcessorService,
    DocumentationOrchestrator,
    DocumentGeneratorService,
    FileSystemService,
    MarkdownBuilderService,
    TemplateProcessorService,
    TypeInspectorService,
)

# プロトコルのエクスポート
from .protocols import (
    BatchProcessorProtocol,
    DocumentGeneratorProtocol,
    FileSystemInterfaceProtocol,
    MarkdownBuilderProtocol,
    TemplateProcessorProtocol,
    TypeInspectorProtocol,
)
from .types import (
    BatchGenerationConfig,
    BatchGenerationResult,
    CodeBlock,
    ContentString,
    DocumentationMetrics,
    # 設定クラス
    DocumentConfig,
    DocumentStructure,
    FileSystemConfig,
    GenerationResult,
    MarkdownGenerationConfig,
    MarkdownSection,
    MarkdownSectionInfo,
    # 型エイリアス
    OutputPath,
    PositiveInt,
    TemplateConfig,
    TemplateName,
    TypeInspectionConfig,
    TypeInspectionResult,
    TypeName,
    ValidatedOutputPath,
)

__all__ = [
    "BatchGenerationConfig",
    "BatchGenerationResult",
    "BatchProcessorProtocol",
    "BatchProcessorService",
    "CodeBlock",
    "ContentString",
    # 設定クラス
    "DocumentConfig",
    # プロトコル
    "DocumentGeneratorProtocol",
    # モデル
    "DocumentGeneratorService",
    "DocumentStructure",
    "DocumentationMetrics",
    "DocumentationOrchestrator",
    "FileSystemConfig",
    "FileSystemInterfaceProtocol",
    "FileSystemService",
    # 型定義
    "GenerationResult",
    "MarkdownBuilderProtocol",
    "MarkdownBuilderService",
    "MarkdownGenerationConfig",
    "MarkdownSection",
    "MarkdownSectionInfo",
    # 型エイリアス
    "OutputPath",
    "PositiveInt",
    "TemplateConfig",
    "TemplateName",
    "TemplateProcessorProtocol",
    "TemplateProcessorService",
    "TypeInspectionConfig",
    "TypeInspectionResult",
    "TypeInspectorProtocol",
    "TypeInspectorService",
    "TypeName",
    "ValidatedOutputPath",
]
