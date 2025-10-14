"""
型定義レベル分析のメインアナライザ

すべての分析機能を統合し、型定義レベルとドキュメント品質の分析を実行します。
"""

import ast
from pathlib import Path

from src.core.analyzer.docstring_analyzer import DocstringAnalyzer
from src.core.analyzer.type_classifier import TypeClassifier
from src.core.analyzer.type_level_models import (
    DocstringRecommendation,
    TypeAnalysisReport,
    TypeDefinition,
    TypeStatistics,
    UpgradeRecommendation,
)
from src.core.analyzer.type_reporter import TypeReporter
from src.core.analyzer.type_statistics import TypeStatisticsCalculator
from src.core.analyzer.type_upgrade_analyzer import TypeUpgradeAnalyzer
from src.core.utils.io_helpers import collect_python_files


class TypeLevelAnalyzer:
    """型定義レベル分析のメインアナライザ"""

    def __init__(self, threshold_ratios: dict[str, float] | None = None):
        """初期化

        Args:
            threshold_ratios: 警告閾値（デフォルト: 推奨閾値）
                - level1_max: Level 1の上限（これを超えたら警告）
                - level2_min: Level 2の下限（これを下回ったら警告）
                - level3_min: Level 3の下限（これを下回ったら警告）
        """
        self.classifier = TypeClassifier()
        self.statistics_calculator = TypeStatisticsCalculator()
        self.docstring_analyzer = DocstringAnalyzer()
        self.upgrade_analyzer = TypeUpgradeAnalyzer()
        self.reporter = TypeReporter(threshold_ratios)

        self.threshold_ratios = threshold_ratios or {
            "level1_max": 0.20,  # Level 1は20%以下が望ましい
            "level2_min": 0.40,  # Level 2は40%以上が望ましい
            "level3_min": 0.15,  # Level 3は15%以上が望ましい
        }

    def analyze_directory(
        self,
        directory: Path,
        *,
        include_upgrade_recommendations: bool = True,
        exclude_patterns: list[str] | None = None,
    ) -> TypeAnalysisReport:
        """ディレクトリ内の型定義を分析

        Args:
            directory: 解析対象のディレクトリ
            include_upgrade_recommendations: 型レベルアップ推奨を含めるか
            exclude_patterns: 除外するパターン（glob形式）

        Returns:
            TypeAnalysisReport
        """
        # Pythonファイルを収集（共通ヘルパー関数を使用）
        py_files = collect_python_files(directory, exclude_patterns)

        # 型定義を収集
        all_type_definitions: list[TypeDefinition] = []
        for py_file in py_files:
            type_defs = self.classifier.classify_file(py_file)
            all_type_definitions.extend(type_defs)

        # 重複を除去（同じファイル・型名・行番号の組み合わせで重複判定）
        unique_type_definitions = self._deduplicate_type_definitions(all_type_definitions)

        # 統計情報を計算
        statistics = self.statistics_calculator.calculate(unique_type_definitions)

        # ドキュメント推奨を生成
        # 注: unique_type_definitionsを使用して、同一型の重複推奨を防ぐ
        # ユーザーに表示する推奨事項は重複除去後のデータを使用する
        docstring_recommendations = self._generate_docstring_recommendations(unique_type_definitions)

        # 型レベルアップ推奨を生成
        # 注: all_type_definitionsを使用して、型の使用回数を正確にカウント
        # 使用回数のカウントには全ての定義が必要（重複を含む）
        upgrade_recommendations: list[UpgradeRecommendation] = []
        if include_upgrade_recommendations:
            upgrade_recommendations = self._generate_upgrade_recommendations(all_type_definitions)
            # 重複除去
            upgrade_recommendations = self._deduplicate_upgrade_recommendations(upgrade_recommendations)

        # 一般的な推奨事項を生成
        recommendations = self._generate_general_recommendations(statistics)

        # 警告閾値との乖離を計算
        deviation_from_threshold = self._calculate_deviation(statistics)

        return TypeAnalysisReport(
            statistics=statistics,
            type_definitions=unique_type_definitions,
            recommendations=recommendations,
            upgrade_recommendations=upgrade_recommendations,
            docstring_recommendations=docstring_recommendations,
            threshold_ratios=self.threshold_ratios,
            deviation_from_threshold=deviation_from_threshold,
        )

    def analyze_file(self, file_path: Path) -> TypeAnalysisReport:
        """単一ファイルの型定義を分析

        Args:
            file_path: 解析対象のファイルパス

        Returns:
            TypeAnalysisReport
        """
        # 型定義を収集
        type_definitions = self.classifier.classify_file(file_path)

        # 統計情報を計算
        statistics = self.statistics_calculator.calculate(type_definitions)

        # ドキュメント推奨を生成
        docstring_recommendations = self._generate_docstring_recommendations(type_definitions)

        # 型レベルアップ推奨を生成
        upgrade_recommendations = self._generate_upgrade_recommendations(type_definitions)

        # 一般的な推奨事項を生成
        recommendations = self._generate_general_recommendations(statistics)

        # 警告閾値との乖離を計算
        deviation_from_threshold = self._calculate_deviation(statistics)

        return TypeAnalysisReport(
            statistics=statistics,
            type_definitions=type_definitions,
            recommendations=recommendations,
            upgrade_recommendations=upgrade_recommendations,
            docstring_recommendations=docstring_recommendations,
            threshold_ratios=self.threshold_ratios,
            deviation_from_threshold=deviation_from_threshold,
        )

    def _generate_docstring_recommendations(
        self, type_definitions: list[TypeDefinition]
    ) -> list[DocstringRecommendation]:
        """docstring改善推奨を生成

        Args:
            type_definitions: 型定義リスト

        Returns:
            DocstringRecommendationのリスト
        """
        recommendations: list[DocstringRecommendation] = []

        for type_def in type_definitions:
            # docstringを解析
            detail = self.docstring_analyzer.analyze_docstring(type_def.docstring)

            # 推奨事項を生成
            rec = self.docstring_analyzer.recommend_docstring_improvements(type_def, detail)

            # "none"以外の推奨事項を追加
            if rec.recommended_action != "none":
                recommendations.append(rec)

        # 優先度順にソート
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda r: priority_order.get(r.priority, 3))

        return recommendations

    def _generate_upgrade_recommendations(self, type_definitions: list[TypeDefinition]) -> list[UpgradeRecommendation]:
        """型レベルアップ推奨を生成

        Args:
            type_definitions: 型定義リスト

        Returns:
            UpgradeRecommendationのリスト
        """
        recommendations: list[UpgradeRecommendation] = []

        # 使用回数をカウント
        usage_counts = self._count_type_usage(type_definitions)

        for type_def in type_definitions:
            # 使用回数を取得
            usage_count = usage_counts.get(type_def.name, 0)
            rec = self.upgrade_analyzer.analyze(type_def, usage_count=usage_count)

            if rec:
                recommendations.append(rec)

        # 優先度と確信度順にソート
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda r: (priority_order.get(r.priority, 3), -r.confidence))

        return recommendations

    def _generate_general_recommendations(self, statistics: TypeStatistics) -> list[str]:
        """一般的な推奨事項を生成

        Args:
            statistics: 統計情報

        Returns:
            推奨事項のリスト
        """
        recommendations = []

        # Level 1の比率が高すぎる場合（上限を超えている）
        level1_max = self.threshold_ratios["level1_max"]
        if statistics.level1_ratio > level1_max:
            recommendations.append(
                f"⚠️ Level 1（type エイリアス）の比率が"
                f"{statistics.level1_ratio * 100:.1f}%と高すぎます。"
                f"推奨上限の{level1_max * 100:.0f}%を超えています。"
                f"制約が必要な型はLevel 2に昇格させ、不要な型は削除を検討してください。"
            )

        # Level 2の比率が低すぎる場合（下限を下回っている）
        level2_min = self.threshold_ratios["level2_min"]
        if statistics.level2_ratio < level2_min:
            recommendations.append(
                f"⚠️ Level 2（Annotated）の比率が"
                f"{statistics.level2_ratio * 100:.1f}%と低すぎます。"
                f"推奨下限の{level2_min * 100:.0f}%を下回っています。"
                f"バリデーションが必要な型をLevel 2に昇格させてください。"
            )

        # Level 3の比率が低すぎる場合（下限を下回っている）
        level3_min = self.threshold_ratios["level3_min"]
        if statistics.level3_ratio < level3_min:
            recommendations.append(
                f"⚠️ Level 3（BaseModel）の比率が"
                f"{statistics.level3_ratio * 100:.1f}%と低すぎます。"
                f"推奨下限の{level3_min * 100:.0f}%を下回っています。"
                f"複雑なドメイン型をLevel 3に昇格させてください。"
            )

        # ドキュメント実装率が低い場合
        if statistics.documentation.implementation_rate < 0.70:
            recommendations.append(
                f"ドキュメント実装率が"
                f"{statistics.documentation.implementation_rate * 100:.1f}%と低いです。"
                f"目標の80%以上に近づけるため、docstringを追加してください。"
            )

        # ドキュメント詳細度が低い場合
        if statistics.documentation.detail_rate < 0.50:
            recommendations.append(
                f"ドキュメント詳細度が"
                f"{statistics.documentation.detail_rate * 100:.1f}%と低いです。"
                f"Attributes、Examples等のセクションを追加してドキュメントを充実させてください。"
            )

        return recommendations

    def _calculate_deviation(self, statistics: TypeStatistics) -> dict[str, float]:
        """警告閾値との乖離を計算

        Args:
            statistics: 統計情報

        Returns:
            乖離の辞書（正の値 = 閾値を超えている、負の値 = 閾値を下回っている）
        """
        return {
            "level1_max": statistics.level1_ratio - self.threshold_ratios["level1_max"],  # 正 = 上限超過（警告）
            "level2_min": statistics.level2_ratio - self.threshold_ratios["level2_min"],  # 負 = 下限未満（警告）
            "level3_min": statistics.level3_ratio - self.threshold_ratios["level3_min"],  # 負 = 下限未満（警告）
        }

    def _count_type_usage(self, type_definitions: list[TypeDefinition]) -> dict[str, int]:
        """型の使用回数をカウント

        AST解析を使用して、実際の型参照箇所をカウントします。
        - 関数の引数・戻り値の型アノテーション
        - 変数の型アノテーション
        - Annotated, BaseModelのフィールド型
        などを参照としてカウントします。

        Args:
            type_definitions: 型定義リスト

        Returns:
            型名 -> 使用回数の辞書
        """
        import ast

        # 型名の集合を作成
        type_names = {td.name for td in type_definitions}

        # ファイルパスごとにグループ化
        files_to_analyze: dict[str, list[str]] = {}
        for td in type_definitions:
            if td.file_path not in files_to_analyze:
                files_to_analyze[td.file_path] = []
            # 対象の型名を記録（重複を避ける）
            if td.name not in files_to_analyze[td.file_path]:
                files_to_analyze[td.file_path].append(td.name)

        # 使用回数を初期化（定義のみの場合は0）
        usage_counts: dict[str, int] = {name: 0 for name in type_names}

        # 各ファイルをAST解析して参照をカウント
        for file_path_str in files_to_analyze:
            file_path = Path(file_path_str)
            try:
                with open(file_path, encoding="utf-8") as f:
                    source_code = f.read()
                tree = ast.parse(source_code)

                # 型参照をカウント
                visitor = _TypeReferenceCounter(type_names)
                visitor.visit(tree)

                # カウント結果をマージ
                for type_name, count in visitor.reference_counts.items():
                    usage_counts[type_name] += count

            except (SyntaxError, FileNotFoundError):
                # パースエラーやファイルが見つからない場合は無視
                pass

        return usage_counts

    def _deduplicate_type_definitions(self, type_definitions: list[TypeDefinition]) -> list[TypeDefinition]:
        """型定義の重複を除去

        ファイルパス、型名、行番号の組み合わせで重複判定を行います。
        これにより、異なるモジュールに存在する同名の型（例: foo.User と bar.User）が
        誤って除外されることを防ぎます。

        Args:
            type_definitions: 型定義リスト

        Returns:
            重複除去後の型定義リスト
        """
        seen_keys: set[tuple[str, str, int]] = set()
        unique_types: list[TypeDefinition] = []

        for td in type_definitions:
            key = (td.file_path, td.name, td.line_number)
            if key not in seen_keys:
                seen_keys.add(key)
                unique_types.append(td)

        return unique_types

    def _deduplicate_upgrade_recommendations(
        self, recommendations: list[UpgradeRecommendation]
    ) -> list[UpgradeRecommendation]:
        """型レベルアップ推奨の重複を除去

        ファイルパス、型名、行番号の組み合わせで重複判定を行います。
        これにより、異なるファイルに存在する同名の型の推奨が誤って除外されることを防ぎます。

        Args:
            recommendations: 推奨事項リスト

        Returns:
            重複除去後の推奨事項リスト
        """
        seen_keys: set[tuple[str, str, int]] = set()
        unique_recs: list[UpgradeRecommendation] = []

        for rec in recommendations:
            key = (rec.file_path, rec.type_name, rec.line_number)
            if key not in seen_keys:
                seen_keys.add(key)
                unique_recs.append(rec)

        return unique_recs


class _TypeReferenceCounter(ast.NodeVisitor):
    """型参照をカウントするAST Visitor

    関数の引数・戻り値、変数アノテーション、クラスのベースクラス、
    クラスフィールドなどで使用される型名をカウントします。
    """

    def __init__(self, type_names: set[str]):
        """初期化

        Args:
            type_names: カウント対象の型名の集合
        """
        self.type_names = type_names
        self.reference_counts: dict[str, int] = {name: 0 for name in type_names}

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """関数定義を訪問（引数・戻り値の型アノテーション）"""
        # 引数の型アノテーション
        for arg in node.args.args:
            if arg.annotation:
                self._count_annotation(arg.annotation)

        # 戻り値の型アノテーション
        if node.returns:
            self._count_annotation(node.returns)

        # 子ノードを訪問
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """非同期関数定義を訪問"""
        # FunctionDefと同様の処理
        for arg in node.args.args:
            if arg.annotation:
                self._count_annotation(arg.annotation)

        if node.returns:
            self._count_annotation(node.returns)

        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """変数の型アノテーション付き代入を訪問"""
        if node.annotation:
            self._count_annotation(node.annotation)

        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """クラス定義を訪問（ベースクラスの型参照をカウント）"""
        # ベースクラスをカウント（例: class MyModel(BaseModel)のBaseModel）
        for base in node.bases:
            self._count_annotation(base)

        # クラス本体内のアノテーションをカウント
        self.generic_visit(node)

    def visit_TypeAlias(self, node: ast.TypeAlias) -> None:
        """型エイリアス定義を訪問（Python 3.12+ type文）

        型エイリアスの値部分に含まれる型参照をカウントします。
        例: type CyclePath = list[NodeId] の NodeId をカウント
        """
        # 型エイリアスの値部分をカウント
        self._count_annotation(node.value)

        # 子ノードを訪問
        self.generic_visit(node)

    def _count_annotation(self, annotation: ast.expr) -> None:
        """型アノテーションから型名を抽出してカウント

        Args:
            annotation: 型アノテーションのASTノード
        """
        # Name ノード (例: UserId)
        if isinstance(annotation, ast.Name):
            if annotation.id in self.type_names:
                self.reference_counts[annotation.id] += 1

        # Subscript ノード (例: list[UserId], Annotated[str, ...])
        elif isinstance(annotation, ast.Subscript):
            # ベース型をチェック (例: list, Annotated)
            if isinstance(annotation.value, ast.Name):
                if annotation.value.id in self.type_names:
                    self.reference_counts[annotation.value.id] += 1

            # インデックス部分を再帰的にチェック
            self._count_annotation_recursive(annotation.slice)

        # その他の複雑な型 (Union, Tuple など)
        else:
            self._count_annotation_recursive(annotation)

    def _count_annotation_recursive(self, node: ast.expr) -> None:
        """型アノテーション内を再帰的に走査

        Args:
            node: 走査対象のASTノード
        """
        if isinstance(node, ast.Name):
            if node.id in self.type_names:
                self.reference_counts[node.id] += 1

        elif isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Name):
                if node.value.id in self.type_names:
                    self.reference_counts[node.value.id] += 1
            self._count_annotation_recursive(node.slice)

        elif isinstance(node, ast.Tuple):
            for elt in node.elts:
                self._count_annotation_recursive(elt)

        elif isinstance(node, ast.List):
            for elt in node.elts:
                self._count_annotation_recursive(elt)

        # BinOp (例: int | str の Union型)
        elif isinstance(node, ast.BinOp):
            self._count_annotation_recursive(node.left)
            self._count_annotation_recursive(node.right)

        # Constant, Attribute などは型名ではないのでスキップ
