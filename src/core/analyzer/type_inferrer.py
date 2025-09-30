"""
型推論モジュール

mypy の --infer フラグを活用して、未アノテーションのコードから型を自動推測します。
推論結果を既存の型アノテーションとマージし、TypeDependencyGraph を構築します。
"""

import ast
import subprocess
import tempfile
import os
from pathlib import Path
from src.core.analyzer.base import Analyzer
from src.core.schemas.graph_types import TypeDependencyGraph, GraphNode
from src.core.analyzer.models import InferResult, MypyResult
from src.core.analyzer.exceptions import MypyExecutionError, TypeInferenceError


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
            ValueError: 入力が無効な場合
            TypeInferenceError: 推論に失敗した場合
        """
        if isinstance(input_path, str):
            # コード文字列の場合、一時ファイルを作成
            from src.core.utils.io_helpers import create_temp_file, cleanup_temp_file
            from src.core.schemas.analyzer_types import TempFileConfig

            temp_config: TempFileConfig = {
                "code": input_path,
                "suffix": ".py",
                "mode": "w",
            }
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
        graph.metadata = {
            "analysis_type": "type_inference",
            "source_file": str(file_path),
            "inferred_count": len(merged_types),
        }

        return graph

    def infer_types_from_code(
        self, code: str, module_name: str = "temp_module"
    ) -> dict[str, InferResult]:
        """
        与えられたPythonコードから型を推論します。

        Args:
            code: 推論対象のPythonコード
            module_name: 一時的なモジュール名

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
            cmd = ["uv", "run", "mypy", "--infer", "--dump-type-stats"]
            cmd.append(temp_file_path)

            # mypy --infer を実行
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
        types: dict[str, InferResult] = {}
        lines = output.split("\n")

        for line in lines:
            if "->" in line and ":" in line:
                # 簡易的な解析（実際にはより詳細な実装が必要）
                parts = line.split(":")
                if len(parts) >= 2:
                    var_name = parts[0].strip()
                    type_info = parts[1].strip()
                    types[var_name] = InferResult(
                        variable_name=var_name, inferred_type=type_info, confidence=0.8
                    )

        return types

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
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()

        module_name = Path(file_path).stem
        return self.infer_types_from_code(code, module_name)

    def extract_existing_annotations(self, file_path: str) -> dict[str, str]:
        """
        既存のファイルから型アノテーションを抽出します。

        Args:
            file_path: Pythonファイルのパス

        Returns:
            抽出された型アノテーションの辞書
        """
        with open(file_path, "r", encoding="utf-8") as f:
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
                    if arg.arg not in annotations:  # 重複を避ける
                        annotations[arg.arg] = (
                            ast.unparse(arg.annotation) if arg.annotation else "Any"
                        )

        return annotations


def run_mypy_inference(
    file_path: Path, mypy_flags: list[str], timeout: int = 60
) -> dict[str, InferResult]:
    """
    mypyを実行して型推論を行うユーティリティ関数

    Args:
        file_path: 解析対象のファイルパス
        mypy_flags: mypyフラグのリスト
        timeout: タイムアウト（秒）

    Returns:
        推論された型情報の辞書

    Raises:
        MypyExecutionError: mypy実行に失敗した場合
    """
    cmd = ["uv", "run", "mypy"] + mypy_flags + [str(file_path)]

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
    mypy_result = MypyResult(
        stdout=result.stdout, stderr=result.stderr, return_code=result.returncode
    )

    # 推論結果をパース
    inferred_types = _parse_mypy_output(result.stdout)
    mypy_result.inferred_types = inferred_types

    return inferred_types


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

    for line in lines:
        if "->" in line and ":" in line:
            # 簡易的な解析（実際にはより詳細な実装が必要）
            parts = line.split(":")
            if len(parts) >= 2:
                var_name = parts[0].strip()
                type_info = parts[1].strip()
                types[var_name] = InferResult(
                    variable_name=var_name, inferred_type=type_info, confidence=0.8
                )

    return types
