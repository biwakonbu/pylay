"""
型推論モジュール

mypy の統計フラグを活用して、型推論情報を抽出します。
推論結果を既存の型アノテーションとマージし、TypeDependencyGraph を構築します。

信頼度計算
----------
型推論の信頼度は、以下の3要素を重み付けして計算されます：

1. **基礎確実性（base_certainty）**: mypyの診断結果から導出（重み: 0.5）
   - エラー/警告メッセージの有無を検査
   - エラーがなければ確実性1.0、警告があれば0.7、エラーがあれば0.3

2. **型複雑度ペナルティ（complexity_penalty）**: 型の複雑さに基づく減点（重み: 0.3）
   - Union型: 0.15/個
   - Optional/None: 0.1/個
   - ジェネリック型（[の数）: 0.1/個
   - Any型: 0.2/個
   - ペナルティは最大1.0でキャップ

3. **アノテーション品質ボーナス（annotation_bonus）**: 明示的型アノテーションの
   有無（重み: 0.2）
   - 周辺スコープのアノテーション率を非線形（^0.8）で評価
   - 型情報が豊富な環境では推論精度が向上すると仮定

最終的な信頼度スコアは以下の式で計算されます：

    confidence = 0.5 * base_certainty + 0.3 * (1.0 - complexity_penalty)
                 + 0.2 * annotation_bonus

スコアは0.0-1.0の範囲にクリップされます。

使用例
------
    >>> from src.core.analyzer.type_inferrer import TypeInferenceAnalyzer
    >>> analyzer = TypeInferenceAnalyzer()
    >>> graph = analyzer.analyze("path/to/file.py")
    >>> for node in graph.nodes:
    ...     print(f"{node.name}: {node.attributes.get('inferred_type')}")
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import tempfile
from pathlib import Path

from src.core.analyzer.abc_base import Analyzer
from src.core.analyzer.exceptions import MypyExecutionError
from src.core.analyzer.models import InferResult, MypyResult
from src.core.schemas.graph import GraphNode, TypeDependencyGraph
from src.core.schemas.types import (
    GraphMetadata,
    create_confidence_score,
    create_line_number,
)

# モジュールレベル定数
DEFAULT_UNTYPED = "Any"  # アノテーションがない場合のデフォルト値（将来設定可能にする可能性あり）


class TypeInferenceAnalyzer(Analyzer):
    """
    型推論に特化したAnalyzer

    mypyとASTを組み合わせた型推論を実行し、グラフを生成します。
    """

    def analyze(self, input_path: Path | str) -> TypeDependencyGraph:
        """
        指定された入力から型推論を実行し、グラフを生成します。

        Args:
            input_path: 解析対象のファイルパスまたはコード文字列

        Returns:
            型推論結果を含むTypeDependencyGraph

        Raises:
            ValueError: 入力が無効な場合、またはファイルが存在しない場合
        """
        if isinstance(input_path, str):
            # コード文字列の場合、一時ファイルを作成
            from pydantic import ValidationError

            from src.core.analyzer.models import TempFileConfig
            from src.core.utils.io_helpers import cleanup_temp_file, create_temp_file

            try:
                temp_config = TempFileConfig(code=input_path, suffix=".py", mode="w")
            except ValidationError as e:
                raise ValueError(f"無効な入力: {e}") from e
            temp_path = create_temp_file(temp_config)
            try:
                return self._analyze_from_file(temp_path)
            finally:
                cleanup_temp_file(temp_path)
        elif isinstance(input_path, Path):
            return self._analyze_from_file(input_path)
        else:
            raise ValueError("input_path は Path または str でなければなりません")

    def _analyze_from_file(self, file_path: Path) -> TypeDependencyGraph:
        """ファイルから型推論を実行"""
        if not file_path.exists():
            raise ValueError(f"ファイルが存在しません: {file_path}")

        # 既存アノテーション抽出
        existing_annotations = self.extract_existing_annotations(str(file_path))

        # mypy型推論
        inferred_types = self.infer_types_from_file(str(file_path))

        # マージ
        merged_types = self.merge_inferred_types(existing_annotations, inferred_types)

        # グラフ構築
        graph = TypeDependencyGraph(nodes=[], edges=[])
        for var_name, type_info in merged_types.items():
            node = GraphNode(
                name=var_name,
                node_type="inferred_variable",
                attributes={
                    "source_file": str(file_path),
                    "inferred_type": str(type_info),
                    "extraction_method": "mypy_inferred",
                },
            )
            graph.add_node(node)

        # メタデータ追加
        graph.metadata = GraphMetadata(
            custom_fields={
                "analysis_type": "type_inference",
                "source_file": str(file_path),
            },
            statistics={
                "inferred_count": len(merged_types),
            },
        )

        return graph

    def infer_types_from_code(self, code: str) -> dict[str, InferResult]:
        """
        与えられたPythonコードから型を推論します。

        Args:
            code: 推論対象のPythonコード

        Returns:
            推論された型情報の辞書

        Raises:
            RuntimeError: mypy推論に失敗した場合
        """
        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_file_path = f.name

        try:
            # mypy コマンドの構築（config_fileは後で追加可能）
            cmd = ["uv", "run", "mypy", "--inferstats", "--timing-stats"]
            cmd.append(temp_file_path)

            # mypy --inferstats --timing-stats を実行
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent.parent,  # pylayルート
            )

            if result.returncode != 0:
                # mypyエラーを無視して続行（推論は成功する場合がある）
                pass

            # 推論結果を解析
            inferred_types = self.parse_mypy_output(result.stdout)

            return inferred_types

        finally:
            # 一時ファイルを削除
            os.unlink(temp_file_path)

    def parse_mypy_output(self, output: str) -> dict[str, InferResult]:
        """
        mypyの出力を解析して型情報を抽出します。

        Args:
            output: mypyの標準出力

        Returns:
            抽出された型情報の辞書
        """
        # グローバル関数を使用（重複を避けるため）
        return _parse_mypy_output(output)

    def merge_inferred_types(
        self,
        existing_annotations: dict[str, str],
        inferred_types: dict[str, InferResult],
    ) -> dict[str, str]:
        """
        既存の型アノテーションと推論結果をマージします。

        Args:
            existing_annotations: 既存の型アノテーション
            inferred_types: 推論された型情報

        Returns:
            マージされた型アノテーション
        """
        merged = existing_annotations.copy()

        for var_name, infer_result in inferred_types.items():
            if var_name not in merged:
                # 推論された型を追加（Pydanticモデルのフィールドアクセス）
                merged[var_name] = infer_result.inferred_type

        return merged

    def infer_types_from_file(self, file_path: str) -> dict[str, InferResult]:
        """
        ファイルから型を推論します。

        Args:
            file_path: Pythonファイルのパス

        Returns:
            推論された型情報の辞書
        """
        with open(file_path, encoding="utf-8") as f:
            code = f.read()

        return self.infer_types_from_code(code)

    def extract_existing_annotations(self, file_path: str) -> dict[str, str]:
        """
        既存のファイルから型アノテーションを抽出します。

        Args:
            file_path: Pythonファイルのパス

        Returns:
            抽出された型アノテーションの辞書
        """
        with open(file_path, encoding="utf-8") as f:
            tree = ast.parse(f.read())

        annotations = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.AnnAssign):
                # 型付きの代入（例: x: int = 5）
                var_name = node.target.id if isinstance(node.target, ast.Name) else None
                if var_name:
                    annotations[var_name] = ast.unparse(node.annotation)
            elif isinstance(node, ast.FunctionDef):
                # 関数引数の型
                for arg in node.args.args:
                    if arg.annotation and arg.arg not in annotations:  # アノテーションがある場合のみ追加
                        annotations[arg.arg] = ast.unparse(arg.annotation)

        return annotations


def run_mypy_inference(file_path: Path, mypy_flags: list[str], timeout: int = 60) -> MypyResult:
    """
    mypyを実行して型推論を行うユーティリティ関数

    Args:
        file_path: 解析対象のファイルパス
        mypy_flags: mypyフラグのリスト
        timeout: タイムアウト（秒）

    Returns:
        mypy実行結果（推論された型情報を含む）

    Raises:
        MypyExecutionError: mypy実行に失敗した場合
    """
    cmd = ["uv", "run", "mypy", *mypy_flags, str(file_path)]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path(__file__).parent.parent.parent,
        )
    except subprocess.TimeoutExpired:
        raise MypyExecutionError(
            f"mypy実行がタイムアウトしました（{timeout}秒）",
            return_code=-1,
            file_path=str(file_path),
        )
    except FileNotFoundError:
        raise MypyExecutionError(
            "mypyコマンドが見つかりません。uvがインストールされているか確認してください。",
            return_code=-1,
            file_path=str(file_path),
        )

    # 結果を解析
    mypy_result = MypyResult(stdout=result.stdout, stderr=result.stderr, return_code=result.returncode)

    # 推論結果をパース
    inferred_types = _parse_mypy_output(result.stdout)
    mypy_result.inferred_types = inferred_types

    return mypy_result


def _compute_confidence(
    type_info: str,
    mypy_output: str,
    var_name: str,
    annotation_coverage: float = 0.5,
) -> float:
    """
    型推論の信頼度を計算します。

    信頼度は以下の3要素を重み付けして計算します：
    1. 基礎確実性（base_certainty）: mypyの診断結果から導出（重み: 0.5）
       - エラー/警告メッセージの有無を検査
       - エラーがなければ高い確実性、警告があれば中程度、エラーがあれば低い
    2. 型複雑度ペナルティ（complexity_penalty）: 型の複雑さに基づく
       減点（重み: 0.3）
       - Union、Optional、ジェネリック型の数に応じて減点
       - 複雑な型ほど推論の不確実性が高いと仮定
    3. アノテーション品質ボーナス（annotation_bonus）: 明示的型アノテーションの
       有無（重み: 0.2）
       - 周辺スコープにアノテーションが存在すれば加点
       - 型情報が豊富な環境では推論精度が向上すると仮定

    重み: certainty=0.5, complexity=0.3, annotation=0.2

    Args:
        type_info: 推論された型情報
        mypy_output: mypyの完全な出力（エラー/警告チェック用）
        var_name: 変数名（診断メッセージの検索用）
        annotation_coverage: 周辺スコープのアノテーション率（0.0-1.0）

    Returns:
        計算された信頼度（0.0-1.0）

    Examples:
        >>> _compute_confidence("int", "", "x", 0.8)
        0.95  # 単純型、エラーなし、高カバレッジ

        >>> _compute_confidence("Union[int, str, None]", "error: x", "x", 0.3)
        0.42  # 複雑型、エラーあり、低カバレッジ
    """
    # 重み定義
    W_CERTAINTY = 0.5
    W_COMPLEXITY = 0.3
    W_ANNOTATION = 0.2

    # 1. 基礎確実性の計算
    base_certainty = _compute_base_certainty(mypy_output, var_name)

    # 2. 型複雑度ペナルティの計算
    complexity_penalty = _compute_complexity_penalty(type_info)

    # 3. アノテーション品質ボーナスの計算
    annotation_bonus = _compute_annotation_bonus(annotation_coverage)

    # 重み付き平均で最終スコアを計算
    confidence = (
        W_CERTAINTY * base_certainty + W_COMPLEXITY * (1.0 - complexity_penalty) + W_ANNOTATION * annotation_bonus
    )

    # 0.0-1.0の範囲にクリップ
    return max(0.0, min(1.0, confidence))


def _compute_base_certainty(mypy_output: str, var_name: str) -> float:
    """
    mypyの診断結果から基礎確実性を計算します。

    Args:
        mypy_output: mypyの完全な出力
        var_name: 変数名

    Returns:
        基礎確実性スコア（0.0-1.0）
    """
    # 変数名を含むエラー/警告メッセージを検索
    error_pattern = re.compile(rf"\berror\b.*\b{re.escape(var_name)}\b", re.IGNORECASE)
    warning_pattern = re.compile(rf"\bwarning\b.*\b{re.escape(var_name)}\b", re.IGNORECASE)

    has_error = bool(error_pattern.search(mypy_output))
    has_warning = bool(warning_pattern.search(mypy_output))

    if has_error:
        return 0.3  # エラーあり: 低い確実性
    elif has_warning:
        return 0.7  # 警告のみ: 中程度の確実性
    else:
        return 1.0  # エラー/警告なし: 高い確実性


def _compute_complexity_penalty(type_info: str) -> float:
    """
    型の複雑さに基づくペナルティを計算します。

    Args:
        type_info: 型情報文字列

    Returns:
        複雑度ペナルティ（0.0-1.0、高いほど複雑）
    """
    penalty = 0.0

    # Union型のカウント（Union[...] または | 構文）
    union_count = type_info.count("Union[") + type_info.count(" | ")
    penalty += union_count * 0.15

    # Optional/None のカウント
    optional_count = type_info.count("Optional[") + type_info.count("| None")
    penalty += optional_count * 0.1

    # ジェネリック型のカウント（ネストした [ ] の深さ）
    generic_depth = type_info.count("[")
    penalty += generic_depth * 0.1

    # Anyのカウント（型安全性の欠如）
    any_count = type_info.count("Any")
    penalty += any_count * 0.2

    # 0.0-1.0の範囲にクリップ
    return min(1.0, penalty)


def _compute_annotation_bonus(annotation_coverage: float) -> float:
    """
    周辺スコープのアノテーションカバレッジに基づくボーナスを計算します。

    Args:
        annotation_coverage: アノテーション率（0.0-1.0）

    Returns:
        アノテーションボーナススコア（0.0-1.0）
    """
    # カバレッジが高いほど高いボーナス（非線形に強調）
    return annotation_coverage**0.8


def _parse_mypy_output(output: str) -> dict[str, InferResult]:
    """
    mypyの出力を解析して型情報を抽出します。

    Args:
        output: mypyの標準出力

    Returns:
        抽出された型情報の辞書
    """
    types: dict[str, InferResult] = {}
    lines = output.split("\n")

    for line_num, line in enumerate(lines, start=1):
        # 空行とコメント行をスキップ
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # 型アノテーション行のみを処理
        if "->" in line and ":" in line:
            try:
                # maxsplit=1で最初の":"のみで分割（型に":"が含まれる場合に対応）
                parts = line.split(":", maxsplit=1)
                if len(parts) < 2:
                    continue

                var_name = parts[0].strip()
                type_info = parts[1].strip()

                # 変数名と型情報が空でないことを検証
                if not var_name or not type_info:
                    continue

                # 信頼度を計算（アノテーションカバレッジは暫定的に0.5を使用）
                confidence = _compute_confidence(
                    type_info=type_info,
                    mypy_output=output,
                    var_name=var_name,
                    annotation_coverage=0.5,
                )

                types[var_name] = InferResult(
                    variable_name=var_name,
                    inferred_type=type_info,
                    confidence=create_confidence_score(confidence),
                    line_number=create_line_number(line_num),
                )
            except (ValueError, AttributeError):
                # パースエラーは無視して次の行に進む
                # ログ出力が必要な場合はここに追加可能
                continue

    return types
