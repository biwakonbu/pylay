"""
型レベルアップ判定エンジン

型定義を分析し、適切なレベルへの昇格・削除を推奨します。
"""

import re

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
        """型定義を分析し、レベルアップの推奨を返す

        Args:
            type_def: 型定義
            usage_count: 使用回数（未実装の場合は0）

        Returns:
            UpgradeRecommendation（推奨事項がない場合はNone）
        """
        if type_def.level == "level1":
            return self._analyze_level1(type_def, usage_count)
        elif type_def.level == "level2":
            return self._analyze_level2(type_def, usage_count)

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
        # 削除判定
        deletion_check = self._should_delete_level1(type_def, usage_count)
        if deletion_check["should_delete"]:
            return UpgradeRecommendation(
                type_name=type_def.name,
                current_level=type_def.level,
                recommended_level="delete",
                confidence=deletion_check["confidence"],
                reasons=deletion_check["reasons"],
                suggested_validator=None,
                suggested_implementation=None,
                priority=deletion_check["priority"],
            )

        # Level 2への昇格判定
        upgrade_check = self._should_upgrade_to_level2(type_def, usage_count)
        if upgrade_check["should_upgrade"]:
            return UpgradeRecommendation(
                type_name=type_def.name,
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
    # Level 1 の判定ロジック
    # ========================================

    def _should_delete_level1(self, type_def: TypeDefinition, usage_count: int) -> dict:
        """Level 1の型定義を削除すべきか判定

        Args:
            type_def: 型定義
            usage_count: 使用回数

        Returns:
            判定結果
        """
        reasons = []
        confidence = 0.0

        # bool型のエイリアスは削除推奨
        if "bool" in type_def.definition.lower():
            reasons.append("bool型のエイリアスは不要（変数名で十分明確）")
            confidence += 0.4

        # 使用頻度が低い（1-2箇所）
        if usage_count <= 2:
            reasons.append(f"使用箇所が{usage_count}箇所のみで、共通化のメリットがない")
            confidence += 0.3

        # docstringなし
        if not type_def.has_docstring:
            reasons.append("docstringがなく、ドキュメント的価値もない")
            confidence += 0.2

        # 意味的価値がない（Code = str 等）
        if self._is_meaningless_alias(type_def):
            reasons.append("意味的価値がない型エイリアス")
            confidence += 0.3

        if confidence >= 0.5:
            priority = "high" if confidence >= 0.8 else "medium"
            return {
                "should_delete": True,
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
    ) -> dict:
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
    # Level 2 → Level 3 の判定ロジック
    # ========================================

    def _should_upgrade_to_level3(
        self, type_def: TypeDefinition, usage_count: int
    ) -> dict:
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

    def _detect_pattern_based_upgrade(self, type_def: TypeDefinition) -> dict:
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
    # ヘルパーメソッド
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

type {type_name} = Annotated[str, AfterValidator({validator_name})]'''

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

type {type_name} = Annotated[str, AfterValidator({validator_name})]'''

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

type {type_name} = Annotated[int, AfterValidator({validator_name})]'''

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

type {type_name} = Annotated[float, AfterValidator({validator_name})]'''

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
