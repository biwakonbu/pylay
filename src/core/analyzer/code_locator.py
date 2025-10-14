"""
型問題箇所のコード特定モジュール

このモジュールは、型レベル分析で検出された問題について、
該当するコードの位置（ファイル、行、カラム）と実際の実装内容を特定する。
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from src.core.analyzer.type_level_models import TypeDefinition


@dataclass
class CodeLocation:
    """コード位置情報

    Attributes:
        file: ファイルパス
        line: 行番号（1始まり）
        column: カラム位置（0始まり）
        code: 該当する行のコード
        context_before: 前の2行のコード（リスト）
        context_after: 後の2行のコード（リスト）
    """

    file: Path
    line: int
    column: int
    code: str
    context_before: list[str] = field(default_factory=list)
    context_after: list[str] = field(default_factory=list)


@dataclass
class PrimitiveUsageDetail:
    """Primitive型使用の詳細情報

    Attributes:
        location: コード位置
        kind: 使用箇所の種類（function_argument, return_type, class_attribute）
        primitive_type: 使用されているprimitive型（str, int, float, bool等）
        function_name: 関数名（kind=function_*の場合）
        class_name: クラス名（kind=class_attributeの場合）
    """

    location: CodeLocation
    kind: Literal["function_argument", "return_type", "class_attribute"]
    primitive_type: str
    function_name: str | None = None
    class_name: str | None = None


@dataclass
class TypeUsageExample:
    """型使用箇所の例

    Attributes:
        location: コード位置
        context: 使用されているコンテキスト（例: "user_id: UserId"）
        kind: 使用種類（function_argument, return_type, variable_annotation）
    """

    location: CodeLocation
    context: str
    kind: Literal["function_argument", "return_type", "variable_annotation", "class_attribute"]


@dataclass
class Level1TypeDetail:
    """Level 1型の詳細情報

    Attributes:
        type_name: 型名
        definition: 型定義（例: "type UserId = str"）
        location: 定義位置
        usage_count: 使用回数
        docstring: docstring（存在する場合）
        usage_examples: 使用箇所の例（最大3件）
        recommendation: 推奨事項
    """

    type_name: str
    definition: str
    location: CodeLocation
    usage_count: int
    docstring: str | None
    usage_examples: list[TypeUsageExample]
    recommendation: str


@dataclass
class UnusedTypeDetail:
    """被参照0型の詳細情報

    Attributes:
        type_name: 型名
        definition: 型定義
        location: 定義位置
        level: 型レベル（Level 1/2/3）
        docstring: docstring（存在する場合）
        reason: 調査推奨の理由
        recommendation: 推奨事項
    """

    type_name: str
    definition: str
    location: CodeLocation
    level: Literal["Level 1", "Level 2", "Level 3"]
    docstring: str | None
    reason: Literal["implementation_in_progress", "lack_of_awareness", "future_extensibility"]
    recommendation: str


@dataclass
class DeprecatedTypingDetail:
    """非推奨typing使用の詳細情報

    Attributes:
        location: import文の位置
        imports: 非推奨importのリスト
        suggestion: 推奨される代替構文
    """

    location: CodeLocation
    imports: list[dict[str, str]]  # [{"deprecated": "List", "recommended": "list"}, ...]
    suggestion: str


class CodeLocator:
    """コード位置特定エンジン

    型レベル分析で検出された問題について、該当コードの位置と内容を特定する。
    """

    def __init__(self, target_dirs: list[Path]) -> None:
        """初期化

        Args:
            target_dirs: 解析対象ディレクトリのリスト
        """
        self.target_dirs = target_dirs
        self._file_cache: dict[Path, list[str]] = {}

    def find_primitive_usages(self) -> list[PrimitiveUsageDetail]:
        """Primitive型の直接使用箇所を検出

        Returns:
            検出された問題のリスト
        """
        details: list[PrimitiveUsageDetail] = []

        # 対象ディレクトリ内の全Pythonファイルを処理
        for target_dir in self.target_dirs:
            for py_file in target_dir.rglob("*.py"):
                if not py_file.is_file():
                    continue

                try:
                    with open(py_file, encoding="utf-8") as f:
                        source_code = f.read()

                    tree = ast.parse(source_code, filename=str(py_file))
                    visitor = PrimitiveUsageVisitor(py_file, source_code)
                    visitor.visit(tree)
                    details.extend(visitor.details)

                except (SyntaxError, UnicodeDecodeError):
                    # パースできないファイルはスキップ
                    continue

        return details

    def find_level1_types(self, type_definitions: list[TypeDefinition]) -> list[Level1TypeDetail]:
        """Level 1型の詳細情報を取得

        Args:
            type_definitions: 型定義のリスト

        Returns:
            Level 1型の詳細情報リスト
        """
        details: list[Level1TypeDetail] = []

        # 型名をキーとした辞書に変換
        type_dict = {td.name: td for td in type_definitions}

        for type_name, type_def in type_dict.items():
            # Level 1以外はスキップ
            if type_def.level != "level1":
                continue

            # @target-level: level1 や @keep-as-is: true タグがある場合はスキップ
            if type_def.target_level == "level1" or type_def.keep_as_is:
                continue

            # 使用回数をカウント(簡易実装)
            usage_count = self._count_type_usage(type_name, type_definitions)

            # 使用回数が1回以上ある場合のみ対象
            if usage_count < 1:
                continue

            # 使用例を取得(最大3件)
            usage_examples = self._find_type_usage_examples(type_name, max_examples=3)

            # 推奨事項を生成
            recommendation = self._generate_level1_recommendation(type_def, usage_count)

            # コード位置情報を取得
            context_before, code, context_after = self._extract_context(Path(type_def.file_path), type_def.line_number)
            location = CodeLocation(
                file=Path(type_def.file_path),
                line=type_def.line_number,
                column=0,  # 簡易実装
                code=code,
                context_before=context_before,
                context_after=context_after,
            )

            detail = Level1TypeDetail(
                type_name=type_name,
                definition=type_def.definition,
                location=location,
                usage_count=usage_count,
                docstring=type_def.docstring,
                usage_examples=usage_examples,
                recommendation=recommendation,
            )
            details.append(detail)

        return details

    def _count_type_usage(
        self,
        type_name: str,
        type_definitions: dict[str, TypeDefinition] | list[TypeDefinition],
    ) -> int:
        """型の使用回数をカウント

        Args:
            type_name: カウント対象の型名
            type_definitions: 型定義辞書またはリスト

        Returns:
            使用回数
        """
        # 辞書に変換
        type_dict = {td.name: td for td in type_definitions} if isinstance(type_definitions, list) else type_definitions

        # 簡易実装:他の型定義内での使用をカウント
        count = 0
        for other_type_def in type_dict.values():
            if other_type_def.name != type_name:
                # 定義内で型名が登場する回数をカウント
                count += other_type_def.definition.count(type_name)

        return count

    def _find_type_usage_examples(self, type_name: str, max_examples: int = 3) -> list[TypeUsageExample]:
        """型の使用例を取得

        Args:
            type_name: 対象の型名
            max_examples: 最大取得件数

        Returns:
            使用例のリスト
        """
        examples: list[TypeUsageExample] = []

        # 対象ディレクトリ内のファイルを検索
        for target_dir in self.target_dirs:
            for py_file in target_dir.rglob("*.py"):
                if not py_file.is_file():
                    continue

                try:
                    with open(py_file, encoding="utf-8") as f:
                        source_code = f.read()

                    tree = ast.parse(source_code, filename=str(py_file))
                    visitor = TypeUsageVisitor(type_name, py_file, source_code)
                    visitor.visit(tree)
                    examples.extend(visitor.usages)

                    # 最大件数に達したら終了
                    if len(examples) >= max_examples:
                        break

                except (SyntaxError, UnicodeDecodeError):
                    continue

            if len(examples) >= max_examples:
                break

        return examples[:max_examples]

    def _generate_level1_recommendation(self, _type_def: TypeDefinition, usage_count: int) -> str:
        """Level 1型に対する推奨事項を生成

        Args:
            _type_def: 型定義（将来の拡張用、現在は未使用）
            usage_count: 使用回数

        Returns:
            推奨事項
        """
        if usage_count > 10:
            return "使用回数が多く、制約を追加してLevel 2へ昇格させることを強く推奨します。"
        elif usage_count > 5:
            return "使用回数が比較的多く、Level 2への昇格を検討してください。"
        else:
            return "使用回数が少ないため、必要に応じてLevel 2への昇格を検討してください。"

    def find_unused_types(self, type_definitions: list[TypeDefinition]) -> list[UnusedTypeDetail]:
        """被参照0型の詳細情報を取得

        Args:
            type_definitions: 型定義のリスト

        Returns:
            被参照0型の詳細情報リスト
        """
        details: list[UnusedTypeDetail] = []

        # 型名をキーとした辞書に変換
        type_dict = {td.name: td for td in type_definitions}

        for type_name, type_def in type_dict.items():
            # __all__ でエクスポートされている型は除外
            if self._is_exported_type(type_name):
                continue

            # @keep-as-is: true タグがある型は除外
            if type_def.keep_as_is:
                continue

            # 定義から1週間以内の型は除外(実装途中の可能性)
            if self._is_recently_defined(type_def):
                continue

            # 使用回数をカウント
            usage_count = self._count_type_usage_across_project(type_name)

            # 使用回数が0の場合のみ対象
            if usage_count > 0:
                continue

            # レベルを判定
            level = self._determine_type_level(type_def)

            # 理由を判定
            reason = self._determine_unused_reason(type_def)

            # 推奨事項を生成
            recommendation = self._generate_unused_recommendation(type_def, reason)

            # コード位置情報を取得
            context_before, code, context_after = self._extract_context(Path(type_def.file_path), type_def.line_number)
            location = CodeLocation(
                file=Path(type_def.file_path),
                line=type_def.line_number,
                column=0,  # 簡易実装
                code=code,
                context_before=context_before,
                context_after=context_after,
            )

            detail = UnusedTypeDetail(
                type_name=type_name,
                definition=type_def.definition,
                location=location,
                level=level,
                docstring=type_def.docstring,
                reason=reason,
                recommendation=recommendation,
            )
            details.append(detail)

        return details

    def _is_exported_type(self, _type_name: str) -> bool:
        """__all__ でエクスポートされている型かどうかを判定

        Args:
            type_name: 型名

        Returns:
            エクスポートされている場合True
        """
        # 簡易実装:__all__ のチェックは省略
        return False

    def _is_recently_defined(self, _type_def: TypeDefinition) -> bool:
        """定義から1週間以内かどうかを判定

        Args:
            type_def: 型定義

        Returns:
            1週間以内の場合True
        """
        # 簡易実装:常にFalse(ファイルの変更日時チェックは複雑なので省略)
        return False

    def _count_type_usage_across_project(self, type_name: str) -> int:
        """プロジェクト全体での型の使用回数をカウント

        Args:
            type_name: 型名

        Returns:
            使用回数
        """
        count = 0

        # 対象ディレクトリ内の全ファイルを検索
        for target_dir in self.target_dirs:
            for py_file in target_dir.rglob("*.py"):
                if not py_file.is_file():
                    continue

                try:
                    with open(py_file, encoding="utf-8") as f:
                        content = f.read()

                    # 型名が登場する回数をカウント(簡易実装)
                    count += content.count(type_name)

                except (UnicodeDecodeError, OSError):
                    continue

        return count

    def _determine_type_level(self, type_def: TypeDefinition) -> Literal["Level 1", "Level 2", "Level 3"]:
        """型レベルを判定

        Args:
            type_def: 型定義

        Returns:
            型レベル
        """
        level_map: dict[str, Literal["Level 1", "Level 2", "Level 3"]] = {
            "level1": "Level 1",
            "level2": "Level 2",
            "level3": "Level 3",
            "other": "Level 3",  # otherはLevel 3として扱う
        }
        return level_map.get(type_def.level, "Level 1")

    def _determine_unused_reason(
        self, type_def: TypeDefinition
    ) -> Literal["implementation_in_progress", "lack_of_awareness", "future_extensibility"]:
        """未使用の理由を判定

        Args:
            type_def: 型定義

        Returns:
            未使用の理由
        """
        # docstringの内容で判定
        if type_def.docstring and "未使用" in type_def.docstring:
            return "implementation_in_progress"
        elif type_def.docstring and ("将来" in type_def.docstring or "拡張" in type_def.docstring):
            return "future_extensibility"
        else:
            return "lack_of_awareness"

    def _generate_unused_recommendation(self, _type_def: TypeDefinition, reason: str) -> str:
        """未使用型に対する推奨事項を生成

        Args:
            _type_def: 型定義（将来の拡張用、現在は未使用）
            reason: 未使用の理由

        Returns:
            推奨事項
        """
        if reason == "implementation_in_progress":
            return "実装途中の可能性があります。使用箇所を追加するか、設計意図を明確にしてください。"
        elif reason == "future_extensibility":
            return "将来の拡張性を考慮した設計のようです。docstringで意図を明確にしてください。"
        else:
            return "認知不足の可能性があります。既存のprimitive型使用箇所を置き換えることを検討してください。"

    def find_deprecated_typing(self) -> list[DeprecatedTypingDetail]:
        """非推奨typing使用箇所を検出

        Returns:
            検出された問題のリスト
        """
        details: list[DeprecatedTypingDetail] = []

        # 対象ディレクトリ内の全Pythonファイルを処理
        for target_dir in self.target_dirs:
            for py_file in target_dir.rglob("*.py"):
                if not py_file.is_file():
                    continue

                try:
                    with open(py_file, encoding="utf-8") as f:
                        source_code = f.read()

                    tree = ast.parse(source_code, filename=str(py_file))
                    visitor = DeprecatedTypingVisitor(py_file, source_code)
                    visitor.visit(tree)
                    details.extend(visitor.details)

                except (SyntaxError, UnicodeDecodeError):
                    # パースできないファイルはスキップ
                    continue

        return details

    def _get_file_lines(self, file_path: Path) -> list[str]:
        """ファイルの行をキャッシュ付きで取得

        Args:
            file_path: ファイルパス

        Returns:
            ファイルの各行のリスト
        """
        if file_path not in self._file_cache:
            with open(file_path, encoding="utf-8") as f:
                self._file_cache[file_path] = f.readlines()
        return self._file_cache[file_path]

    def _extract_context(
        self, file_path: Path, line: int, before: int = 2, after: int = 2
    ) -> tuple[list[str], str, list[str]]:
        """コードの前後コンテキストを取得

        Args:
            file_path: ファイルパス
            line: 行番号（1始まり）
            before: 前の行数
            after: 後の行数

        Returns:
            (前のコード, 該当行, 後のコード)
        """
        lines = self._get_file_lines(file_path)
        idx = line - 1
        context_before = [lines[i].rstrip() for i in range(max(0, idx - before), idx)]
        code = lines[idx].rstrip()
        context_after = [lines[i].rstrip() for i in range(idx + 1, min(len(lines), idx + 1 + after))]
        return context_before, code, context_after


class PrimitiveUsageVisitor(ast.NodeVisitor):
    """Primitive型使用検出用のAST visitor"""

    # 検出対象のprimitive型
    PRIMITIVE_TYPES = {"str", "int", "float", "bool", "bytes"}

    def __init__(self, file_path: Path, source_code: str):
        """初期化

        Args:
            file_path: 解析対象ファイルパス
            source_code: ソースコード
        """
        self.file_path = file_path
        self.source_code = source_code
        self.details: list[PrimitiveUsageDetail] = []
        self.lines = source_code.splitlines()
        self.class_stack: list[str] = []  # クラス定義のスタック

        # 除外対象の関数名(特殊メソッド等)
        self.excluded_functions = {
            "__init__",
            "__str__",
            "__repr__",
            "__eq__",
            "__hash__",
            "__lt__",
            "__le__",
            "__gt__",
            "__ge__",
            "__call__",
            "__getitem__",
            "__setitem__",
            "__delitem__",
            "__len__",
            "__iter__",
            "__next__",
            "__enter__",
            "__exit__",
            "__bool__",
            "__int__",
            "__float__",
            "__bytes__",
        }

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """関数定義を訪問"""
        # 除外対象の関数はスキップ
        if node.name in self.excluded_functions:
            return

        # クラス内関数はメソッドとして処理
        if self._is_in_class():
            self._check_method_annotations(node)
        else:
            self._check_function_annotations(node)

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """非同期関数定義を訪問"""
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """クラス定義を訪問"""
        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """アノテーション付き代入を訪問（クラス属性）"""
        # クラス内でのみ処理
        if not self._is_in_class():
            return

        # primitive型を抽出(Annotated内も含む)
        primitive_type = self._extract_primitive_type(node.annotation)
        if primitive_type:
            context_before, code, context_after = self._extract_context(node.lineno)
            location = CodeLocation(
                file=self.file_path,
                line=node.lineno,
                column=getattr(node.annotation, "col_offset", 0),
                code=code,
                context_before=context_before,
                context_after=context_after,
            )

            detail = PrimitiveUsageDetail(
                location=location,
                kind="class_attribute",
                primitive_type=primitive_type,
                class_name=self._get_current_class_name(),
            )
            self.details.append(detail)

        self.generic_visit(node)

    def _check_function_annotations(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """関数アノテーションをチェック"""
        # 引数のチェック
        for arg in node.args.args:
            if arg.annotation and isinstance(arg.annotation, ast.Name) and arg.annotation.id in self.PRIMITIVE_TYPES:
                context_before, code, context_after = self._extract_context(arg.lineno or node.lineno)
                location = CodeLocation(
                    file=self.file_path,
                    line=arg.lineno or node.lineno,
                    column=getattr(arg.annotation, "col_offset", 0),
                    code=code,
                    context_before=context_before,
                    context_after=context_after,
                )

                detail = PrimitiveUsageDetail(
                    location=location,
                    kind="function_argument",
                    primitive_type=arg.annotation.id,
                    function_name=node.name,
                )
                self.details.append(detail)

        # 戻り値のチェック
        if node.returns and isinstance(node.returns, ast.Name) and node.returns.id in self.PRIMITIVE_TYPES:
            context_before, code, context_after = self._extract_context(node.lineno)
            location = CodeLocation(
                file=self.file_path,
                line=node.lineno,
                column=getattr(node.returns, "col_offset", 0),
                code=code,
                context_before=context_before,
                context_after=context_after,
            )

            detail = PrimitiveUsageDetail(
                location=location,
                kind="return_type",
                primitive_type=node.returns.id,
                function_name=node.name,
            )
            self.details.append(detail)

    def _check_method_annotations(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """メソッドアノテーションをチェック"""
        # __init__以外の場合のみチェック(__init__は初期化なので許容)
        if node.name != "__init__":
            self._check_function_annotations(node)

    def _is_in_class(self) -> bool:
        """現在クラス定義内かどうかを判定"""
        return len(self.class_stack) > 0

    def _get_current_class_name(self) -> str | None:
        """現在のクラス名を取得"""
        return self.class_stack[-1] if self.class_stack else None

    def _extract_primitive_type(self, annotation: ast.expr) -> str | None:
        """アノテーションからprimitive型を抽出

        Args:
            annotation: 型アノテーションのASTノード

        Returns:
            primitive型名、検出されない場合はNone

        Note:
            以下のパターンを検出:
            - 直接のprimitive型: str, int, float, bool, bytes
            - Annotated内のprimitive型: Annotated[str, ...]
            - NewType内のprimitive型:
              NewType('X', str) または NewType('X', Annotated[str, ...])
        """
        # パターン1: 直接のprimitive型(ast.Name)
        if isinstance(annotation, ast.Name) and annotation.id in self.PRIMITIVE_TYPES:
            return annotation.id

        # パターン2: Annotated[primitive, ...] 形式
        if isinstance(annotation, ast.Subscript):
            # Annotated[...]の場合
            if isinstance(annotation.value, ast.Name) and annotation.value.id == "Annotated":
                # Annotatedの第1引数を取得
                if isinstance(annotation.slice, ast.Tuple) and annotation.slice.elts:
                    first_arg = annotation.slice.elts[0]
                    if isinstance(first_arg, ast.Name) and first_arg.id in self.PRIMITIVE_TYPES:
                        return first_arg.id

            # NewType('X', primitive) または NewType('X', Annotated[...]) 形式
            # NewTypeはCall/ノードとして解析されるため、ここでは検出しない

        # パターン3: NewType(...) 形式(ast.Call)
        if isinstance(annotation, ast.Call):
            # NewType('X', base_type)の場合
            if isinstance(annotation.func, ast.Name) and annotation.func.id == "NewType":
                # NewType定義はprimitive使用としてカウントしない(PEP 484準拠パターン)
                # 例: UserId = NewType('UserId', str) → primitive使用ではない
                return None

        return None

    def _extract_context(self, line: int, before: int = 2, after: int = 2) -> tuple[list[str], str, list[str]]:
        """コードの前後コンテキストを取得

        Args:
            line: 行番号（1始まり）
            before: 前の行数
            after: 後の行数

        Returns:
            (前のコード, 該当行, 後のコード)
        """
        idx = line - 1
        context_before = [self.lines[i] for i in range(max(0, idx - before), idx)]
        code = self.lines[idx] if idx < len(self.lines) else ""
        context_after = [self.lines[i] for i in range(idx + 1, min(len(self.lines), idx + 1 + after))]
        return context_before, code, context_after


class DeprecatedTypingVisitor(ast.NodeVisitor):
    """非推奨typing使用検出用のAST visitor"""

    # 非推奨のtyping要素と推奨される代替構文
    DEPRECATED_MAPPING = {
        "List": "list",
        "Dict": "dict",
        "Set": "set",
        "Tuple": "tuple",
        "FrozenSet": "frozenset",
        "Union": "X | Y",
        "Optional": "X | None",
        "NewType": "Annotated[X, ...]",
        "TypeVar": "class X[T]:",
    }

    def __init__(self, file_path: Path, source_code: str):
        """初期化

        Args:
            file_path: 解析対象ファイルパス
            source_code: ソースコード
        """
        self.file_path = file_path
        self.source_code = source_code
        self.details: list[DeprecatedTypingDetail] = []
        self.lines = source_code.splitlines()
        self.imports: dict[str, str] = {}  # deprecated -> recommended

    def visit_Import(self, node: ast.Import) -> None:
        """Import文を訪問"""
        for alias in node.names:
            if alias.name == "typing":
                # "import typing" はそのまま使用可能
                continue
            elif alias.name.startswith("typing."):
                # "import typing.List" などの個別import
                typing_name = alias.name.split(".", 1)[1]
                if typing_name in self.DEPRECATED_MAPPING:
                    as_name = alias.asname or typing_name
                    self.imports[as_name] = self.DEPRECATED_MAPPING[typing_name]

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """From import文を訪問"""
        if node.module == "typing":
            for alias in node.names:
                typing_name = alias.name
                if typing_name in self.DEPRECATED_MAPPING:
                    as_name = alias.asname or typing_name
                    self.imports[as_name] = self.DEPRECATED_MAPPING[typing_name]

        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """名前ノードを訪問"""
        if node.id in self.imports:
            # 非推奨typingの使用を検出

            # 同じ行に複数の使用がある場合は重複を避ける
            if not hasattr(self, "_processed_lines"):
                self._processed_lines: set[int] = set()

            if node.lineno not in self._processed_lines:
                self._processed_lines.add(node.lineno)

                context_before, code, context_after = self._extract_context(node.lineno)
                location = CodeLocation(
                    file=self.file_path,
                    line=node.lineno,
                    column=getattr(node, "col_offset", 0),
                    code=code,
                    context_before=context_before,
                    context_after=context_after,
                )

                # この行で使用されている非推奨typingを集める
                deprecated_imports = []
                for dep, rec in self.imports.items():
                    if dep in code:
                        deprecated_imports.append({"deprecated": dep, "recommended": rec})

                if deprecated_imports:
                    suggestion = self._generate_migration_suggestion(deprecated_imports)

                    detail = DeprecatedTypingDetail(
                        location=location,
                        imports=deprecated_imports,
                        suggestion=suggestion,
                    )
                    self.details.append(detail)

        self.generic_visit(node)

    def _generate_migration_suggestion(self, imports: list[dict[str, str]]) -> str:
        """移行推奨文を生成

        Args:
            imports: 非推奨importのリスト

        Returns:
            推奨文
        """
        examples = []
        for imp in imports:
            dep = imp["deprecated"]
            rec = imp["recommended"]
            if dep == "List":
                examples.append(f"{dep}[str] → {rec}[str]")
            elif dep == "Dict":
                examples.append(f"{dep}[str, int] → {rec}[str, int]")
            elif dep == "Optional":
                examples.append(f"{dep}[str] → str | None")
            elif dep == "Union":
                examples.append(f"{dep}[str, int] → str | int")
            else:
                examples.append(f"{dep} → {rec}")

        return f"Python 3.13標準構文への移行を推奨します: {'; '.join(examples)}"

    def _extract_context(self, line: int, before: int = 2, after: int = 2) -> tuple[list[str], str, list[str]]:
        """コードの前後コンテキストを取得

        Args:
            line: 行番号（1始まり）
            before: 前の行数
            after: 後の行数

        Returns:
            (前のコード, 該当行, 後のコード)
        """
        idx = line - 1
        context_before = [self.lines[i] for i in range(max(0, idx - before), idx)]
        code = self.lines[idx] if idx < len(self.lines) else ""
        context_after = [self.lines[i] for i in range(idx + 1, min(len(self.lines), idx + 1 + after))]
        return context_before, code, context_after


class TypeUsageVisitor(ast.NodeVisitor):
    """型使用例検出用のAST visitor"""

    def __init__(self, target_type: str, file_path: Path, source_code: str):
        """初期化

        Args:
            target_type: 検出対象の型名
            file_path: 解析対象ファイルパス
            source_code: ソースコード
        """
        self.target_type = target_type
        self.file_path = file_path
        self.source_code = source_code
        self.usages: list[TypeUsageExample] = []
        self.lines = source_code.splitlines()

    def generic_visit(self, node: ast.AST) -> None:
        """ASTトラバーサル中に各子ノードに親ノードを設定"""
        for child in ast.iter_child_nodes(node):
            child._parent = node
        super().generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """名前ノードを訪問"""
        if node.id == self.target_type:
            context_before, code, context_after = self._extract_context(node.lineno)
            location = CodeLocation(
                file=self.file_path,
                line=node.lineno,
                column=getattr(node, "col_offset", 0),
                code=code,
                context_before=context_before,
                context_after=context_after,
            )

            # 使用種類を判定(簡易実装)
            usage_kind = self._determine_usage_kind(node)

            usage = TypeUsageExample(location=location, context=code.strip(), kind=usage_kind)
            self.usages.append(usage)

        self.generic_visit(node)

    def _determine_usage_kind(
        self, node: ast.Name
    ) -> Literal["function_argument", "return_type", "variable_annotation", "class_attribute"]:
        """使用種類を判定

        Args:
            node: Name/ノード

        Returns:
            使用種類
        """
        # 簡易実装:親ノードの種類で判定
        parent = getattr(node, "_parent", None)
        if parent:
            if isinstance(parent, ast.arg):
                return "function_argument"
            elif isinstance(parent, ast.Return):
                return "return_type"
            elif isinstance(parent, ast.AnnAssign):
                return "class_attribute"

        return "variable_annotation"

    def _extract_context(self, line: int, before: int = 2, after: int = 2) -> tuple[list[str], str, list[str]]:
        """コードの前後コンテキストを取得

        Args:
            line: 行番号（1始まり）
            before: 前の行数
            after: 後の行数

        Returns:
            (前のコード, 該当行, 後のコード)
        """
        idx = line - 1
        context_before = [self.lines[i] for i in range(max(0, idx - before), idx)]
        code = self.lines[idx] if idx < len(self.lines) else ""
        context_after = [self.lines[i] for i in range(idx + 1, min(len(self.lines), idx + 1 + after))]
        return context_before, code, context_after
