"""
NewType直接使用の検出と警告

このモジュールは、ファクトリ関数が存在するNewType型の直接使用を検出し、
推奨される修正方法を提案します。
"""

import ast
import re
from dataclasses import dataclass
from pathlib import Path

from src.core.schemas.types import FilePath, LineNumber


@dataclass(frozen=True)
class NewTypeDefinition:
    """NewType定義情報"""

    name: str
    base_type: str
    line_number: int
    has_factory: bool
    factory_name: str | None


@dataclass(frozen=True)
class DirectUsageIssue:
    """NewType直接使用の問題"""

    file_path: FilePath
    line_number: LineNumber
    type_name: str
    factory_name: str
    code_snippet: str

    def to_dict(self) -> dict[str, object]:
        """辞書形式に変換"""
        return {
            "file_path": str(self.file_path),
            "line_number": int(self.line_number),
            "type_name": self.type_name,
            "factory_name": self.factory_name,
            "code_snippet": self.code_snippet,
        }


class FactoryUsageChecker:
    """NewType直接使用を検出するチェッカー"""

    def __init__(self) -> None:
        """チェッカーを初期化"""
        self.newtype_defs: dict[str, NewTypeDefinition] = {}
        self.imported_types: dict[str, str] = {}  # 型名 -> インポート元モジュール
        self.known_factories: dict[str, str] = {}  # 型名 -> ファクトリ関数名
        self._load_known_factories()

    def _load_known_factories(self) -> None:
        """既知の型定義モジュールからファクトリ関数マッピングを読み込む"""
        # src/core/schemas/types.py のファクトリ関数
        self.known_factories.update(
            {
                "IndexFilename": "create_index_filename",
                "LayerFilenameTemplate": "create_layer_filename_template",
                "DirectoryPath": "create_directory_path",
                "MaxDepth": "create_max_depth",
                "Weight": "create_weight",
                "ConfidenceScore": "create_confidence_score",
                "LineNumber": "create_line_number",
                "PositiveInt": "create_positive_int",
                "NonNegativeInt": "create_non_negative_int",
            }
        )

        # src/core/analyzer/types.py のファクトリ関数
        self.known_factories.update(
            {
                "Percentage": "create_percentage",
            }
        )

        # src/core/converters/types.py のファクトリ関数も追加
        # 注: MaxDepthは schemas/types.py と converters/types.py 両方に存在

    def check_file(self, file_path: Path) -> list[DirectUsageIssue]:
        """ファイルをチェックし、NewType直接使用を検出

        Args:
            file_path: チェック対象のファイルパス

        Returns:
            検出された問題のリスト
        """
        if not file_path.exists():
            return []

        try:
            source_code = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source_code, filename=str(file_path))
        except (OSError, SyntaxError):
            return []

        # Step 1: インポート情報を収集
        self._collect_imports(tree, file_path)

        # Step 2: NewType定義とファクトリ関数を収集
        self._collect_newtype_definitions(tree)

        # Step 3: NewType直接使用を検出
        issues = self._detect_direct_usage(tree, file_path, source_code)

        return issues

    def _collect_imports(self, tree: ast.AST, file_path: Path) -> None:
        """インポート情報を収集

        Args:
            tree: ASTツリー
            file_path: 現在のファイルパス
        """
        self.imported_types.clear()

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if not node.module:
                    continue

                # src.core.schemas.types からのインポートを追跡
                for alias in node.names:
                    type_name = alias.asname or alias.name
                    self.imported_types[type_name] = node.module

    def _collect_newtype_definitions(self, tree: ast.AST) -> None:
        """NewType定義とファクトリ関数を収集

        Args:
            tree: ASTツリー
        """
        self.newtype_defs.clear()

        # NewType定義を検出
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                self._check_newtype_assignment(node)

        # ファクトリ関数を検出
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self._check_factory_function(node)

    def _check_newtype_assignment(self, node: ast.Assign) -> None:
        """NewType定義の代入をチェック

        Args:
            node: 代入ノード
        """
        if not isinstance(node.value, ast.Call):
            return

        # NewType(...) のパターンを検出
        if not (
            isinstance(node.value.func, ast.Name) and node.value.func.id == "NewType"
        ):
            return

        if len(node.value.args) < 2:
            return

        # 型名を取得
        if not isinstance(node.value.args[0], ast.Constant):
            return

        type_name_value = node.value.args[0].value
        if not isinstance(type_name_value, str):
            return
        type_name = type_name_value

        # 基底型を取得
        base_type_node = node.value.args[1]
        base_type = self._get_type_name(base_type_node)

        # NewType定義を記録
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == type_name:
                self.newtype_defs[type_name] = NewTypeDefinition(
                    name=type_name,
                    base_type=base_type,
                    line_number=node.lineno,
                    has_factory=False,
                    factory_name=None,
                )

    def _check_factory_function(self, node: ast.FunctionDef) -> None:
        """ファクトリ関数をチェック

        Args:
            node: 関数定義ノード
        """
        # create_* パターンのファクトリ関数を検出
        match = re.match(r"create_(.+)", node.name)
        if not match:
            return

        # snake_caseからPascalCaseに変換
        type_name_snake = match.group(1)
        type_name = self._snake_to_pascal(type_name_snake)

        # 対応するNewType定義が存在するかチェック
        if type_name in self.newtype_defs:
            # ファクトリ関数が存在することを記録
            old_def = self.newtype_defs[type_name]
            self.newtype_defs[type_name] = NewTypeDefinition(
                name=old_def.name,
                base_type=old_def.base_type,
                line_number=old_def.line_number,
                has_factory=True,
                factory_name=node.name,
            )

    def _detect_direct_usage(
        self, tree: ast.AST, file_path: Path, source_code: str
    ) -> list[DirectUsageIssue]:
        """NewType直接使用を検出

        Args:
            tree: ASTツリー
            file_path: ファイルパス
            source_code: ソースコード

        Returns:
            検出された問題のリスト
        """
        issues: list[DirectUsageIssue] = []
        source_lines = source_code.splitlines()

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            # TypeName(...) のパターンを検出
            if not isinstance(node.func, ast.Name):
                continue

            type_name = node.func.id

            # ファクトリ関数名を取得
            factory_name: str | None = None

            # ケース1: 同一ファイル内で定義されたNewType
            if type_name in self.newtype_defs:
                newtype_def = self.newtype_defs[type_name]
                if not newtype_def.has_factory:
                    continue
                factory_name = newtype_def.factory_name

                # 定義行自体は除外
                if node.lineno == newtype_def.line_number:
                    continue

                # ファクトリ関数内での使用は除外（return文など）
                if self._is_in_factory_function(node, tree, factory_name):
                    continue

            # ケース2: インポートされた型（既知のファクトリ関数が存在）
            elif type_name in self.imported_types and type_name in self.known_factories:
                factory_name = self.known_factories[type_name]

            else:
                # ファクトリ関数が存在しない型はスキップ
                continue

            if not factory_name:
                continue

            # 問題として記録
            code_snippet = (
                source_lines[node.lineno - 1].strip()
                if node.lineno <= len(source_lines)
                else ""
            )

            issues.append(
                DirectUsageIssue(
                    file_path=str(file_path),
                    line_number=LineNumber(node.lineno),  # type: ignore[arg-type]
                    type_name=type_name,
                    factory_name=factory_name,
                    code_snippet=code_snippet,
                )
            )

        return issues

    def _is_in_factory_function(
        self, node: ast.AST, tree: ast.AST, factory_name: str | None
    ) -> bool:
        """ノードがファクトリ関数内に存在するかチェック

        Args:
            node: チェック対象ノード
            tree: ASTツリー
            factory_name: ファクトリ関数名

        Returns:
            ファクトリ関数内に存在する場合True
        """
        if not factory_name:
            return False

        for func_node in ast.walk(tree):
            if (
                isinstance(func_node, ast.FunctionDef)
                and func_node.name == factory_name
            ):
                # ノードが関数内に存在するかチェック
                for child in ast.walk(func_node):
                    if child is node:
                        return True

        return False

    def _get_type_name(self, node: ast.AST) -> str:
        """型ノードから型名を取得

        Args:
            node: 型ノード

        Returns:
            型名
        """
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Constant):
            return str(node.value)
        return "unknown"

    def _snake_to_pascal(self, snake_str: str) -> str:
        """snake_caseをPascalCaseに変換

        Args:
            snake_str: snake_case文字列

        Returns:
            PascalCase文字列
        """
        components = snake_str.split("_")
        return "".join(x.capitalize() for x in components)


def check_directory(
    directory: Path, pattern: str = "**/*.py"
) -> dict[str, list[DirectUsageIssue]]:
    """ディレクトリ内のファイルをチェック

    Args:
        directory: チェック対象ディレクトリ
        pattern: ファイルパターン

    Returns:
        ファイルパスをキー、問題リストを値とする辞書
    """
    checker = FactoryUsageChecker()
    results: dict[str, list[DirectUsageIssue]] = {}

    for file_path in directory.glob(pattern):
        if not file_path.is_file():
            continue

        issues = checker.check_file(file_path)
        if issues:
            results[str(file_path)] = issues

    return results
