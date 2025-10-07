"""
型レベルアップ判定エンジン

型定義を分析し、適切なレベルへの昇格・削除を推奨します。
"""

import re
from typing import Any

from src.core.analyzer.type_level_models import TypeDefinition, UpgradeRecommendation


class TypeUpgradeAnalyzer:
    """型レベルアップ判定エンジン"""

    # パターンベースの判定ルール
    PATH_PATTERNS = [r".*Path$", r".*Dir$", r".*Directory$"]
    NAME_PATTERNS = [
        r".*Name$",
        r".*ClassName$",
        r".*FunctionName$",
        r".*ModuleName$",
        r".*VariableName$",
    ]
    COUNT_PATTERNS = [r".*Count$", r".*Index$", r".*Size$", r".*Length$"]
    SCORE_PATTERNS = [
        r".*Weight$",
        r".*Score$",
        r".*Ratio$",
        r".*Percentage$",
        r".*Rate$",
    ]

    def analyze(
        self, type_def: TypeDefinition, usage_count: int = 0
    ) -> UpgradeRecommendation | None:
        """型定義を分析し、レベルアップ・ダウンの推奨を返す

        Args:
            type_def: 型定義
            usage_count: 使用回数（未実装の場合は0）

        Returns:
            UpgradeRecommendation（推奨事項がない場合はNone）
        """
        # docstringで@keep-as-isが指定されている場合はスキップ
        if type_def.keep_as_is:
            return None

        # docstringで目標レベルが指定されている場合は、そのレベルへの推奨
        if type_def.target_level and type_def.target_level != type_def.level:
            return self._create_target_level_recommendation(type_def)

        # 通常の分析
        if type_def.level == "level1":
            return self._analyze_level1(type_def, usage_count)
        elif type_def.level == "level2":
            result = self._analyze_level2(type_def, usage_count)
            if result:
                return result
            # Level 2からLevel 1へのダウングレード判定
            return self._analyze_level2_downgrade(type_def, usage_count)
        elif type_def.level == "level3":
            # Level 3からLevel 2へのダウングレード判定
            return self._analyze_level3_downgrade(type_def, usage_count)

        return None

    def _analyze_level1(
        self, type_def: TypeDefinition, usage_count: int
    ) -> UpgradeRecommendation | None:
        """Level 1の型定義を分析

        Args:
            type_def: 型定義
            usage_count: 使用回数

        Returns:
            UpgradeRecommendation（推奨事項がない場合はNone）
        """
        # 調査推奨判定（被参照0等）
        investigation_check = self._should_delete_level1(type_def, usage_count)
        if investigation_check["confidence"] >= 0.3:
            return UpgradeRecommendation(
                type_name=type_def.name,
                file_path=type_def.file_path,
                line_number=type_def.line_number,
                current_level=type_def.level,
                recommended_level="investigate",
                confidence=investigation_check["confidence"],
                reasons=investigation_check["reasons"],
                suggested_validator=None,
                suggested_implementation=None,
                priority=investigation_check["priority"],
            )

        # Level 2への昇格判定
        upgrade_check = self._should_upgrade_to_level2(type_def, usage_count)
        if upgrade_check["should_upgrade"]:
            return UpgradeRecommendation(
                type_name=type_def.name,
                file_path=type_def.file_path,
                line_number=type_def.line_number,
                current_level=type_def.level,
                recommended_level="level2",
                confidence=upgrade_check["confidence"],
                reasons=upgrade_check["reasons"],
                suggested_validator=upgrade_check.get("validator"),
                suggested_implementation=None,
                priority=upgrade_check["priority"],
            )

        return None

    def _analyze_level2(
        self, type_def: TypeDefinition, usage_count: int
    ) -> UpgradeRecommendation | None:
        """Level 2の型定義を分析

        Args:
            type_def: 型定義
            usage_count: 使用回数

        Returns:
            UpgradeRecommendation（推奨事項がない場合はNone）
        """
        # Level 3への昇格判定
        upgrade_check = self._should_upgrade_to_level3(type_def, usage_count)
        if upgrade_check["should_upgrade"]:
            return UpgradeRecommendation(
                type_name=type_def.name,
                file_path=type_def.file_path,
                line_number=type_def.line_number,
                current_level=type_def.level,
                recommended_level="level3",
                confidence=upgrade_check["confidence"],
                reasons=upgrade_check["reasons"],
                suggested_validator=None,
                suggested_implementation=upgrade_check.get("implementation"),
                priority=upgrade_check["priority"],
            )

        return None

    # ========================================
    # docstringベースの制御
    # ========================================

    def _create_target_level_recommendation(
        self, type_def: TypeDefinition
    ) -> UpgradeRecommendation:
        """docstringで指定された目標レベルへの推奨を生成

        Args:
            type_def: 型定義

        Returns:
            UpgradeRecommendation
        """
        target = type_def.target_level
        if target is None:
            # target_levelがNoneの場合は調査推奨
            return UpgradeRecommendation(
                type_name=type_def.name,
                file_path=type_def.file_path,
                line_number=type_def.line_number,
                current_level=type_def.level,
                recommended_level="investigate",
                confidence=0.5,
                reasons=["target_levelが指定されていません"],
                suggested_validator=None,
                suggested_implementation=None,
                priority="low",
                is_downgrade=False,
            )

        current = type_def.level
        is_downgrade = self._is_downgrade(current, target)

        reasons = [
            f"docstringで @target-level: {target} が指定されています",
            f"現在のレベル {current} から {target} への移行を推奨します",
        ]

        if is_downgrade:
            reasons.append("レベルダウン: 過剰な実装の可能性があります")
        else:
            reasons.append("レベルアップ: より厳密な型定義が推奨されています")

        return UpgradeRecommendation(
            type_name=type_def.name,
            file_path=type_def.file_path,
            line_number=type_def.line_number,
            current_level=current,
            recommended_level=target,
            confidence=1.0,  # docstring指定は確信度最大
            reasons=reasons,
            suggested_validator=None,
            suggested_implementation=None,
            priority="high",
            is_downgrade=is_downgrade,
        )

    def _is_downgrade(self, current: str, target: str) -> bool:
        """レベルダウンかどうかを判定

        Args:
            current: 現在のレベル
            target: 目標レベル

        Returns:
            レベルダウンの場合True
        """
        level_order = {"level1": 1, "level2": 2, "level3": 3}
        return level_order.get(current, 0) > level_order.get(target, 0)

    # ========================================
    # Level 1 の判定ロジック
    # ========================================

    def _should_delete_level1(
        self, type_def: TypeDefinition, usage_count: int
    ) -> dict[str, Any]:
        """Level 1の型定義を調査すべきか判定

        このプロジェクトでは個別型の定義を推奨しているため、
        被参照0の型は「削除」ではなく「調査」対象とする。

        Args:
            type_def: 型定義
            usage_count: 使用回数

        Returns:
            判定結果
        """
        reasons = []
        confidence = 0.0

        # 被参照0の型は調査対象（削除ではない）
        if usage_count == 0:
            reasons.append(
                "定義されているが使用されていません。以下を確認してください："
            )
            reasons.append("  1. 実装途中か？")
            reasons.append("  2. 既存のprimitive型使用箇所を置き換えるべきか？")
            reasons.append("  3. 設計意図（将来の拡張性等）を確認")
            confidence += 0.3

            if not type_def.has_docstring:
                reasons.append("  4. docstringを追加して設計意図を明確にする")
                confidence += 0.2

        # docstringなしの型は要調査
        if usage_count > 0 and not type_def.has_docstring:
            reasons.append("docstringがないため、型の意図が不明確です")
            confidence += 0.2

        # 判定結果は「調査」であり「削除」ではない
        if confidence >= 0.3:
            priority = "medium" if usage_count == 0 else "low"
            return {
                "should_delete": False,  # 削除推奨しない
                "confidence": min(confidence, 1.0),
                "reasons": reasons,
                "priority": priority,
            }

        return {
            "should_delete": False,
            "confidence": 0.0,
            "reasons": [],
            "priority": "low",
        }

    def _should_upgrade_to_level2(
        self, type_def: TypeDefinition, usage_count: int
    ) -> dict[str, Any]:
        """Level 1からLevel 2への昇格判定

        Args:
            type_def: 型定義
            usage_count: 使用回数

        Returns:
            判定結果
        """
        reasons = []
        confidence = 0.0
        suggested_validator = None

        # パターンベースの判定
        pattern_result = self._detect_pattern_based_upgrade(type_def)
        if pattern_result["matched"]:
            reasons.extend(pattern_result["reasons"])
            confidence += pattern_result["confidence"]
            suggested_validator = pattern_result.get("validator")

        # 使用状況ベースの判定
        if usage_count >= 3:
            reasons.append(f"{usage_count}箇所で使用されており、制約を明確にすべき")
            confidence += 0.3

        # docstringがない場合は優先度を下げる
        if not type_def.has_docstring:
            reasons.append("docstringが存在しないため、まずドキュメントを追加すべき")
            confidence *= 0.8

        if confidence >= 0.5:
            priority = "high" if confidence >= 0.8 else "medium"
            return {
                "should_upgrade": True,
                "confidence": min(confidence, 1.0),
                "reasons": reasons,
                "validator": suggested_validator,
                "priority": priority,
            }

        return {
            "should_upgrade": False,
            "confidence": 0.0,
            "reasons": [],
            "priority": "low",
        }

    # ========================================
    # Level 2 → Level 1 ダウングレード判定
    # ========================================

    def _analyze_level2_downgrade(
        self, type_def: TypeDefinition, usage_count: int
    ) -> UpgradeRecommendation | None:
        """Level 2からLevel 1へのダウングレード判定

        Args:
            type_def: 型定義
            usage_count: 使用回数

        Returns:
            UpgradeRecommendation（推奨事項がない場合はNone）
        """
        reasons = []
        confidence = 0.0

        # バリデータが実質的に何もしていない（パススルーのみ）
        if self._is_passthrough_validator(type_def):
            reasons.append("バリデータが実質的に何も検証していません")
            reasons.append("Level 1のtype文で十分です")
            confidence += 0.7

        # 使用回数が極めて少ない（1箇所以下）で、複雑なバリデータもない
        if usage_count <= 1 and not self._has_complex_validator(type_def):
            reasons.append("使用箇所が少なく、バリデーション不要の可能性があります")
            confidence += 0.3

        if confidence >= 0.5:
            priority = "medium" if confidence >= 0.7 else "low"
            return UpgradeRecommendation(
                type_name=type_def.name,
                file_path=type_def.file_path,
                line_number=type_def.line_number,
                current_level=type_def.level,
                recommended_level="level1",
                confidence=min(confidence, 1.0),
                reasons=reasons,
                suggested_validator=None,
                suggested_implementation=None,
                priority=priority,
                is_downgrade=True,
            )

        return None

    # ========================================
    # Level 3 → Level 2 ダウングレード判定
    # ========================================

    def _analyze_level3_downgrade(
        self, type_def: TypeDefinition, usage_count: int
    ) -> UpgradeRecommendation | None:
        """Level 3からLevel 2へのダウングレード判定

        Args:
            type_def: 型定義
            usage_count: 使用回数

        Returns:
            UpgradeRecommendation（推奨事項がない場合はNone）
        """
        reasons = []
        confidence = 0.0

        # 単一フィールドのみで、ビジネスロジックメソッドがない
        if self._is_single_field_basemodel(type_def):
            reasons.append("単一フィールドのみのBaseModelです")
            reasons.append("Annotated + AfterValidator（Level 2）で十分です")
            confidence += 0.6

        # メソッドが__str__, __hash__のみ（Value Object的だがシンプル）
        if self._has_only_utility_methods(type_def):
            reasons.append("ビジネスロジックメソッドが存在しません")
            reasons.append("Level 2への簡素化を検討してください")
            confidence += 0.4

        if confidence >= 0.5:
            priority = "medium" if confidence >= 0.7 else "low"
            return UpgradeRecommendation(
                type_name=type_def.name,
                file_path=type_def.file_path,
                line_number=type_def.line_number,
                current_level=type_def.level,
                recommended_level="level2",
                confidence=min(confidence, 1.0),
                reasons=reasons,
                suggested_validator=None,
                suggested_implementation=None,
                priority=priority,
                is_downgrade=True,
            )

        return None

    # ========================================
    # Level 2 → Level 3 の判定ロジック
    # ========================================

    def _should_upgrade_to_level3(
        self, type_def: TypeDefinition, usage_count: int
    ) -> dict[str, Any]:
        """Level 2からLevel 3への昇格判定

        Args:
            type_def: 型定義
            usage_count: 使用回数

        Returns:
            判定結果
        """
        reasons = []
        confidence = 0.0

        # バリデータの複雑度チェック（10行以上）
        validator_complexity = self._estimate_validator_complexity(type_def)
        if validator_complexity >= 10:
            reasons.append(
                f"バリデータが{validator_complexity}行と複雑で、BaseModelにカプセル化すべき"
            )
            confidence += 0.5

        # 関連する操作が複数存在する（仮定：3つ以上）
        # 実際の実装では、型に対する関数の存在を検出する必要がある
        # ここでは簡略化

        if confidence >= 0.5:
            priority = "high" if confidence >= 0.8 else "medium"
            suggested_implementation = self._generate_basemodel_implementation(type_def)
            return {
                "should_upgrade": True,
                "confidence": min(confidence, 1.0),
                "reasons": reasons,
                "implementation": suggested_implementation,
                "priority": priority,
            }

        return {
            "should_upgrade": False,
            "confidence": 0.0,
            "reasons": [],
            "priority": "low",
        }

    # ========================================
    # パターンベースの判定
    # ========================================

    def _detect_pattern_based_upgrade(self, type_def: TypeDefinition) -> dict[str, Any]:
        """パターンベースの判定

        Args:
            type_def: 型定義

        Returns:
            判定結果
        """
        reasons = []
        confidence = 0.0
        suggested_validator = None

        # パス系の型
        if any(re.match(p, type_def.name) for p in self.PATH_PATTERNS):
            reasons.append("パス系の型は存在チェックと禁止文字チェックが必要")
            confidence += 0.6
            suggested_validator = self._generate_path_validator(type_def.name)

        # 識別子系の型
        elif any(re.match(p, type_def.name) for p in self.NAME_PATTERNS):
            reasons.append("識別子系の型はPython命名規則への準拠が必要")
            confidence += 0.5
            suggested_validator = self._generate_name_validator(type_def.name)

        # 数値範囲系の型
        elif any(re.match(p, type_def.name) for p in self.COUNT_PATTERNS):
            reasons.append("数値範囲系の型は負数や範囲外の値を防ぐ必要がある")
            confidence += 0.5
            suggested_validator = self._generate_count_validator(type_def.name)

        # 重み・スコア系の型
        elif any(re.match(p, type_def.name) for p in self.SCORE_PATTERNS):
            reasons.append("重み・スコア系の型は0.0-1.0の範囲制限が必要")
            confidence += 0.5
            suggested_validator = self._generate_score_validator(type_def.name)

        if reasons:
            return {
                "matched": True,
                "reasons": reasons,
                "confidence": confidence,
                "validator": suggested_validator,
            }

        return {"matched": False, "reasons": [], "confidence": 0.0}

    # ========================================
    # ヘルパーメソッド（ダウングレード判定用）
    # ========================================

    def _is_passthrough_validator(self, type_def: TypeDefinition) -> bool:
        """バリデータがパススルー（何もしていない）か判定

        Args:
            type_def: 型定義

        Returns:
            パススルーの場合True
        """
        # "return v" のみで構成されているバリデータ
        definition = type_def.definition
        # 簡易判定: "return v" があり、raise/if文がない
        has_return_v = "return v" in definition
        has_validation = "raise" in definition or "if " in definition
        return has_return_v and not has_validation

    def _has_complex_validator(self, type_def: TypeDefinition) -> bool:
        """複雑なバリデータを持つか判定

        Args:
            type_def: 型定義

        Returns:
            複雑なバリデータの場合True
        """
        # バリデータ関数の行数が5行以上
        return self._estimate_validator_complexity(type_def) >= 5

    def _is_single_field_basemodel(self, type_def: TypeDefinition) -> bool:
        """単一フィールドのみのBaseModelか判定

        Args:
            type_def: 型定義

        Returns:
            単一フィールドのみの場合True
        """
        # 簡易判定: フィールド定義が1つだけ
        # "value: str" のようなパターンをカウント
        field_pattern = r"^\s+\w+:\s+"
        field_count = len(re.findall(field_pattern, type_def.definition, re.MULTILINE))
        return field_count == 1

    def _has_only_utility_methods(self, type_def: TypeDefinition) -> bool:
        """ユーティリティメソッド（__str__, __hash__等）のみか判定

        Args:
            type_def: 型定義

        Returns:
            ユーティリティメソッドのみの場合True
        """
        # 簡易判定: def が存在し、すべてが__で始まるメソッド
        method_pattern = r"def\s+(\w+)\("
        methods = re.findall(method_pattern, type_def.definition)
        if not methods:
            return False
        # すべてのメソッドが__で始まる（ダンダーメソッド）
        return all(m.startswith("__") for m in methods)

    # ========================================
    # ヘルパーメソッド（その他）
    # ========================================

    def _is_meaningless_alias(self, type_def: TypeDefinition) -> bool:
        """意味的価値がない型エイリアスか判定

        Args:
            type_def: 型定義

        Returns:
            意味的価値がない場合True
        """
        # Code = str, Message = str 等の単純なエイリアス
        meaningless_patterns = [
            r"type\s+Code\s*=\s*str",
            r"type\s+Message\s*=\s*str",
            r"type\s+Text\s*=\s*str",
            r"type\s+Value\s*=\s*str",
        ]

        return any(re.match(p, type_def.definition) for p in meaningless_patterns)

    def _estimate_validator_complexity(self, type_def: TypeDefinition) -> int:
        """バリデータの複雑度を推定（行数）

        Args:
            type_def: 型定義

        Returns:
            推定行数
        """
        # 定義の行数をカウント
        return len(type_def.definition.splitlines())

    # ========================================
    # バリデータコード生成
    # ========================================

    def _generate_path_validator(self, type_name: str) -> str:
        """パス系のバリデータコードを生成

        Args:
            type_name: 型名

        Returns:
            バリデータコード
        """
        validator_name = f"validate_{type_name.lower()}"
        return f'''def {validator_name}(v: str) -> str:
    """パスの妥当性をバリデーション"""
    if "\\0" in v:
        raise ValueError("無効な文字が含まれています")
    if len(v) > 4096:
        raise ValueError("パスが長すぎます")
    return v

{type_name} = NewType(
    '{type_name}', Annotated[str, AfterValidator({validator_name})]
)'''

    def _generate_name_validator(self, type_name: str) -> str:
        """識別子系のバリデータコードを生成

        Args:
            type_name: 型名

        Returns:
            バリデータコード
        """
        validator_name = f"validate_{type_name.lower()}"
        return f'''def {validator_name}(v: str) -> str:
    """識別子の妥当性をバリデーション"""
    if not v.isidentifier():
        raise ValueError("無効な識別子です")
    return v

{type_name} = NewType(
    '{type_name}', Annotated[str, AfterValidator({validator_name})]
)'''

    def _generate_count_validator(self, type_name: str) -> str:
        """数値範囲系のバリデータコードを生成

        Args:
            type_name: 型名

        Returns:
            バリデータコード
        """
        validator_name = f"validate_{type_name.lower()}"
        return f'''def {validator_name}(v: int) -> int:
    """数値範囲のバリデーション"""
    if v < 0:
        raise ValueError("負の値は許可されていません")
    return v

{type_name} = NewType(
    '{type_name}', Annotated[int, AfterValidator({validator_name})]
)'''

    def _generate_score_validator(self, type_name: str) -> str:
        """重み・スコア系のバリデータコードを生成

        Args:
            type_name: 型名

        Returns:
            バリデータコード
        """
        validator_name = f"validate_{type_name.lower()}"
        return f'''def {validator_name}(v: float) -> float:
    """スコア範囲のバリデーション（0.0-1.0）"""
    if not 0.0 <= v <= 1.0:
        raise ValueError("スコアは0.0-1.0の範囲である必要があります")
    return v

{type_name} = NewType(
    '{type_name}', Annotated[float, AfterValidator({validator_name})]
)'''

    def _generate_basemodel_implementation(self, type_def: TypeDefinition) -> str:
        """BaseModel実装コードを生成

        Args:
            type_def: 型定義

        Returns:
            BaseModel実装コード
        """
        return f'''class {type_def.name}(BaseModel):
    """
    {type_def.name}の説明をここに記述

    Attributes:
        value: 値
    """

    value: str  # 適切な型に置き換えてください

    @field_validator("value")
    def validate_value(cls, v: str) -> str:
        """値のバリデーション"""
        # バリデーションロジックをここに記述
        return v'''
