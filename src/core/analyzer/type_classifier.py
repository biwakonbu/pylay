"""
型定義の分類ロジック

Pythonソースコードから型定義を検出し、Level 1/2/3に分類します。
"""

import ast
import re
from pathlib import Path
from typing import Literal

from src.core.analyzer.type_level_models import TypeDefinition


class TypeClassifier:
    """型定義を分類するクラス"""

    # 検出パターン
    LEVEL1_PATTERN = re.compile(r"^\s*type\s+(\w+)\s*=\s*(.+)$", re.MULTILINE)
    LEVEL2_PATTERN = re.compile(
        r"^\s*type\s+(\w+)\s*=\s*Annotated\[.*AfterValidator.*\]", re.MULTILINE
    )
    # 新パターン: NewType定義
    NEWTYPE_PATTERN = re.compile(
        r"^\s*(\w+)\s*=\s*NewType\(['\"](\w+)['\"]\s*,\s*(\w+)\)", re.MULTILINE
    )
    # ファクトリ関数パターン
    FACTORY_PATTERN = re.compile(
        r"^\s*def\s+(create_(\w+)|(\w+))\s*\([^)]*\)\s*->\s*(\w+):", re.MULTILINE
    )
    VALIDATE_CALL_PATTERN = re.compile(
        r"@validate_call\s+def\s+(\w+)\s*\([^)]*\)\s*->\s*(\w+):", re.MULTILINE
    )
    LEVEL3_PATTERN = re.compile(r"^\s*class\s+(\w+)\(.*BaseModel.*\):", re.MULTILINE)
    OTHER_CLASS_PATTERN = re.compile(
        r"^\s*class\s+(\w+)(?:\((?!.*BaseModel).*\))?:", re.MULTILINE
    )
    OTHER_DATACLASS_PATTERN = re.compile(
        r"@dataclass.*\n\s*class\s+(\w+)", re.MULTILINE
    )
    OTHER_TYPEDDICT_PATTERN = re.compile(
        r"^\s*class\s+(\w+)\(TypedDict\):", re.MULTILINE
    )

    # docstring抽出パターン
    DOCSTRING_TRIPLE_PATTERN = re.compile(r'"""(.*?)"""', re.DOTALL)
    DOCSTRING_SINGLE_PATTERN = re.compile(r"'''(.*?)'''", re.DOTALL)

    def classify_file(self, file_path: Path) -> list[TypeDefinition]:
        """ファイル内の型定義を分類

        Args:
            file_path: 解析対象のファイルパス

        Returns:
            TypeDefinitionのリスト
        """
        if not file_path.exists() or not file_path.is_file():
            return []

        try:
            with open(file_path, encoding="utf-8") as f:
                source_code = f.read()
        except Exception:
            return []

        type_definitions: list[TypeDefinition] = []

        # AST解析とパターンマッチングを併用
        try:
            tree = ast.parse(source_code)
            type_definitions.extend(
                self._classify_with_ast(tree, file_path, source_code)
            )
        except SyntaxError:
            pass

        # パターンマッチングで追加の型定義を検出
        type_definitions.extend(self._classify_with_regex(source_code, file_path))

        # 重複除去（同じ名前・ファイル・行番号の型定義）
        seen = set()
        unique_types = []
        for td in type_definitions:
            key = (td.name, td.file_path, td.line_number)
            if key not in seen:
                seen.add(key)
                unique_types.append(td)

        return unique_types

    def _classify_with_ast(
        self, tree: ast.AST, file_path: Path, source_code: str
    ) -> list[TypeDefinition]:
        """ASTを使用した型定義の分類

        Args:
            tree: ASTツリー
            file_path: ファイルパス
            source_code: ソースコード

        Returns:
            TypeDefinitionのリスト
        """
        type_definitions: list[TypeDefinition] = []

        for node in ast.walk(tree):
            # ClassDefノードを処理
            if isinstance(node, ast.ClassDef):
                td = self._classify_class_def(node, file_path, source_code)
                if td:
                    type_definitions.append(td)

            # type文（Python 3.12+）
            elif isinstance(node, ast.TypeAlias):
                td = self._classify_type_alias(node, file_path, source_code)
                if td:
                    type_definitions.append(td)

            # 代入形式のtypeエイリアス（従来構文）
            elif isinstance(node, ast.Assign):
                td = self._classify_assign_alias(node, file_path, source_code)
                if td:
                    type_definitions.append(td)

        return type_definitions

    def _classify_class_def(
        self, node: ast.ClassDef, file_path: Path, source_code: str
    ) -> TypeDefinition | None:
        """ClassDefノードを分類

        Args:
            node: ClassDefノード
            file_path: ファイルパス
            source_code: ソースコード

        Returns:
            TypeDefinition（該当しない場合はNone）
        """
        # BaseModelを継承しているか確認
        is_basemodel = any(self._is_basemodel_base(base) for base in node.bases)

        # dataclassデコレータがあるか確認
        is_dataclass = any(
            self._is_dataclass_decorator(dec) for dec in node.decorator_list
        )

        # TypedDictを継承しているか確認
        is_typeddict = any(self._is_typeddict_base(base) for base in node.bases)

        # docstringを取得
        docstring = ast.get_docstring(node)

        # 型定義のコードを抽出
        definition = self._extract_definition(node, source_code)

        if is_basemodel:
            level = "level3"
            category = "basemodel"
        elif is_dataclass:
            level = "other"
            category = "dataclass"
        elif is_typeddict:
            level = "other"
            category = "typeddict"
        else:
            level = "other"
            category = "class"

        # docstringから制御フィールドを抽出
        target_level = self._extract_target_level(docstring)
        keep_as_is = self._extract_keep_as_is(docstring)

        return TypeDefinition(
            name=node.name,
            level=level,
            file_path=str(file_path),
            line_number=node.lineno,
            definition=definition,
            category=category,
            docstring=docstring,
            has_docstring=docstring is not None,
            docstring_lines=len(docstring.splitlines()) if docstring else 0,
            target_level=target_level,
            keep_as_is=keep_as_is,
        )

    def _classify_type_alias(
        self, node: ast.TypeAlias, file_path: Path, source_code: str
    ) -> TypeDefinition | None:
        """TypeAliasノードを分類

        Args:
            node: TypeAliasノード
            file_path: ファイルパス
            source_code: ソースコード

        Returns:
            TypeDefinition（該当しない場合はNone）
        """
        # type文の名前を取得
        if isinstance(node.name, ast.Name):
            type_name = node.name.id
        else:
            return None

        # 型定義のコードを抽出
        definition = self._extract_definition(node, source_code)

        # Annotated型かつAfterValidatorを含むか確認
        is_level2 = self._is_annotated_with_validator(node.value)

        if is_level2:
            level = "level2"
            category = "annotated"
        else:
            level = "level1"
            category = "type_alias"

        # docstringを抽出（type文の直後のコメントまたは文字列）
        docstring = self._extract_type_alias_docstring(node, source_code)

        # docstringから制御フィールドを抽出
        target_level = self._extract_target_level(docstring)
        keep_as_is = self._extract_keep_as_is(docstring)

        return TypeDefinition(
            name=type_name,
            level=level,
            file_path=str(file_path),
            line_number=node.lineno,
            definition=definition,
            category=category,
            docstring=docstring,
            has_docstring=docstring is not None,
            docstring_lines=len(docstring.splitlines()) if docstring else 0,
            target_level=target_level,
            keep_as_is=keep_as_is,
        )

    def _classify_assign_alias(
        self, node: ast.Assign, file_path: Path, source_code: str
    ) -> TypeDefinition | None:
        """代入形式の型エイリアスを分類

        Args:
            node: Assignノード
            file_path: ファイルパス
            source_code: ソースコード

        Returns:
            TypeDefinition（該当しない場合はNone）
        """
        # 単一ターゲットのName代入のみを対象
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            return None

        type_name = node.targets[0].id

        # 型定義のコードを抽出
        definition = self._extract_definition(node, source_code)

        # Annotated型かつAfterValidatorを含むか確認
        is_level2 = self._is_annotated_with_validator(node.value)

        if is_level2:
            level = "level2"
            category = "annotated"
        else:
            level = "level1"
            category = "type_alias"

        # docstringを抽出（代入文の直後のコメントまたは文字列）
        docstring = self._extract_docstring_near_line(source_code, node.lineno + 1)

        # docstringから制御フィールドを抽出
        target_level = self._extract_target_level(docstring)
        keep_as_is = self._extract_keep_as_is(docstring)

        return TypeDefinition(
            name=type_name,
            level=level,
            file_path=str(file_path),
            line_number=node.lineno,
            definition=definition,
            category=category,
            docstring=docstring,
            has_docstring=docstring is not None,
            docstring_lines=len(docstring.splitlines()) if docstring else 0,
            target_level=target_level,
            keep_as_is=keep_as_is,
        )

    def _classify_with_regex(
        self, source_code: str, file_path: Path
    ) -> list[TypeDefinition]:
        """正規表現を使用した型定義の分類

        Args:
            source_code: ソースコード
            file_path: ファイルパス

        Returns:
            TypeDefinitionのリスト
        """
        type_definitions: list[TypeDefinition] = []

        # NewType + ファクトリ関数パターンを検出（新パターン）
        newtype_with_factory = self._detect_newtype_with_factory(source_code, file_path)
        type_definitions.extend(newtype_with_factory)

        # Level 2: Annotated + AfterValidator（旧パターン）
        for match in self.LEVEL2_PATTERN.finditer(source_code):
            type_name = match.group(1)
            line_number = source_code[: match.start()].count("\n") + 1
            definition = match.group(0).strip()

            # docstringを抽出
            docstring = self._extract_docstring_near_line(source_code, line_number)

            type_definitions.append(
                TypeDefinition(
                    name=type_name,
                    level="level2",
                    file_path=str(file_path),
                    line_number=line_number,
                    definition=definition,
                    category="annotated",
                    docstring=docstring,
                    has_docstring=docstring is not None,
                    docstring_lines=len(docstring.splitlines()) if docstring else 0,
                )
            )

        # Level 1: type エイリアス（Level 2以外）
        for match in self.LEVEL1_PATTERN.finditer(source_code):
            type_name = match.group(1)
            line_number = source_code[: match.start()].count("\n") + 1
            definition = match.group(0).strip()

            # Level 2として既に検出されていないか確認
            if not any(
                td.name == type_name and td.line_number == line_number
                for td in type_definitions
            ):
                # docstringを抽出
                docstring = self._extract_docstring_near_line(source_code, line_number)

                type_definitions.append(
                    TypeDefinition(
                        name=type_name,
                        level="level1",
                        file_path=str(file_path),
                        line_number=line_number,
                        definition=definition,
                        category="type_alias",
                        docstring=docstring,
                        has_docstring=docstring is not None,
                        docstring_lines=len(docstring.splitlines()) if docstring else 0,
                    )
                )

        return type_definitions

    # ========================================
    # ヘルパーメソッド
    # ========================================

    def _is_basemodel_base(self, base: ast.expr) -> bool:
        """BaseModelを継承しているか確認"""
        if isinstance(base, ast.Name) and base.id == "BaseModel":
            return True
        if isinstance(base, ast.Attribute) and base.attr == "BaseModel":
            return True
        return False

    def _is_dataclass_decorator(self, decorator: ast.expr) -> bool:
        """dataclassデコレータか確認"""
        if isinstance(decorator, ast.Name) and decorator.id == "dataclass":
            return True
        if isinstance(decorator, ast.Attribute) and decorator.attr == "dataclass":
            return True
        return False

    def _is_typeddict_base(self, base: ast.expr) -> bool:
        """TypedDictを継承しているか確認"""
        if isinstance(base, ast.Name) and base.id == "TypedDict":
            return True
        if isinstance(base, ast.Attribute) and base.attr == "TypedDict":
            return True
        return False

    def _is_annotated_with_validator(self, node: ast.expr) -> bool:
        """Annotated型かつAfterValidatorを含むか確認"""
        if isinstance(node, ast.Subscript):
            # Annotated[...]の形式
            if isinstance(node.value, ast.Name) and node.value.id == "Annotated":
                # スライス部分を確認
                if isinstance(node.slice, ast.Tuple):
                    for elt in node.slice.elts:
                        if self._contains_after_validator(elt):
                            return True
        return False

    def _contains_after_validator(self, node: ast.expr) -> bool:
        """AfterValidatorを含むか確認"""
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "AfterValidator":
                return True
        return False

    def _extract_definition(self, node: ast.AST, source_code: str) -> str:
        """ノードから型定義のコードを抽出"""
        try:
            lines = source_code.splitlines()
            if (
                hasattr(node, "lineno")
                and hasattr(node, "end_lineno")
                and hasattr(node, "end_lineno")
                and getattr(node, "end_lineno") is not None
            ):
                # hastattrで確認済みなので安全にアクセス可能
                start = getattr(node, "lineno") - 1
                end = getattr(node, "end_lineno")
                return "\n".join(lines[start:end])
        except Exception:
            pass
        return ""

    def _extract_type_alias_docstring(
        self, node: ast.TypeAlias, source_code: str
    ) -> str | None:
        """type文のdocstringを抽出"""
        # type文の直後の行からdocstringを探す
        if hasattr(node, "end_lineno") and node.end_lineno is not None:
            return self._extract_docstring_near_line(source_code, node.end_lineno + 1)
        return None

    def _extract_docstring_near_line(
        self, source_code: str, line_number: int
    ) -> str | None:
        """指定行の近くのdocstringを抽出

        Args:
            source_code: ソースコード
            line_number: 検索開始行番号（1始まり、ASTのlinenoと同じ）

        Returns:
            抽出されたdocstring（見つからない場合はNone）
        """
        lines = source_code.splitlines()
        # line_numberは1始まりなので、0始まりのインデックスに変換
        start_index = line_number - 1
        if start_index >= len(lines):
            return None

        # 次の数行を確認
        for i in range(start_index, min(start_index + 3, len(lines))):
            line = lines[i].strip()

            # トリプルクォートで始まる
            if line.startswith('"""') or line.startswith("'''"):
                quote = '"""' if line.startswith('"""') else "'''"

                # 同じ行で終わる
                if line.count(quote) >= 2:
                    return line.strip(quote).strip()

                # 複数行のdocstring
                docstring_lines = [line.lstrip(quote)]
                for j in range(i + 1, len(lines)):
                    if quote in lines[j]:
                        docstring_lines.append(lines[j].split(quote)[0])
                        return "\n".join(docstring_lines).strip()
                    docstring_lines.append(lines[j])

        return None

    def _extract_target_level(
        self, docstring: str | None
    ) -> Literal["level1", "level2", "level3"] | None:
        """docstringから@target-levelを抽出

        Args:
            docstring: docstring

        Returns:
            目標レベル（level1/level2/level3）、指定がない場合はNone
        """
        if not docstring:
            return None

        # @target-level: level1/level2/level3 のパターン
        match = re.search(r"@target-level:\s*(level[123])", docstring)
        if match:
            level = match.group(1)
            # 型ガードで検証
            if level == "level1":
                return "level1"
            elif level == "level2":
                return "level2"
            elif level == "level3":
                return "level3"

        return None

    def _extract_keep_as_is(self, docstring: str | None) -> bool:
        """docstringから@keep-as-isを抽出

        Args:
            docstring: docstring

        Returns:
            @keep-as-is: true の場合True、それ以外False
        """
        if not docstring:
            return False

        # @keep-as-is: true のパターン
        match = re.search(r"@keep-as-is:\s*(true|True|yes|Yes)", docstring)
        return match is not None

    def _detect_newtype_with_factory(
        self, source_code: str, file_path: Path
    ) -> list[TypeDefinition]:
        """NewType + ファクトリ関数パターンを検出（PEP 484準拠パターン）

        Args:
            source_code: ソースコード
            file_path: ファイルパス

        Returns:
            検出されたLevel 2型定義のリスト
        """
        type_definitions: list[TypeDefinition] = []

        # NewType定義を収集
        newtype_defs: dict[
            str, tuple[int, str, str]
        ] = {}  # {type_name: (line, definition, base_type)}
        for match in self.NEWTYPE_PATTERN.finditer(source_code):
            var_name = match.group(1)
            type_name = match.group(2)
            base_type = match.group(3)
            line_number = source_code[: match.start()].count("\n") + 1
            definition = match.group(0).strip()

            # 変数名と型名が一致する場合のみ検出（UserId = NewType('UserId', str)）
            if var_name == type_name:
                newtype_defs[type_name] = (line_number, definition, base_type)

        # ファクトリ関数を収集
        factory_funcs: dict[str, int] = {}  # {type_name: line_number}

        # パターン1: create_* 関数
        for match in self.FACTORY_PATTERN.finditer(source_code):
            full_func_name = match.group(1)
            # create_user_id -> UserId
            if full_func_name.startswith("create_"):
                type_name_snake = full_func_name.replace("create_", "")
                # snake_case -> PascalCase
                type_name = "".join(
                    word.capitalize() for word in type_name_snake.split("_")
                )
            else:
                type_name = full_func_name

            return_type = match.group(4)
            if return_type == type_name:
                line_number = source_code[: match.start()].count("\n") + 1
                factory_funcs[type_name] = line_number

        # パターン2: @validate_call + 同名関数
        for match in self.VALIDATE_CALL_PATTERN.finditer(source_code):
            func_name = match.group(1)
            return_type = match.group(2)
            # 関数名と返り値型が一致する場合（UserId関数 -> UserId型）
            if func_name == return_type:
                line_number = source_code[: match.start()].count("\n") + 1
                factory_funcs[func_name] = line_number

        # NewTypeとファクトリ関数のペアを検出
        for type_name, (newtype_line, definition, base_type) in newtype_defs.items():
            if type_name in factory_funcs:
                # ペアになっている場合、Level 2として登録
                docstring = self._extract_docstring_near_line(source_code, newtype_line)

                type_definitions.append(
                    TypeDefinition(
                        name=type_name,
                        level="level2",
                        file_path=str(file_path),
                        line_number=newtype_line,
                        definition=definition,
                        category="newtype_with_factory",
                        docstring=docstring,
                        has_docstring=docstring is not None,
                        docstring_lines=len(docstring.splitlines()) if docstring else 0,
                    )
                )

        return type_definitions
