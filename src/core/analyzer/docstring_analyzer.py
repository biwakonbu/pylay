"""
ドキュメント解析エンジン

docstringの詳細度を分析し、改善推奨を生成します。
"""

import re
from typing import Literal

from src.core.analyzer.type_level_models import (
    DocstringDetail,
    DocstringRecommendation,
    TypeDefinition,
)


class DocstringAnalyzer:
    """ドキュメント解析エンジン"""

    def analyze_docstring(self, docstring: str | None) -> DocstringDetail:
        """docstringを解析して詳細情報を抽出

        Args:
            docstring: docstring文字列

        Returns:
            DocstringDetail
        """
        if docstring is None or not docstring.strip():
            return DocstringDetail(
                has_summary=False,
                has_description=False,
                has_attributes=False,
                has_args=False,
                has_returns=False,
                has_examples=False,
                format_style="unknown",
                line_count=0,
                detail_score=0.0,
            )

        # フォーマット検出
        format_style = self._detect_format(docstring)

        # セクション検出
        has_summary = self._has_summary(docstring)
        has_description = self._has_description(docstring)
        has_attributes = self._has_section(docstring, "Attributes")
        has_args = self._has_section(docstring, "Args")
        has_returns = self._has_section(docstring, "Returns")
        has_examples = self._has_section(docstring, "Examples")

        # 詳細度スコア計算
        detail_score = self._calculate_detail_score(
            has_summary,
            has_description,
            has_attributes,
            has_args,
            has_returns,
            has_examples,
        )

        return DocstringDetail(
            has_summary=has_summary,
            has_description=has_description,
            has_attributes=has_attributes,
            has_args=has_args,
            has_returns=has_returns,
            has_examples=has_examples,
            format_style=format_style,
            line_count=len(docstring.splitlines()),
            detail_score=detail_score,
        )

    def recommend_docstring_improvements(
        self, type_def: TypeDefinition, detail: DocstringDetail
    ) -> DocstringRecommendation:
        """docstring改善推奨を生成

        Args:
            type_def: 型定義
            detail: docstring詳細情報

        Returns:
            DocstringRecommendation
        """
        # 現状判定
        if type_def.docstring is None:
            current_status = "missing"
            recommended_action = "add"
            priority = "high" if type_def.level in ["level2", "level3"] else "medium"
            reasons = ["docstringが存在しません"]
            detail_gaps = ["summary", "description"]
        elif detail.line_count == 1:
            current_status = "minimal"
            recommended_action = "expand"
            priority = "medium"
            reasons = ["最低限のdocstringしかありません"]
            detail_gaps = []
            if not detail.has_description:
                detail_gaps.append("description")
            if not detail.has_attributes and type_def.level == "level3":
                detail_gaps.append("Attributes")
        elif detail.detail_score < 0.5:
            current_status = "partial"
            recommended_action = "expand"
            priority = "low"
            reasons = [
                f"docstringの詳細度が不足しています（スコア: {detail.detail_score:.2f}）"
            ]
            detail_gaps = []
            if not detail.has_attributes and type_def.level == "level3":
                detail_gaps.append("Attributes")
            if not detail.has_examples:
                detail_gaps.append("Examples")
        else:
            current_status = "complete"
            recommended_action = "none"
            priority = "low"
            reasons = []
            detail_gaps = []

        # テンプレート生成
        suggested_template = None
        if recommended_action in ["add", "expand"]:
            suggested_template = self.generate_docstring_template(type_def)

        return DocstringRecommendation(
            type_name=type_def.name,
            file_path=type_def.file_path,
            line_number=type_def.line_number,
            current_status=current_status,
            recommended_action=recommended_action,
            priority=priority,
            reasons=reasons,
            suggested_template=suggested_template,
            detail_gaps=detail_gaps,
        )

    def generate_docstring_template(
        self,
        type_def: TypeDefinition,
        format_style: Literal["google", "numpy", "restructured"] = "google",
    ) -> str:
        """型定義に応じたdocstringテンプレートを生成

        Args:
            type_def: 型定義
            format_style: フォーマットスタイル

        Returns:
            docstringテンプレート
        """
        if type_def.level == "level1":
            # type エイリアスの場合
            return f'"""{type_def.name}型の説明をここに記述"""'

        elif type_def.level == "level2":
            # Annotated型の場合
            return f'''"""{type_def.name}型の説明をここに記述

この型は制約付きで、以下のバリデーションが適用されます。
"""'''

        elif type_def.level == "level3" or type_def.category == "basemodel":
            # BaseModelの場合
            if format_style == "google":
                return f'''"""
{type_def.name}の説明をここに記述

Attributes:
    field1 (type): フィールド1の説明
    field2 (type): フィールド2の説明

Examples:
    >>> obj = {type_def.name}(field1=value1, field2=value2)
    >>> print(obj)
"""'''
            elif format_style == "numpy":
                return f'''"""
{type_def.name}の説明をここに記述

Attributes
----------
field1 : type
    フィールド1の説明
field2 : type
    フィールド2の説明

Examples
--------
>>> obj = {type_def.name}(field1=value1, field2=value2)
>>> print(obj)
"""'''

        return f'"""{type_def.name}の説明をここに記述"""'

    # ========================================
    # ヘルパーメソッド
    # ========================================

    def _detect_format(
        self, docstring: str
    ) -> Literal["google", "numpy", "restructured", "unknown"]:
        """docstringフォーマットを検出

        Args:
            docstring: docstring文字列

        Returns:
            フォーマットスタイル
        """
        # Google形式: "Args:", "Returns:", "Attributes:"
        google_markers = ["Args:", "Returns:", "Attributes:", "Examples:"]
        if any(marker in docstring for marker in google_markers):
            return "google"

        # NumPy形式: "Parameters\n----------", "Returns\n-------"
        numpy_pattern = re.compile(
            r"(Parameters|Returns|Attributes|Examples)\n\s*-{3,}"
        )
        if numpy_pattern.search(docstring):
            return "numpy"

        # reStructuredText形式: ":param", ":returns:", ":rtype:"
        rst_markers = [":param", ":returns:", ":rtype:", ":type:"]
        if any(marker in docstring for marker in rst_markers):
            return "restructured"

        return "unknown"

    def _has_summary(self, docstring: str) -> bool:
        """概要行が存在するか

        Args:
            docstring: docstring文字列

        Returns:
            概要行が存在する場合True
        """
        lines = docstring.strip().splitlines()
        return len(lines) > 0 and len(lines[0].strip()) > 0

    def _has_description(self, docstring: str) -> bool:
        """詳細説明が存在するか（2行以上）

        Args:
            docstring: docstring文字列

        Returns:
            詳細説明が存在する場合True
        """
        lines = docstring.strip().splitlines()
        # 概要行 + 空行 + 詳細説明で最低3行
        return len(lines) > 2

    def _has_section(self, docstring: str, section: str) -> bool:
        """特定のセクションが存在するか

        Args:
            docstring: docstring文字列
            section: セクション名

        Returns:
            セクションが存在する場合True
        """
        # Google形式: "Args:", "Returns:", "Attributes:"
        if f"{section}:" in docstring:
            return True

        # NumPy形式: "Parameters", "Returns", "Attributes"
        numpy_pattern = re.compile(rf"{section}\n\s*-{{3,}}")
        if numpy_pattern.search(docstring):
            return True

        # reStructuredText形式: ":param", ":returns:", etc.
        rst_mapping = {
            "Args": ":param",
            "Returns": ":returns:",
            "Attributes": ":ivar",
        }
        if section in rst_mapping and rst_mapping[section] in docstring:
            return True

        return False

    def _calculate_detail_score(
        self,
        has_summary: bool,
        has_description: bool,
        has_attributes: bool,
        has_args: bool,
        has_returns: bool,
        has_examples: bool,
    ) -> float:
        """詳細度スコアを計算（0.0-1.0）

        Args:
            has_summary: 概要が存在するか
            has_description: 詳細説明が存在するか
            has_attributes: Attributesセクションが存在するか
            has_args: Argsセクションが存在するか
            has_returns: Returnsセクションが存在するか
            has_examples: Examplesセクションが存在するか

        Returns:
            詳細度スコア
        """
        score = 0.0
        weights = {
            "summary": 0.2,  # 概要（必須）
            "description": 0.2,  # 詳細説明
            "attributes": 0.2,  # Attributes（BaseModelの場合）
            "args": 0.15,  # Args（関数の場合）
            "returns": 0.15,  # Returns（関数の場合）
            "examples": 0.1,  # Examples
        }

        if has_summary:
            score += weights["summary"]
        if has_description:
            score += weights["description"]
        if has_attributes:
            score += weights["attributes"]
        if has_args:
            score += weights["args"]
        if has_returns:
            score += weights["returns"]
        if has_examples:
            score += weights["examples"]

        return score
