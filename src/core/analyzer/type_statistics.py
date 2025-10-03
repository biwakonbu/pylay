"""
型定義の統計情報計算

型定義レベルとドキュメント品質の統計情報を計算します。
"""

from collections import defaultdict
from pathlib import Path

from src.core.analyzer.type_level_models import (
    DocumentationStatistics,
    TypeDefinition,
    TypeStatistics,
)


class TypeStatisticsCalculator:
    """型定義の統計情報を計算するクラス"""

    def calculate(self, type_definitions: list[TypeDefinition]) -> TypeStatistics:
        """統計情報を計算

        Args:
            type_definitions: 型定義のリスト

        Returns:
            TypeStatistics
        """
        if not type_definitions:
            return self._empty_statistics()

        total_count = len(type_definitions)

        # レベル別カウント
        level1_count = sum(1 for td in type_definitions if td.level == "level1")
        level2_count = sum(1 for td in type_definitions if td.level == "level2")
        level3_count = sum(1 for td in type_definitions if td.level == "level3")
        other_count = sum(1 for td in type_definitions if td.level == "other")

        # 比率計算
        level1_ratio = level1_count / total_count if total_count > 0 else 0.0
        level2_ratio = level2_count / total_count if total_count > 0 else 0.0
        level3_ratio = level3_count / total_count if total_count > 0 else 0.0
        other_ratio = other_count / total_count if total_count > 0 else 0.0

        # ディレクトリ別統計
        by_directory = self._calculate_by_directory(type_definitions)

        # カテゴリ別統計
        by_category = self._calculate_by_category(type_definitions)

        # ドキュメント統計
        documentation = self._calculate_documentation_statistics(type_definitions)

        return TypeStatistics(
            total_count=total_count,
            level1_count=level1_count,
            level2_count=level2_count,
            level3_count=level3_count,
            other_count=other_count,
            level1_ratio=level1_ratio,
            level2_ratio=level2_ratio,
            level3_ratio=level3_ratio,
            other_ratio=other_ratio,
            by_directory=by_directory,
            by_category=by_category,
            documentation=documentation,
        )

    def _empty_statistics(self) -> TypeStatistics:
        """空の統計情報を生成"""
        return TypeStatistics(
            total_count=0,
            level1_count=0,
            level2_count=0,
            level3_count=0,
            other_count=0,
            level1_ratio=0.0,
            level2_ratio=0.0,
            level3_ratio=0.0,
            other_ratio=0.0,
            by_directory={},
            by_category={},
            documentation=DocumentationStatistics(
                total_types=0,
                documented_types=0,
                undocumented_types=0,
                implementation_rate=0.0,
                minimal_docstrings=0,
                detailed_docstrings=0,
                detail_rate=0.0,
                avg_docstring_lines=0.0,
                quality_score=0.0,
                by_level={},
                by_format={},
            ),
        )

    def _calculate_by_directory(
        self, type_definitions: list[TypeDefinition]
    ) -> dict[str, dict[str, int]]:
        """ディレクトリ別の統計を計算"""
        by_directory: dict[str, dict[str, int]] = defaultdict(
            lambda: {"level1": 0, "level2": 0, "level3": 0, "other": 0}
        )

        for td in type_definitions:
            directory = str(Path(td.file_path).parent)
            by_directory[directory][td.level] += 1

        return dict(by_directory)

    def _calculate_by_category(
        self, type_definitions: list[TypeDefinition]
    ) -> dict[str, int]:
        """カテゴリ別の統計を計算"""
        by_category: dict[str, int] = defaultdict(int)

        for td in type_definitions:
            by_category[td.category] += 1

        return dict(by_category)

    def _calculate_documentation_statistics(
        self, type_definitions: list[TypeDefinition]
    ) -> DocumentationStatistics:
        """ドキュメント統計を計算"""
        total_types = len(type_definitions)
        documented_types = sum(1 for td in type_definitions if td.has_docstring)
        undocumented_types = total_types - documented_types

        implementation_rate = documented_types / total_types if total_types > 0 else 0.0

        # 最低限のdocstring（1-2行）と詳細なdocstring（3行以上）
        minimal_docstrings = sum(
            1
            for td in type_definitions
            if td.has_docstring and 1 <= td.docstring_lines <= 2
        )
        detailed_docstrings = sum(
            1 for td in type_definitions if td.has_docstring and td.docstring_lines >= 3
        )

        detail_rate = (
            detailed_docstrings / documented_types if documented_types > 0 else 0.0
        )

        # 平均docstring行数
        total_lines = sum(td.docstring_lines for td in type_definitions)
        avg_docstring_lines = total_lines / total_types if total_types > 0 else 0.0

        # 総合品質スコア
        quality_score = implementation_rate * detail_rate

        # レベル別のdocstring統計
        by_level = self._calculate_documentation_by_level(type_definitions)

        # フォーマット別のdocstring数（現時点では未実装）
        by_format: dict[str, int] = {
            "google": 0,
            "numpy": 0,
            "restructured": 0,
            "unknown": 0,
        }

        return DocumentationStatistics(
            total_types=total_types,
            documented_types=documented_types,
            undocumented_types=undocumented_types,
            implementation_rate=implementation_rate,
            minimal_docstrings=minimal_docstrings,
            detailed_docstrings=detailed_docstrings,
            detail_rate=detail_rate,
            avg_docstring_lines=avg_docstring_lines,
            quality_score=quality_score,
            by_level=by_level,
            by_format=by_format,
        )

    def _calculate_documentation_by_level(
        self, type_definitions: list[TypeDefinition]
    ) -> dict[str, dict[str, float]]:
        """レベル別のドキュメント統計を計算"""
        by_level: dict[str, dict[str, float]] = {}

        for level in ["level1", "level2", "level3", "other"]:
            level_types = [td for td in type_definitions if td.level == level]
            total = len(level_types)

            if total > 0:
                documented = sum(1 for td in level_types if td.has_docstring)
                detailed = sum(
                    1
                    for td in level_types
                    if td.has_docstring and td.docstring_lines >= 3
                )

                by_level[level] = {
                    "total": float(total),
                    "documented": float(documented),
                    "implementation_rate": documented / total,
                    "detailed": float(detailed),
                    "detail_rate": detailed / documented if documented > 0 else 0.0,
                }
            else:
                by_level[level] = {
                    "total": 0.0,
                    "documented": 0.0,
                    "implementation_rate": 0.0,
                    "detailed": 0.0,
                    "detail_rate": 0.0,
                }

        return by_level
