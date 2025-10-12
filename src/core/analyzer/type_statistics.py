"""
型定義の統計情報計算

型定義レベルとドキュメント品質の統計情報を計算します。
"""

import re
from collections import defaultdict
from pathlib import Path

from src.core.analyzer.docstring_analyzer import DocstringAnalyzer
from src.core.analyzer.type_level_models import (
    DocumentationStatistics,
    TypeDefinition,
    TypeStatistics,
)


class TypeStatisticsCalculator:
    """型定義の統計情報を計算するクラス"""

    def __init__(self) -> None:
        """初期化"""
        self.docstring_analyzer = DocstringAnalyzer()

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

        # primitive型使用統計
        primitive_usage_count = self._count_primitive_usage(type_definitions)
        primitive_usage_ratio = primitive_usage_count / total_count if total_count > 0 else 0.0

        # 非推奨typing使用統計
        deprecated_typing_count = self._count_deprecated_typing(type_definitions)
        deprecated_typing_ratio = deprecated_typing_count / total_count if total_count > 0 else 0.0

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
            primitive_usage_count=primitive_usage_count,
            deprecated_typing_count=deprecated_typing_count,
            primitive_usage_ratio=primitive_usage_ratio,
            deprecated_typing_ratio=deprecated_typing_ratio,
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
                by_level_avg_lines={},
                by_format={},
            ),
        )

    def _calculate_by_directory(self, type_definitions: list[TypeDefinition]) -> dict[str, dict[str, int]]:
        """ディレクトリ別の統計を計算"""
        by_directory: dict[str, dict[str, int]] = defaultdict(
            lambda: {"level1": 0, "level2": 0, "level3": 0, "other": 0}
        )

        for td in type_definitions:
            directory = str(Path(td.file_path).parent)
            by_directory[directory][td.level] += 1

        return dict(by_directory)

    def _calculate_by_category(self, type_definitions: list[TypeDefinition]) -> dict[str, int]:
        """カテゴリ別の統計を計算"""
        by_category: dict[str, int] = defaultdict(int)

        for td in type_definitions:
            by_category[td.category] += 1

        return dict(by_category)

    def _calculate_documentation_statistics(self, type_definitions: list[TypeDefinition]) -> DocumentationStatistics:
        """ドキュメント統計を計算"""
        total_types = len(type_definitions)
        documented_types = sum(1 for td in type_definitions if td.has_docstring)
        undocumented_types = total_types - documented_types

        implementation_rate = documented_types / total_types if total_types > 0 else 0.0

        # 最低限のdocstring（1-2行）と詳細なdocstring（3行以上）
        minimal_docstrings = sum(1 for td in type_definitions if td.has_docstring and 1 <= td.docstring_lines <= 2)
        detailed_docstrings = sum(1 for td in type_definitions if td.has_docstring and td.docstring_lines >= 3)

        detail_rate = detailed_docstrings / documented_types if documented_types > 0 else 0.0

        # 平均docstring行数
        total_lines = sum(td.docstring_lines for td in type_definitions)
        avg_docstring_lines = total_lines / total_types if total_types > 0 else 0.0

        # 総合品質スコア
        quality_score = implementation_rate * detail_rate

        # レベル別のdocstring統計とレベル別平均行数を計算
        by_level, by_level_avg_lines = self._calculate_documentation_by_level(type_definitions)

        # フォーマット別のdocstring数を計算
        by_format: dict[str, int] = {
            "google": 0,
            "numpy": 0,
            "restructured": 0,
            "unknown": 0,
        }
        for td in type_definitions:
            if not td.has_docstring or not td.docstring:
                continue
            detail = self.docstring_analyzer.analyze_docstring(td.docstring)
            by_format[detail.format_style] += 1

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
            by_level_avg_lines=by_level_avg_lines,
            by_format=by_format,
        )

    def _calculate_documentation_by_level(
        self, type_definitions: list[TypeDefinition]
    ) -> tuple[dict[str, dict[str, int]], dict[str, float]]:
        """レベル別のドキュメント統計を計算

        Returns:
            tuple[dict[str, dict[str, int]], dict[str, float]]:
                - by_level: レベル別のカウント値
                - by_level_avg_lines: レベル別の平均行数
        """
        by_level: dict[str, dict[str, int]] = {}
        by_level_avg_lines: dict[str, float] = {}

        for level in ["level1", "level2", "level3", "other"]:
            level_types = [td for td in type_definitions if td.level == level]
            total = len(level_types)

            if total > 0:
                documented = sum(1 for td in level_types if td.has_docstring)
                detailed = sum(1 for td in level_types if td.has_docstring and td.docstring_lines >= 3)
                total_lines = sum(td.docstring_lines for td in level_types if td.has_docstring)
                avg_lines = total_lines / documented if documented > 0 else 0.0

                by_level[level] = {
                    "total": total,
                    "documented": documented,
                    "detailed": detailed,
                }
                by_level_avg_lines[level] = avg_lines
            else:
                by_level[level] = {
                    "total": 0,
                    "documented": 0,
                    "detailed": 0,
                }
                by_level_avg_lines[level] = 0.0

        return by_level, by_level_avg_lines

    def _count_primitive_usage(self, type_definitions: list[TypeDefinition]) -> int:
        """primitive型の直接使用をカウント

        Args:
            type_definitions: 型定義のリスト

        Returns:
            primitive型を直接使用している型定義の数

        Note:
            以下は検出対象外（誤検出を避ける）:
            - BaseModel/dataclassのフィールド定義
            - Annotated内で使用されている場合
            - ジェネリック型のパラメータ（list[str]等）は許容
        """
        # チェック対象のprimitive型（小文字のみ、大文字は型変数の可能性）
        primitive_types = {
            "str",
            "int",
            "float",
            "bool",
            "bytes",
        }

        count = 0
        for td in type_definitions:
            # BaseModel/dataclassのフィールドは除外
            if td.level == "level3" or td.category in ["class", "dataclass"]:
                continue

            # Annotatedを使用している場合は除外
            if "Annotated" in td.definition or "annotated" in td.definition.lower():
                continue

            definition = td.definition

            # Level 1（type文）での直接使用を検出
            if td.level == "level1":
                # "type UserId = str" のようなパターン
                for prim in primitive_types:
                    # 右辺が単純にprimitive型のみの場合を検出
                    pattern = rf"=\s*{prim}\s*$"
                    if re.search(pattern, definition, re.IGNORECASE):
                        count += 1
                        break

        return count

    def _count_deprecated_typing(self, type_definitions: list[TypeDefinition]) -> int:
        """非推奨typing使用をカウント

        Args:
            type_definitions: 型定義のリスト

        Returns:
            非推奨typing型を使用している型定義の数

        Note:
            以下は検出対象外（誤検出を避ける）:
            - コメント内の記述
            - インポート文のみの記述
            - docstring内の記述
        """
        # 非推奨typing型（Python 3.13で非推奨）
        deprecated_types = {
            "Union",
            "Optional",
            "List",
            "Dict",
            "Set",
            "Tuple",
            "FrozenSet",
            "Deque",
            "DefaultDict",
            "OrderedDict",
            "Counter",
            "ChainMap",
            "NewType",
        }

        count = 0
        for td in type_definitions:
            # 型定義の本体をチェック
            definition = td.definition

            # コメント行、インポート行、docstring内を除外
            # 実際の型定義行のみを対象とする
            lines = definition.split("\n")
            relevant_lines = []
            in_docstring = False
            for line in lines:
                stripped = line.strip()

                # docstringの開始/終了を検出
                if '"""' in stripped or "'''" in stripped:
                    # トリプルクォートの数をカウント
                    triple_quote_count = stripped.count('"""') + stripped.count("'''")
                    if triple_quote_count % 2 == 1:
                        in_docstring = not in_docstring
                    continue

                # docstring内の行はスキップ
                if in_docstring:
                    continue

                # コメント行、空行、インポート行を除外
                if (
                    not stripped
                    or stripped.startswith("#")
                    or stripped.startswith("from ")
                    or stripped.startswith("import ")
                    or " # " in stripped  # インラインコメント内も除外
                ):
                    continue

                # インラインコメントを削除
                if "#" in line:
                    line = line[: line.index("#")]

                relevant_lines.append(line)

            relevant_definition = "\n".join(relevant_lines)

            # 非推奨typing型のパターンを検出
            for deprecated in deprecated_types:
                # 型として実際に使用されている場合のみ検出
                if deprecated == "NewType":
                    # NewTypeは特殊: "NewType('Name', type)" の形式
                    pattern = rf"\b{deprecated}\s*\("
                else:
                    # その他: "Union[str, int]" や ": Optional[str]"
                    pattern = rf"\b{deprecated}\s*\["

                if re.search(pattern, relevant_definition):
                    count += 1
                    break  # 1つでも見つかればカウント

        return count
