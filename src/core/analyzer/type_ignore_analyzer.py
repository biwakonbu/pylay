"""
型無視（type: ignore）の原因行特定分析

# type: ignore コメントが使用されている箇所について、
なぜ型チェックを回避する必要があったのか、その原因となっているコードを特定します。
"""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from src.core.schemas.pylay_config import PylayConfig
from src.core.schemas.types import FilePath, LineNumber

# 優先度の型定義
type Priority = Literal["HIGH", "MEDIUM", "LOW"]


class CodeContext(BaseModel):
    """コードコンテキスト情報"""

    before_lines: list[str] = Field(default_factory=list, description="前後の行")
    target_line: str = Field(description="対象行")
    after_lines: list[str] = Field(default_factory=list, description="後の行")
    line_number: LineNumber = Field(description="行番号")


class TypeIgnoreIssue(BaseModel):
    """type: ignore の問題箇所の情報"""

    file_path: FilePath = Field(description="ファイルパス")
    line_number: LineNumber = Field(description="行番号")
    ignore_type: str = Field(
        description="type: ignore の種類（e.g., call-arg, arg-type）"
    )
    cause: str = Field(description="原因の要約")
    detail: str = Field(description="詳細な説明")
    code_context: CodeContext = Field(description="コードコンテキスト")
    priority: Priority = Field(description="優先度（HIGH/MEDIUM/LOW）")
    solutions: list[str] = Field(default_factory=list, description="解決策の提案")

    class Config:
        """Pydantic設定"""

        frozen = True


class TypeIgnoreSummary(BaseModel):
    """type: ignore 全体のサマリー情報"""

    total_count: int = Field(description="type: ignore の総数")
    high_priority_count: int = Field(description="HIGH優先度の数")
    medium_priority_count: int = Field(description="MEDIUM優先度の数")
    low_priority_count: int = Field(description="LOW優先度の数")
    by_category: dict[str, int] = Field(
        default_factory=dict, description="カテゴリ別の数"
    )


class TypeIgnoreAnalyzer:
    """type: ignore の原因分析を行うアナライザー"""

    def __init__(self) -> None:
        """アナライザーを初期化"""
        self._type_error_cache: dict[str, list[dict[str, str]]] = {}

    def analyze_file(self, file_path: str | Path) -> list[TypeIgnoreIssue]:
        """
        ファイル内の type: ignore を分析

        Args:
            file_path: 解析対象のファイルパス

        Returns:
            検出された type: ignore 問題のリスト
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"ファイルが存在しません: {file_path}")

        # ファイルからtype: ignoreを検出
        type_ignore_lines = self._detect_type_ignore(file_path)

        if not type_ignore_lines:
            return []

        # mypy/pyrightで型エラー情報を取得
        type_errors = self._get_type_errors(file_path)

        # 各type: ignoreについて原因を特定
        issues = []
        for line_num, ignore_type in type_ignore_lines:
            issue = self._analyze_type_ignore(
                file_path, line_num, ignore_type, type_errors
            )
            issues.append(issue)

        return issues

    def analyze_project(self, project_path: str | Path) -> list[TypeIgnoreIssue]:
        """
        プロジェクト全体の type: ignore を分析

        pyproject.toml の [tool.pylay] exclude_patterns 設定を使用して
        不要なファイル（.venv, tests, __pycache__ 等）を除外します。

        Args:
            project_path: プロジェクトのルートパス

        Returns:
            検出された type: ignore 問題のリスト
        """
        project_path = Path(project_path)
        all_issues = []

        # pyproject.tomlから除外パターンを読み込み
        try:
            config = PylayConfig.from_pyproject_toml(project_path)
            exclude_patterns = config.exclude_patterns
        except (FileNotFoundError, ValueError):
            # pyproject.tomlが見つからない場合はデフォルトの除外パターンを使用
            exclude_patterns = [
                "**/tests/**",
                "**/*_test.py",
                "**/__pycache__/**",
                "**/.venv/**",
                "**/node_modules/**",
                "**/dist/**",
                "**/build/**",
            ]

        # Pythonファイルを再帰的に検索（除外パターンでフィルタリング）
        analyzed_count = 0
        excluded_count = 0
        for py_file in project_path.rglob("*.py"):
            # 除外パターンに一致するかチェック
            if self._should_exclude(py_file, project_path, exclude_patterns):
                excluded_count += 1
                continue

            analyzed_count += 1
            try:
                issues = self.analyze_file(py_file)
                all_issues.extend(issues)
            except Exception as e:
                print(f"警告: {py_file} の解析中にエラー: {e}")

        import sys

        print(
            f"解析対象: {analyzed_count}ファイル, 除外: {excluded_count}ファイル",
            file=sys.stderr,
        )

        return all_issues

    def _should_exclude(
        self, file_path: Path, project_root: Path, patterns: list[str]
    ) -> bool:
        """
        ファイルが除外パターンに一致するかチェック

        Args:
            file_path: チェック対象のファイルパス
            project_root: プロジェクトルート
            patterns: 除外パターンのリスト

        Returns:
            除外すべき場合True
        """
        try:
            # プロジェクトルートからの相対パスを取得
            rel_path = file_path.relative_to(project_root)
        except ValueError:
            # プロジェクト外のファイルは除外
            return True

        # POSIX形式のパス文字列に変換
        rel_path_str = rel_path.as_posix()

        # 各パターンに対してマッチングをチェック
        import fnmatch

        for pattern in patterns:
            # パターンを簡易的に処理
            if pattern.startswith("**/"):
                # **/pattern のケース
                suffix = pattern[3:]
                if suffix.endswith("/**"):
                    # **/tests/** -> tests/ を含むパス
                    dir_name = suffix[:-3]
                    if f"/{dir_name}/" in rel_path_str or rel_path_str.startswith(
                        dir_name + "/"
                    ):
                        return True
                elif "/" not in suffix and "*" not in suffix:
                    # **/__pycache__ -> __pycache__ をパスの一部として含む
                    # (ワイルドカードなし)
                    if (
                        f"/{suffix}/" in rel_path_str
                        or rel_path_str.startswith(suffix + "/")
                        or rel_path_str == suffix
                    ):
                        return True
                else:
                    # **/*_test.py -> _test.py で終わるファイル
                    # (ワイルドカード含む)
                    if fnmatch.fnmatch(rel_path_str.split("/")[-1], suffix):
                        return True
            elif pattern.endswith("/**"):
                # tests/** -> tests/ で始まるパス
                prefix = pattern[:-3]
                if rel_path_str.startswith(prefix + "/") or rel_path_str == prefix:
                    return True
            else:
                # 通常のパターン（ワイルドカード含む）
                if fnmatch.fnmatch(rel_path_str, pattern):
                    return True

        return False

    def generate_summary(self, issues: list[TypeIgnoreIssue]) -> TypeIgnoreSummary:
        """
        サマリー情報を生成

        Args:
            issues: type: ignore 問題のリスト

        Returns:
            サマリー情報
        """
        high_count = sum(1 for i in issues if i.priority == "HIGH")
        medium_count = sum(1 for i in issues if i.priority == "MEDIUM")
        low_count = sum(1 for i in issues if i.priority == "LOW")

        # カテゴリ別集計
        by_category: dict[str, int] = {}
        for issue in issues:
            category = issue.ignore_type or "unknown"
            by_category[category] = by_category.get(category, 0) + 1

        return TypeIgnoreSummary(
            total_count=len(issues),
            high_priority_count=high_count,
            medium_priority_count=medium_count,
            low_priority_count=low_count,
            by_category=by_category,
        )

    def _detect_type_ignore(self, file_path: Path) -> list[tuple[int, str]]:
        """
        ファイルから type: ignore コメントを検出

        Args:
            file_path: 解析対象のファイルパス

        Returns:
            (行番号, ignore種別) のリスト
        """
        type_ignore_pattern = re.compile(r"#\s*type:\s*ignore(?:\[([^\]]+)\])?")
        results = []

        with open(file_path, encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                match = type_ignore_pattern.search(line)
                if match:
                    ignore_type = match.group(1) or "general"
                    results.append((line_num, ignore_type))

        return results

    def _get_type_errors(self, file_path: Path) -> list[dict[str, str]]:
        """
        mypy/pyrightを実行して型エラー情報を取得

        Args:
            file_path: 解析対象のファイルパス

        Returns:
            型エラー情報のリスト
        """
        # キャッシュチェック
        cache_key = str(file_path)
        if cache_key in self._type_error_cache:
            return self._type_error_cache[cache_key]

        errors = []

        # mypyを実行（uvが利用可能ならuv経由、なければ直接実行）
        # まずuv経由でmypyを実行
        cmd = ["uv", "run", "mypy", "--no-error-summary", str(file_path)]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            errors.extend(self._parse_mypy_output(result.stdout + result.stderr))
        except FileNotFoundError:
            # uvコマンドが見つからない場合はmypyを直接実行
            cmd_fallback = ["mypy", "--no-error-summary", str(file_path)]
            try:
                result = subprocess.run(
                    cmd_fallback,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                errors.extend(self._parse_mypy_output(result.stdout + result.stderr))
            except FileNotFoundError:
                # mypy自体が見つからない場合は警告を出す
                import sys

                print(
                    "警告: mypyが見つかりません。型エラー情報を取得できません。",
                    file=sys.stderr,
                )
        except subprocess.TimeoutExpired:
            pass

        # キャッシュに保存
        self._type_error_cache[cache_key] = errors
        return errors

    def _parse_mypy_output(self, output: str) -> list[dict[str, str]]:
        """
        mypyの出力から型エラー情報を抽出

        Args:
            output: mypyの出力

        Returns:
            型エラー情報のリスト
        """
        errors = []
        # mypy出力形式: file_path:line:col: error: message [error-type]
        error_pattern = re.compile(
            r"^(.+?):(\d+):(?:\d+:)?\s*(error|warning|note):\s*(.+?)(?:\s*\[([^\]]+)\])?$",
            re.MULTILINE,
        )

        for match in error_pattern.finditer(output):
            errors.append(
                {
                    "file": match.group(1),
                    "line": match.group(2),
                    "severity": match.group(3),
                    "message": match.group(4),
                    "error_type": match.group(5) or "unknown",
                }
            )

        return errors

    def _analyze_type_ignore(
        self,
        file_path: Path,
        line_num: int,
        ignore_type: str,
        type_errors: list[dict[str, str]],
    ) -> TypeIgnoreIssue:
        """
        個別の type: ignore を分析

        Args:
            file_path: ファイルパス
            line_num: 行番号
            ignore_type: ignore種別
            type_errors: 型エラー情報のリスト

        Returns:
            type: ignore 問題情報
        """
        # コードコンテキストを取得
        code_context = self._get_code_context(file_path, line_num)

        # 該当行の型エラーを検索（ファイルパスとseverity=errorも確認）
        resolved_file_path = file_path.resolve()
        matching_errors: list[dict[str, str]] = []
        for err in type_errors:
            if err.get("severity") != "error":
                continue
            err_file = err.get("file")
            if not err_file:
                continue
            if Path(err_file).resolve() != resolved_file_path:
                continue
            if int(err.get("line", "0")) != line_num:
                continue
            matching_errors.append(err)

        # 原因と詳細を特定
        if matching_errors:
            # 型エラーが見つかった場合
            error = matching_errors[0]
            cause = error.get("message", "型エラーが発生")
            detail = self._extract_error_detail(error, code_context)
        else:
            # 型エラーが見つからない場合（既にignoreされているため）
            cause = f"型チェックを回避: {ignore_type}"
            detail = self._infer_cause_from_code(code_context, ignore_type)

        # 優先度を判定
        priority = self._determine_priority(ignore_type, code_context, matching_errors)

        # 解決策を生成
        solutions = self._generate_solutions(ignore_type, code_context, matching_errors)

        return TypeIgnoreIssue(
            file_path=str(file_path),
            line_number=line_num,
            ignore_type=ignore_type,
            cause=cause,
            detail=detail,
            code_context=code_context,
            priority=priority,
            solutions=solutions,
        )

    def _get_code_context(self, file_path: Path, line_num: int) -> CodeContext:
        """
        コードコンテキストを取得

        Args:
            file_path: ファイルパス
            line_num: 行番号

        Returns:
            コードコンテキスト
        """
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()

        # 前後3行を取得
        before_lines = lines[max(0, line_num - 4) : line_num - 1]
        target_line = lines[line_num - 1] if line_num <= len(lines) else ""
        after_lines = lines[line_num : min(len(lines), line_num + 3)]

        return CodeContext(
            before_lines=[line.rstrip() for line in before_lines],
            target_line=target_line.rstrip(),
            after_lines=[line.rstrip() for line in after_lines],
            line_number=line_num,
        )

    def _extract_error_detail(
        self, error: dict[str, str], code_context: CodeContext
    ) -> str:
        """
        型エラーから詳細説明を抽出

        Args:
            error: 型エラー情報
            code_context: コードコンテキスト

        Returns:
            詳細説明
        """
        message = error.get("message", "")
        error_type = error.get("error_type", "")

        # AST解析で原因式を特定（簡易版）
        try:
            tree = ast.parse(code_context.target_line)
            # 関数呼び出しや変数アクセスを検出
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    return f"{message} (関数呼び出しで型エラー)"
                elif isinstance(node, ast.Attribute):
                    return f"{message} (属性アクセスで型エラー)"
        except SyntaxError:
            pass

        return f"{message} [{error_type}]"

    def _infer_cause_from_code(
        self, code_context: CodeContext, ignore_type: str
    ) -> str:
        """
        コードから原因を推測

        Args:
            code_context: コードコンテキスト
            ignore_type: ignore種別

        Returns:
            推測された原因
        """
        target = code_context.target_line

        # Pydantic関連パターン
        if "BaseModel" in target or "model_construct" in target:
            return "Pydanticモデルの動的生成による型エラー"

        # dict型アクセスパターン
        if "[" in target and "]" in target:
            return "dict型の値アクセスで型が不明確"

        # Any型パターン
        if "Any" in target:
            return "Any型の使用による型安全性の低下"

        return f"型チェック回避: {ignore_type}"

    def _determine_priority(
        self,
        ignore_type: str,
        code_context: CodeContext,
        errors: list[dict[str, str]],
    ) -> Priority:
        """
        優先度を判定

        Args:
            ignore_type: ignore種別
            code_context: コードコンテキスト
            errors: 型エラー情報のリスト

        Returns:
            優先度（HIGH/MEDIUM/LOW）
        """
        target = code_context.target_line

        # HIGH: Any型の多用、重要な型チェック回避
        if "Any" in target and ignore_type in [
            "assignment",
            "arg-type",
            "return-value",
        ]:
            return "HIGH"

        # HIGH: エラーが複数ある場合
        if len(errors) > 1:
            return "HIGH"

        # MEDIUM: 局所的な型エラー
        if ignore_type in ["call-arg", "arg-type", "attr-defined"]:
            return "MEDIUM"

        # LOW: 既知の制約（Pydantic動的属性等）
        if "BaseModel" in target or "model_construct" in target:
            return "LOW"

        return "MEDIUM"

    def _generate_solutions(
        self,
        ignore_type: str,
        code_context: CodeContext,
        errors: list[dict[str, str]],
    ) -> list[str]:
        """
        解決策を生成

        Args:
            ignore_type: ignore種別
            code_context: コードコンテキスト
            errors: 型エラー情報のリスト

        Returns:
            解決策のリスト
        """
        solutions = []
        target = code_context.target_line

        # Pydantic関連
        if "BaseModel" in target:
            solutions.append("model_construct()を使用して動的にインスタンス作成")
            solutions.append("TypedDictで型定義してBaseModelに変換")

        # dict型アクセス
        if "[" in target and "]" in target:
            solutions.append("Pydanticモデルのまま操作（model_dump()を使わない）")
            solutions.append("TypedDict形式のスキーマを追加")

        # call-arg
        if ignore_type == "call-arg":
            solutions.append("関数シグネチャに型アノテーションを追加")
            solutions.append("引数の型をキャストまたはバリデーション追加")

        # 汎用的な解決策
        if not solutions:
            solutions.append("型アノテーションの追加または修正を検討")
            solutions.append("型の不一致を修正するためのキャストやバリデーションを追加")

        return solutions
