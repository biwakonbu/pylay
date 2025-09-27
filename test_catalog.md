# テストカタログ

**生成日**: 2025-09-27T14:09:48.466064

## test_generate_test_docs.py

### TestGenerateTestDocs.test_generate_test_docs_with_empty_directory
**説明**: 空のディレクトリでの動作確認

**実行**: `pytest tests/test_generate_test_docs.py::TestGenerateTestDocs.test_generate_test_docs_with_empty_directory -v`

### TestGenerateTestDocs.test_generate_test_docs_with_mixed_files
**説明**: テストファイルと非テストファイルが混在する場合の動作確認

**実行**: `pytest tests/test_generate_test_docs.py::TestGenerateTestDocs.test_generate_test_docs_with_mixed_files -v`

### TestGenerateTestDocs.test_generate_test_docs_with_no_docstring
**説明**: docstringなしのテスト関数での動作確認

**実行**: `pytest tests/test_generate_test_docs.py::TestGenerateTestDocs.test_generate_test_docs_with_no_docstring -v`

### TestGenerateTestDocs.test_generate_test_docs_with_valid_files
**説明**: 有効なテストファイルでのドキュメント生成テスト

**実行**: `pytest tests/test_generate_test_docs.py::TestGenerateTestDocs.test_generate_test_docs_with_valid_files -v`

### TestGenerateTestDocsErrorHandling.test_generate_test_docs_with_invalid_module
**説明**: 無効なモジュールでの動作確認

**実行**: `pytest tests/test_generate_test_docs.py::TestGenerateTestDocsErrorHandling.test_generate_test_docs_with_invalid_module -v`

### TestGenerateTestDocsErrorHandling.test_generate_test_docs_with_nonexistent_directory
**説明**: 存在しないディレクトリでの動作確認

**実行**: `pytest tests/test_generate_test_docs.py::TestGenerateTestDocsErrorHandling.test_generate_test_docs_with_nonexistent_directory -v`

### TestGenerateTestDocsOutputFormat.test_module_count_calculation
**説明**: モジュール数の計算が正しいことを確認

**実行**: `pytest tests/test_generate_test_docs.py::TestGenerateTestDocsOutputFormat.test_module_count_calculation -v`

### TestGenerateTestDocsOutputFormat.test_output_includes_timestamp
**説明**: 出力にタイムスタンプが含まれることを確認

**実行**: `pytest tests/test_generate_test_docs.py::TestGenerateTestDocsOutputFormat.test_output_includes_timestamp -v`

### TestGenerateTestDocsOutputFormat.test_pytest_command_format
**説明**: pytestコマンドの形式が正しいことを確認

**実行**: `pytest tests/test_generate_test_docs.py::TestGenerateTestDocsOutputFormat.test_pytest_command_format -v`

## test_generate_type_docs.py

### TestGenerateTypeDocs.test_generate_docs_creates_index
**説明**: 全ドキュメント生成でインデックスファイルが作成されることを確認

**実行**: `pytest tests/test_generate_type_docs.py::TestGenerateTypeDocs.test_generate_docs_creates_index -v`

### TestGenerateTypeDocs.test_generate_layer_docs_creates_directory
**説明**: 出力ディレクトリが自動作成されることを確認

**実行**: `pytest tests/test_generate_type_docs.py::TestGenerateTypeDocs.test_generate_layer_docs_creates_directory -v`

### TestGenerateTypeDocs.test_generate_layer_docs_skip_newtype
**説明**: NewTypeが正しく除外されることを確認

**実行**: `pytest tests/test_generate_type_docs.py::TestGenerateTypeDocs.test_generate_layer_docs_skip_newtype -v`

### TestGenerateTypeDocs.test_generate_layer_docs_with_typealias_descriptions
**説明**: TypeAlias用の説明が正しく適用されることを確認

**実行**: `pytest tests/test_generate_type_docs.py::TestGenerateTypeDocs.test_generate_layer_docs_with_typealias_descriptions -v`

### TestGenerateTypeDocs.test_generate_layer_docs_with_valid_types
**説明**: 有効な型でのレイヤードキュメント生成テスト

**実行**: `pytest tests/test_generate_type_docs.py::TestGenerateTypeDocs.test_generate_layer_docs_with_valid_types -v`

### TestGenerateTypeDocsErrorHandling.test_generate_layer_docs_with_empty_registry
**説明**: 空のレジストリでの動作確認

**実行**: `pytest tests/test_generate_type_docs.py::TestGenerateTypeDocsErrorHandling.test_generate_layer_docs_with_empty_registry -v`

### TestGenerateTypeDocsErrorHandling.test_generate_layer_docs_with_invalid_output_path
**説明**: 無効な出力パスでの動作確認

**実行**: `pytest tests/test_generate_type_docs.py::TestGenerateTypeDocsErrorHandling.test_generate_layer_docs_with_invalid_output_path -v`

### TestGenerateTypeDocsPerformance.test_generate_layer_docs_large_registry
**説明**: 大規模レジストリでのパフォーマンステスト

**実行**: `pytest tests/test_generate_type_docs.py::TestGenerateTypeDocsPerformance.test_generate_layer_docs_large_registry -v`

## test_integration_doc_generators.py

### TestBackwardCompatibility.test_existing_import_paths_work
**説明**: Test that existing import paths continue to work.

**実行**: `pytest tests/test_integration_doc_generators.py::TestBackwardCompatibility.test_existing_import_paths_work -v`

### TestBackwardCompatibility.test_generate_test_docs_api_unchanged
**説明**: Test that generate_test_docs API remains unchanged.

**実行**: `pytest tests/test_integration_doc_generators.py::TestBackwardCompatibility.test_generate_test_docs_api_unchanged -v`

### TestBackwardCompatibility.test_generate_type_docs_api_unchanged
**説明**: Test that generate_type_docs API remains unchanged.

**実行**: `pytest tests/test_integration_doc_generators.py::TestBackwardCompatibility.test_generate_type_docs_api_unchanged -v`

### TestBackwardCompatibility.test_output_format_unchanged
**説明**: Test that output format matches pre-refactoring expectations.

**実行**: `pytest tests/test_integration_doc_generators.py::TestBackwardCompatibility.test_output_format_unchanged -v`

### TestDocGeneratorsIntegration.test_both_generators_create_compatible_output
**説明**: Test that both generators create compatible documentation.

**実行**: `pytest tests/test_integration_doc_generators.py::TestDocGeneratorsIntegration.test_both_generators_create_compatible_output -v`

### TestDocGeneratorsIntegration.test_configuration_consistency
**説明**: Test that configuration is applied consistently across generators.

**実行**: `pytest tests/test_integration_doc_generators.py::TestDocGeneratorsIntegration.test_configuration_consistency -v`

### TestDocGeneratorsIntegration.test_content_quality_standards
**説明**: Test that both generators meet the same content quality standards.

**実行**: `pytest tests/test_integration_doc_generators.py::TestDocGeneratorsIntegration.test_content_quality_standards -v`

### TestDocGeneratorsIntegration.test_error_isolation_between_generators
**説明**: Test that errors in one generator don't affect the other.

**実行**: `pytest tests/test_integration_doc_generators.py::TestDocGeneratorsIntegration.test_error_isolation_between_generators -v`

### TestDocGeneratorsIntegration.test_output_directory_structure
**説明**: Test that both generators respect the expected directory structure.

**実行**: `pytest tests/test_integration_doc_generators.py::TestDocGeneratorsIntegration.test_output_directory_structure -v`

### TestDocGeneratorsIntegration.test_parallel_generation_workflow
**説明**: Test that both generators can run in parallel without conflicts.

**実行**: `pytest tests/test_integration_doc_generators.py::TestDocGeneratorsIntegration.test_parallel_generation_workflow -v`

### TestDocGeneratorsIntegration.test_shared_infrastructure_consistency
**説明**: Test that shared infrastructure provides consistent behavior.

**実行**: `pytest tests/test_integration_doc_generators.py::TestDocGeneratorsIntegration.test_shared_infrastructure_consistency -v`

### TestPerformanceIntegration.test_generation_performance_acceptable
**説明**: Test that documentation generation completes in reasonable time.

**実行**: `pytest tests/test_integration_doc_generators.py::TestPerformanceIntegration.test_generation_performance_acceptable -v`

### TestPerformanceIntegration.test_memory_usage_reasonable
**説明**: Test that generators don't consume excessive memory.

**実行**: `pytest tests/test_integration_doc_generators.py::TestPerformanceIntegration.test_memory_usage_reasonable -v`

## test_migrations.py

## test_refactored_generate_test_docs.py

### TestCatalogGenerator.test_count_test_modules_accurate
**説明**: Test that module counting is accurate.

**実行**: `pytest tests/test_refactored_generate_test_docs.py::TestCatalogGenerator.test_count_test_modules_accurate -v`

### TestCatalogGenerator.test_extract_test_functions_finds_methods
**説明**: Test that function extraction finds both functions and class methods.

**実行**: `pytest tests/test_refactored_generate_test_docs.py::TestCatalogGenerator.test_extract_test_functions_finds_methods -v`

### TestCatalogGenerator.test_format_generation_footer
**説明**: Test generation footer formatting.

**実行**: `pytest tests/test_refactored_generate_test_docs.py::TestCatalogGenerator.test_format_generation_footer -v`

### TestCatalogGenerator.test_generate_creates_output_file
**説明**: Test that generate() creates output file.

**実行**: `pytest tests/test_refactored_generate_test_docs.py::TestCatalogGenerator.test_generate_creates_output_file -v`

### TestCatalogGenerator.test_generate_handles_test_classes
**説明**: Test that generator correctly handles test classes and methods.

**実行**: `pytest tests/test_refactored_generate_test_docs.py::TestCatalogGenerator.test_generate_handles_test_classes -v`

### TestCatalogGenerator.test_generate_includes_timestamp
**説明**: Test that generated document includes timestamp.

**実行**: `pytest tests/test_refactored_generate_test_docs.py::TestCatalogGenerator.test_generate_includes_timestamp -v`

### TestCatalogGenerator.test_generate_with_custom_output_path
**説明**: Test generation with custom output path override.

**実行**: `pytest tests/test_refactored_generate_test_docs.py::TestCatalogGenerator.test_generate_with_custom_output_path -v`

### TestCatalogGenerator.test_generator_initialization
**説明**: Test generator initializes correctly.

**実行**: `pytest tests/test_refactored_generate_test_docs.py::TestCatalogGenerator.test_generator_initialization -v`

### TestCatalogGenerator.test_import_module_handles_errors_gracefully
**説明**: Test that module import errors are handled gracefully.

**実行**: `pytest tests/test_refactored_generate_test_docs.py::TestCatalogGenerator.test_import_module_handles_errors_gracefully -v`

### TestCatalogGenerator.test_scan_test_modules_filters_correctly
**説明**: Test that module scanning respects include/exclude patterns.

**実行**: `pytest tests/test_refactored_generate_test_docs.py::TestCatalogGenerator.test_scan_test_modules_filters_correctly -v`

### TestCatalogGeneratorErrorHandling.test_handles_module_import_errors
**説明**: Test graceful handling of module import errors.

**実行**: `pytest tests/test_refactored_generate_test_docs.py::TestCatalogGeneratorErrorHandling.test_handles_module_import_errors -v`

### TestCatalogGeneratorErrorHandling.test_handles_recursion_errors
**説明**: Test graceful handling of recursion errors.

**実行**: `pytest tests/test_refactored_generate_test_docs.py::TestCatalogGeneratorErrorHandling.test_handles_recursion_errors -v`

### TestInMemoryFileSystem.test_file_not_found_error
**説明**: Test FileNotFoundError for non-existent files.

**実行**: `pytest tests/test_refactored_generate_test_docs.py::TestInMemoryFileSystem.test_file_not_found_error -v`

### TestInMemoryFileSystem.test_list_files
**説明**: Test listing files.

**実行**: `pytest tests/test_refactored_generate_test_docs.py::TestInMemoryFileSystem.test_list_files -v`

### TestInMemoryFileSystem.test_mkdir_creates_directories
**説明**: Test directory creation.

**実行**: `pytest tests/test_refactored_generate_test_docs.py::TestInMemoryFileSystem.test_mkdir_creates_directories -v`

### TestInMemoryFileSystem.test_write_and_read_file
**説明**: Test writing and reading files.

**実行**: `pytest tests/test_refactored_generate_test_docs.py::TestInMemoryFileSystem.test_write_and_read_file -v`

### TestInMemoryFileSystem.test_write_creates_parent_directories
**説明**: Test that writing files creates parent directories.

**実行**: `pytest tests/test_refactored_generate_test_docs.py::TestInMemoryFileSystem.test_write_creates_parent_directories -v`

### TestMarkdownBuilder.test_bullet_points
**説明**: Test bullet point generation.

**実行**: `pytest tests/test_refactored_generate_test_docs.py::TestMarkdownBuilder.test_bullet_points -v`

### TestMarkdownBuilder.test_clear_functionality
**説明**: Test that clear() empties the content.

**実行**: `pytest tests/test_refactored_generate_test_docs.py::TestMarkdownBuilder.test_clear_functionality -v`

### TestMarkdownBuilder.test_code_block
**説明**: Test code block generation.

**実行**: `pytest tests/test_refactored_generate_test_docs.py::TestMarkdownBuilder.test_code_block -v`

### TestMarkdownBuilder.test_fluent_api_chaining
**説明**: Test that all methods return self for chaining.

**実行**: `pytest tests/test_refactored_generate_test_docs.py::TestMarkdownBuilder.test_fluent_api_chaining -v`

### TestMarkdownBuilder.test_formatting_helpers
**説明**: Test text formatting helpers.

**実行**: `pytest tests/test_refactored_generate_test_docs.py::TestMarkdownBuilder.test_formatting_helpers -v`

### TestMarkdownBuilder.test_heading_generation
**説明**: Test heading generation with different levels.

**実行**: `pytest tests/test_refactored_generate_test_docs.py::TestMarkdownBuilder.test_heading_generation -v`

### TestMarkdownBuilder.test_invalid_heading_level
**説明**: Test that invalid heading levels raise error.

**実行**: `pytest tests/test_refactored_generate_test_docs.py::TestMarkdownBuilder.test_invalid_heading_level -v`

### TestMarkdownBuilder.test_paragraph_and_line_break
**説明**: Test paragraph and line break generation.

**実行**: `pytest tests/test_refactored_generate_test_docs.py::TestMarkdownBuilder.test_paragraph_and_line_break -v`

### TestMarkdownBuilder.test_table_generation
**説明**: Test table generation.

**実行**: `pytest tests/test_refactored_generate_test_docs.py::TestMarkdownBuilder.test_table_generation -v`

## test_refactored_generate_type_docs.py

### TestConfigurationIntegration.test_generators_use_config_output_directory
**説明**: Test generators respect output directory configuration.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestConfigurationIntegration.test_generators_use_config_output_directory -v`

### TestConfigurationIntegration.test_layer_generator_uses_config_descriptions
**説明**: Test LayerDocGenerator uses custom type descriptions.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestConfigurationIntegration.test_layer_generator_uses_config_descriptions -v`

### TestConfigurationIntegration.test_layer_generator_uses_config_skip_types
**説明**: Test LayerDocGenerator respects skip_types configuration.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestConfigurationIntegration.test_layer_generator_uses_config_skip_types -v`

### TestGeneratorErrorHandling.test_index_generator_handles_empty_registry
**説明**: Test IndexDocGenerator handles empty type registry.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestGeneratorErrorHandling.test_index_generator_handles_empty_registry -v`

### TestGeneratorErrorHandling.test_layer_generator_handles_missing_docstring
**説明**: Test LayerDocGenerator handles types without docstrings.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestGeneratorErrorHandling.test_layer_generator_handles_missing_docstring -v`

### TestGeneratorErrorHandling.test_layer_generator_handles_pydantic_schema_errors
**説明**: Test LayerDocGenerator handles Pydantic schema generation errors.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestGeneratorErrorHandling.test_layer_generator_handles_pydantic_schema_errors -v`

### TestIndexDocGenerator.test_generate_creates_output_file
**説明**: Test that generate() creates output file.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestIndexDocGenerator.test_generate_creates_output_file -v`

### TestIndexDocGenerator.test_generate_includes_footer
**説明**: Test that generated index includes footer.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestIndexDocGenerator.test_generate_includes_footer -v`

### TestIndexDocGenerator.test_generate_includes_layer_sections
**説明**: Test that generated index includes layer detail sections.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestIndexDocGenerator.test_generate_includes_layer_sections -v`

### TestIndexDocGenerator.test_generate_includes_statistics
**説明**: Test that generated index includes statistics section.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestIndexDocGenerator.test_generate_includes_statistics -v`

### TestIndexDocGenerator.test_generate_includes_unified_usage_section
**説明**: Test that generated index includes unified usage section.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestIndexDocGenerator.test_generate_includes_unified_usage_section -v`

### TestIndexDocGenerator.test_generate_layer_links
**説明**: Test that layer sections include links to detailed documentation.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestIndexDocGenerator.test_generate_layer_links -v`

### TestIndexDocGenerator.test_generate_type_preview
**説明**: Test that layer sections show preview of main types.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestIndexDocGenerator.test_generate_type_preview -v`

### TestIndexDocGenerator.test_generate_with_custom_output_path
**説明**: Test generation with custom output path override.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestIndexDocGenerator.test_generate_with_custom_output_path -v`

### TestIndexDocGenerator.test_generator_initialization
**説明**: Test generator initializes correctly.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestIndexDocGenerator.test_generator_initialization -v`

### TestLayerDocGenerator.test_generate_creates_output_file
**説明**: Test that generate() creates output file.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestLayerDocGenerator.test_generate_creates_output_file -v`

### TestLayerDocGenerator.test_generate_includes_auto_growth_section
**説明**: Test that generated document includes auto-growth explanation.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestLayerDocGenerator.test_generate_includes_auto_growth_section -v`

### TestLayerDocGenerator.test_generate_includes_footer
**説明**: Test that generated document includes footer.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestLayerDocGenerator.test_generate_includes_footer -v`

### TestLayerDocGenerator.test_generate_layer_specific_usage
**説明**: Test that layer-specific usage examples are included.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestLayerDocGenerator.test_generate_layer_specific_usage -v`

### TestLayerDocGenerator.test_generate_skips_configured_types
**説明**: Test that generation skips types in skip_types configuration.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestLayerDocGenerator.test_generate_skips_configured_types -v`

### TestLayerDocGenerator.test_generate_with_custom_output_path
**説明**: Test generation with custom output path override.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestLayerDocGenerator.test_generate_with_custom_output_path -v`

### TestLayerDocGenerator.test_generate_with_pydantic_types
**説明**: Test generation with Pydantic model types.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestLayerDocGenerator.test_generate_with_pydantic_types -v`

### TestLayerDocGenerator.test_generator_initialization
**説明**: Test generator initializes correctly.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestLayerDocGenerator.test_generator_initialization -v`

### TestTypeInspector.test_extract_code_blocks_with_markdown
**説明**: Test extracting code blocks from docstring with markdown.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestTypeInspector.test_extract_code_blocks_with_markdown -v`

### TestTypeInspector.test_extract_code_blocks_without_markdown
**説明**: Test extracting from docstring without code blocks.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestTypeInspector.test_extract_code_blocks_without_markdown -v`

### TestTypeInspector.test_format_type_definition_fallback
**説明**: Test formatting with fallback for unknown types.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestTypeInspector.test_format_type_definition_fallback -v`

### TestTypeInspector.test_format_type_definition_with_newtype
**説明**: Test formatting NewType definition.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestTypeInspector.test_format_type_definition_with_newtype -v`

### TestTypeInspector.test_format_type_definition_with_pydantic
**説明**: Test formatting Pydantic type definition.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestTypeInspector.test_format_type_definition_with_pydantic -v`

### TestTypeInspector.test_get_docstring_from_class
**説明**: Test extracting docstring from a class.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestTypeInspector.test_get_docstring_from_class -v`

### TestTypeInspector.test_get_docstring_from_class_without_docstring
**説明**: Test extracting docstring from class without docstring.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestTypeInspector.test_get_docstring_from_class_without_docstring -v`

### TestTypeInspector.test_get_newtype_supertype
**説明**: Test getting NewType supertype.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestTypeInspector.test_get_newtype_supertype -v`

### TestTypeInspector.test_get_pydantic_schema
**説明**: Test getting Pydantic JSON schema.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestTypeInspector.test_get_pydantic_schema -v`

### TestTypeInspector.test_get_pydantic_schema_with_non_pydantic
**説明**: Test getting schema from non-Pydantic class.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestTypeInspector.test_get_pydantic_schema_with_non_pydantic -v`

### TestTypeInspector.test_initialization_with_custom_skip_types
**説明**: Test initialization with custom skip types.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestTypeInspector.test_initialization_with_custom_skip_types -v`

### TestTypeInspector.test_initialization_with_default_skip_types
**説明**: Test that TypeInspector initializes with default skip types.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestTypeInspector.test_initialization_with_default_skip_types -v`

### TestTypeInspector.test_is_newtype_with_mock_newtype
**説明**: Test NewType detection with mock NewType.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestTypeInspector.test_is_newtype_with_mock_newtype -v`

### TestTypeInspector.test_is_newtype_with_regular_type
**説明**: Test NewType detection with regular type.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestTypeInspector.test_is_newtype_with_regular_type -v`

### TestTypeInspector.test_is_pydantic_model_with_pydantic_class
**説明**: Test Pydantic model detection with actual Pydantic class.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestTypeInspector.test_is_pydantic_model_with_pydantic_class -v`

### TestTypeInspector.test_is_pydantic_model_with_regular_class
**説明**: Test Pydantic model detection with regular class.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestTypeInspector.test_is_pydantic_model_with_regular_class -v`

### TestTypeInspector.test_is_standard_newtype_doc_detection
**説明**: Test detection of standard NewType documentation.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestTypeInspector.test_is_standard_newtype_doc_detection -v`

### TestTypeInspector.test_should_skip_type
**説明**: Test type skipping logic.

**実行**: `pytest tests/test_refactored_generate_type_docs.py::TestTypeInspector.test_should_skip_type -v`

## test_type_management.py

### test_basic_types
**説明**: 全基本型の個別テスト

**実行**: `pytest tests/test_type_management.py::test_basic_types -v`

### test_build_registry
**説明**: 型レジストリの構築をテスト

**実行**: `pytest tests/test_type_management.py::test_build_registry -v`

### test_circular_reference_detection
**説明**: 循環参照検出のテスト

**実行**: `pytest tests/test_type_management.py::test_circular_reference_detection -v`

### test_complex_union_types
**説明**: 複雑なUnion型のテスト

**実行**: `pytest tests/test_type_management.py::test_complex_union_types -v`

### test_error_handling
**説明**: エラーハンドリングのテスト

**実行**: `pytest tests/test_type_management.py::test_error_handling -v`

### test_field_level_docstrings
**説明**: フィールドレベルdocstringのテスト

**実行**: `pytest tests/test_type_management.py::test_field_level_docstrings -v`

### test_nested_structures
**説明**: 複雑なネスト構造のテスト

**実行**: `pytest tests/test_type_management.py::test_nested_structures -v`

### test_reference_resolution
**説明**: 参照解決のテスト

**実行**: `pytest tests/test_type_management.py::test_reference_resolution -v`

### test_roundtrip
**説明**: 説明なし

**実行**: `pytest tests/test_type_management.py::test_roundtrip -v`

### test_roundtrip_transparency
**説明**: ラウンドトリップ透過性のテスト

**実行**: `pytest tests/test_type_management.py::test_roundtrip_transparency -v`

### test_type_to_yaml
**説明**: 説明なし

**実行**: `pytest tests/test_type_management.py::test_type_to_yaml -v`

### test_v1_1_multiple_types
**説明**: v1.1複数型のテスト

**実行**: `pytest tests/test_type_management.py::test_v1_1_multiple_types -v`

### test_yaml_to_spec_and_validate
**説明**: 説明なし

**実行**: `pytest tests/test_type_management.py::test_yaml_to_spec_and_validate -v`

**総テストモジュール数**: 7
