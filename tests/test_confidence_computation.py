"""
信頼度計算機能のユニットテスト

型推論の信頼度計算における以下の要素をテストします:
- 基礎確実性（mypy診断結果）
- 型複雑度ペナルティ
- アノテーション品質ボーナス
"""

import pytest

from src.core.analyzer.type_inferrer import (
    _compute_annotation_bonus,
    _compute_base_certainty,
    _compute_complexity_penalty,
    _compute_confidence,
)


class TestBaseCertainty:
    """基礎確実性計算のテスト"""

    def test_no_error_no_warning(self):
        """エラーも警告もない場合、確実性は1.0"""
        mypy_output = "Success: no issues found in checked files"
        result = _compute_base_certainty(mypy_output, "my_var")
        assert result == 1.0

    def test_with_error(self):
        """エラーがある場合、確実性は0.3"""
        mypy_output = "error: Incompatible types for my_var"
        result = _compute_base_certainty(mypy_output, "my_var")
        assert result == 0.3

    def test_with_warning(self):
        """警告のみの場合、確実性は0.7"""
        mypy_output = "warning: Unused variable my_var"
        result = _compute_base_certainty(mypy_output, "my_var")
        assert result == 0.7

    def test_different_variable_error(self):
        """別の変数のエラーは影響しない"""
        mypy_output = "error: Incompatible types for other_var"
        result = _compute_base_certainty(mypy_output, "my_var")
        assert result == 1.0

    def test_case_insensitive(self):
        """エラー/警告の検出は大文字小文字を区別しない"""
        mypy_output = "ERROR: Issue with my_var"
        result = _compute_base_certainty(mypy_output, "my_var")
        assert result == 0.3


class TestComplexityPenalty:
    """型複雑度ペナルティのテスト"""

    def test_simple_type(self):
        """単純型はペナルティなし"""
        result = _compute_complexity_penalty("int")
        assert result == 0.0

    def test_single_union(self):
        """Union型1つはペナルティ0.15"""
        result = _compute_complexity_penalty("Union[int, str]")
        assert result == pytest.approx(0.15 + 0.1)  # Union + generic bracket

    def test_union_pipe_syntax(self):
        """パイプ構文のUnionもカウント"""
        result = _compute_complexity_penalty("int | str")
        assert result == pytest.approx(0.15)

    def test_optional(self):
        """Optional型はペナルティ0.1 + ジェネリック0.1"""
        result = _compute_complexity_penalty("Optional[int]")
        assert result == pytest.approx(0.1 + 0.1)

    def test_optional_none_syntax(self):
        """| None構文のOptionalもカウント"""
        result = _compute_complexity_penalty("int | None")
        # " | " (Union) + "| None" (Optional) = 0.15 + 0.1 = 0.25
        assert result == pytest.approx(0.25)

    def test_any_type(self):
        """Any型はペナルティ0.2"""
        result = _compute_complexity_penalty("Any")
        assert result == pytest.approx(0.2)

    def test_nested_generic(self):
        """ネストしたジェネリック型"""
        result = _compute_complexity_penalty("list[dict[str, int]]")
        # 2つの '[' でペナルティ 0.2 (list[ と dict[ のみカウント)
        assert result == pytest.approx(0.2)

    def test_complex_type(self):
        """複雑な型の組み合わせ"""
        result = _compute_complexity_penalty("Union[list[int], dict[str, Any], None]")
        # Union[1]: 0.15, brackets[3]: 0.3 (Union[, list[, dict[), Any[1]: 0.2
        # = 0.15 + 0.3 + 0.2 = 0.65
        expected = 0.65
        assert result == pytest.approx(expected)

    def test_penalty_capped_at_one(self):
        """ペナルティは1.0でキャップされる"""
        # 極端に複雑な型
        complex_type = "Union[" * 20 + "int" + "]" * 20
        result = _compute_complexity_penalty(complex_type)
        assert result == 1.0


class TestAnnotationBonus:
    """アノテーション品質ボーナスのテスト"""

    def test_zero_coverage(self):
        """カバレッジ0の場合、ボーナスは0"""
        result = _compute_annotation_bonus(0.0)
        assert result == pytest.approx(0.0)

    def test_full_coverage(self):
        """カバレッジ100%の場合、ボーナスは1.0"""
        result = _compute_annotation_bonus(1.0)
        assert result == pytest.approx(1.0)

    def test_half_coverage(self):
        """カバレッジ50%の場合、ボーナスは0.5^0.8"""
        result = _compute_annotation_bonus(0.5)
        assert result == pytest.approx(0.5**0.8)

    def test_high_coverage(self):
        """カバレッジ80%の場合"""
        result = _compute_annotation_bonus(0.8)
        assert result == pytest.approx(0.8**0.8)

    def test_nonlinear_bonus(self):
        """ボーナスは非線形（べき乗）"""
        # 0.8^0.8 > 0.6^0.8 の差は、0.8 - 0.6 の線形差より小さい
        bonus_80 = _compute_annotation_bonus(0.8)
        bonus_60 = _compute_annotation_bonus(0.6)
        linear_diff = 0.8 - 0.6
        bonus_diff = bonus_80 - bonus_60
        # 非線形性により、差が圧縮される
        assert bonus_diff < linear_diff


class TestComputeConfidence:
    """総合的な信頼度計算のテスト"""

    def test_simple_type_no_error_high_coverage(self):
        """理想的な状況: 単純型、エラーなし、高カバレッジ"""
        confidence = _compute_confidence(type_info="int", mypy_output="", var_name="x", annotation_coverage=0.8)
        # certainty=1.0, complexity=0.0, annotation=0.8^0.8
        # 0.5*1.0 + 0.3*1.0 + 0.2*(0.8^0.8) ≈ 0.96
        assert confidence >= 0.95

    def test_complex_type_with_error_low_coverage(self):
        """最悪の状況: 複雑型、エラーあり、低カバレッジ"""
        confidence = _compute_confidence(
            type_info="Union[int, str, None]",
            mypy_output="error: Issue with x",
            var_name="x",
            annotation_coverage=0.3,
        )
        # certainty=0.3, complexity≈0.4, annotation≈0.35
        # 0.5*0.3 + 0.3*(1-0.4) + 0.2*0.35 ≈ 0.40
        assert confidence < 0.5

    def test_medium_complexity_warning_medium_coverage(self):
        """中程度の状況"""
        confidence = _compute_confidence(
            type_info="Optional[str]",
            mypy_output="warning: Unused y",
            var_name="y",
            annotation_coverage=0.5,
        )
        # certainty=0.7, complexity≈0.2, annotation≈0.44
        # 0.5*0.7 + 0.3*(1-0.2) + 0.2*0.44 ≈ 0.68
        assert 0.6 < confidence < 0.8

    def test_confidence_range(self):
        """信頼度は常に0.0-1.0の範囲"""
        # 極端な値でもクリップされる
        confidence_high = _compute_confidence(type_info="int", mypy_output="", var_name="x", annotation_coverage=1.0)
        confidence_low = _compute_confidence(
            type_info="Any",
            mypy_output="error: x has issues",
            var_name="x",
            annotation_coverage=0.0,
        )
        assert 0.0 <= confidence_low <= 1.0
        assert 0.0 <= confidence_high <= 1.0

    def test_weights_sum_correctly(self):
        """重みが正しく適用されている"""
        # 重み: certainty=0.5, complexity=0.3, annotation=0.2
        # 完全な値: 1.0, 0.0, 1.0の場合
        confidence = _compute_confidence(
            type_info="str",  # complexity=0
            mypy_output="Success",  # certainty=1.0
            var_name="z",
            annotation_coverage=1.0,  # annotation=1.0
        )
        # 0.5*1.0 + 0.3*1.0 + 0.2*1.0 = 1.0
        assert confidence == pytest.approx(1.0)

    def test_generic_type_penalty(self):
        """ジェネリック型は信頼度を下げる"""
        simple_confidence = _compute_confidence(type_info="list", mypy_output="", var_name="x", annotation_coverage=0.5)
        generic_confidence = _compute_confidence(
            type_info="list[dict[str, Any]]",
            mypy_output="",
            var_name="x",
            annotation_coverage=0.5,
        )
        assert generic_confidence < simple_confidence

    def test_annotation_coverage_impact(self):
        """アノテーションカバレッジは信頼度に影響する"""
        low_cov = _compute_confidence(type_info="int", mypy_output="", var_name="x", annotation_coverage=0.2)
        high_cov = _compute_confidence(type_info="int", mypy_output="", var_name="x", annotation_coverage=0.9)
        assert high_cov > low_cov


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_empty_type_info(self):
        """空の型情報"""
        confidence = _compute_confidence(type_info="", mypy_output="", var_name="x", annotation_coverage=0.5)
        assert 0.0 <= confidence <= 1.0

    def test_empty_mypy_output(self):
        """空のmypy出力"""
        confidence = _compute_confidence(type_info="int", mypy_output="", var_name="x", annotation_coverage=0.5)
        # エラーなしとして扱われる
        assert confidence > 0.5

    def test_special_characters_in_var_name(self):
        """特殊文字を含む変数名"""
        confidence = _compute_confidence(
            type_info="int",
            mypy_output="error: _special_var$ failed",
            var_name="_special_var$",
            annotation_coverage=0.5,
        )
        assert 0.0 <= confidence <= 1.0

    def test_boundary_annotation_coverage(self):
        """カバレッジの境界値"""
        for coverage in [0.0, 0.25, 0.5, 0.75, 1.0]:
            confidence = _compute_confidence(
                type_info="int",
                mypy_output="",
                var_name="x",
                annotation_coverage=coverage,
            )
            assert 0.0 <= confidence <= 1.0
