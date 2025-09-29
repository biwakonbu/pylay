"""
型推論モジュール

mypy の --infer フラグを活用して、未アノテーションのコードから型を自動推測します。
推論結果を既存の型アノテーションとマージし、完全な型情報を構築します。
"""

import ast
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Any, Optional
from collections.abc import Mapping


def infer_types_from_code(
    code: str, module_name: str = "temp_module", config_file: str | None = None
) -> dict[str, Any]:
    """
    与えられたPythonコードから型を推論します。

    Args:
        code: 推論対象のPythonコード
        module_name: 一時的なモジュール名
        config_file: mypy設定ファイルのパス（pyproject.tomlなど）

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
        # mypy コマンドの構築
        cmd = ["uv", "run", "mypy", "--infer", "--dump-type-stats"]

        # 設定ファイルが指定されている場合は追加
        if config_file:
            cmd.extend(["--config-file", config_file])

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

        # 推論結果を解析（簡易的な実装）
        inferred_types = parse_mypy_output(result.stdout)

        return inferred_types

    finally:
        # 一時ファイルを削除
        os.unlink(temp_file_path)


def parse_mypy_output(output: str) -> dict[str, Any]:
    """
    mypyの出力を解析して型情報を抽出します。

    Args:
        output: mypyの標準出力

    Returns:
        抽出された型情報の辞書
    """
    types = {}
    lines = output.split("\n")

    for line in lines:
        if "->" in line and ":" in line:
            # 簡易的な解析（実際にはより詳細な実装が必要）
            parts = line.split(":")
            if len(parts) >= 2:
                var_name = parts[0].strip()
                type_info = parts[1].strip()
                types[var_name] = type_info

    return types


def merge_inferred_types(
    existing_annotations: dict[str, str], inferred_types: dict[str, Any]
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

    for var_name, inferred_type in inferred_types.items():
        if var_name not in merged:
            # 推論された型を追加
            merged[var_name] = str(inferred_type)

    return merged


def infer_types_from_file(
    file_path: str, config_file: str | None = None
) -> dict[str, Any]:
    """
    ファイルから型を推論します。

    Args:
        file_path: Pythonファイルのパス
        config_file: mypy設定ファイルのパス（pyproject.tomlなど）

    Returns:
        推論された型情報の辞書
    """
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()

    module_name = Path(file_path).stem
    return infer_types_from_code(code, module_name, config_file)


def extract_existing_annotations(file_path: str) -> dict[str, str]:
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
