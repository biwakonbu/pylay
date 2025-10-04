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
    # 型定義
    "GenerationResult",
    "TypeInspectionResult",
    "MarkdownSectionInfo",
    "DocumentStructure",
    "TemplateConfig",
    "DocumentationMetrics",
    "BatchGenerationConfig",
    "BatchGenerationResult",
    # 設定クラス
    "DocumentConfig",
    "TypeInspectionConfig",
    "MarkdownGenerationConfig",
    "FileSystemConfig",
    # 型エイリアス
    "OutputPath",
    "TemplateName",
    "TypeName",
    "ContentString",
    "CodeBlock",
    "MarkdownSection",
    "ValidatedOutputPath",
    "PositiveInt",
    # プロトコル
    "DocumentGeneratorProtocol",
    "TypeInspectorProtocol",
    "MarkdownBuilderProtocol",
    "FileSystemInterfaceProtocol",
    "TemplateProcessorProtocol",
    "BatchProcessorProtocol",
    # モデル
    "DocumentGeneratorService",
    "TypeInspectorService",
    "MarkdownBuilderService",
    "FileSystemService",
    "TemplateProcessorService",
    "BatchProcessorService",
    "DocumentationOrchestrator",
]
