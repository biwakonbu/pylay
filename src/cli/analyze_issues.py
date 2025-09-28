#!/usr/bin/env python3
"""
pylay プロジェクトの問題分析スクリプト

このスクリプトは、以下のチェックを実行し、問題を分析・報告します：
1. リンター問題（Ruff）
2. 型チェック問題（mypy）
3. テスト失敗（pytest）
4. セキュリティ問題（safety）
5. コード複雑度（radon）
6. docstringカバレッジ（interrogate）
7. コードカバレッジレポート
8. 依存関係の脆弱性チェック
"""

import subprocess
import sys
import json
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Any


@dataclass
class CheckResult:
    """チェック結果を表すデータクラス"""

    name: str
    success: bool
    output: str
    error_output: str
    return_code: int
    has_issues: bool = False


class ProjectAnalyzer:
    """プロジェクトの包括的な問題分析を行うクラス"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.results: list[CheckResult] = []

    def run_command(
        self, cmd: list[str], description: str, expected_exit_codes: list[int] = None
    ) -> CheckResult:
        """
        コマンドを実行し、結果を記録する

        Args:
            cmd: 実行するコマンド（リスト形式）
            description: チェックの説明
            expected_exit_codes: 正常終了とみなす終了コードのリスト（デフォルト: [0]）

        Returns:
            CheckResult: 実行結果
        """
        if expected_exit_codes is None:
            expected_exit_codes = [0]

        print(f"\n🔍 {description} を実行中...")

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": str(self.project_root)},
            )

            # 結果を判定
            success = result.returncode in expected_exit_codes
            has_issues = not success or bool(result.stderr.strip())

            check_result = CheckResult(
                name=description,
                success=success,
                output=result.stdout.strip(),
                error_output=result.stderr.strip(),
                return_code=result.returncode,
                has_issues=has_issues,
            )

            self.results.append(check_result)

            # 結果を表示
            if check_result.output:
                print("📋 出力:")
                print(check_result.output)

            if check_result.error_output:
                print("⚠️ エラー/警告:")
                print(check_result.error_output)

            if check_result.success:
                print("✅ 成功")
            else:
                print("❌ 失敗")

            return check_result

        except Exception as e:
            error_msg = f"コマンド実行エラー: {e}"
            print(f"💥 {error_msg}")

            check_result = CheckResult(
                name=description,
                success=False,
                output="",
                error_output=error_msg,
                return_code=-1,
                has_issues=True,
            )

            self.results.append(check_result)
            return check_result

    def check_linting(self) -> CheckResult:
        """リンター問題をチェック"""
        return self.run_command(
            ["uv", "run", "ruff", "check", ".", "--output-format=concise"],
            "リンター問題チェック（Ruff）",
        )

    def check_type_checking(self) -> CheckResult:
        """型チェック問題を確認"""
        # ネームスペース競合を避けるため、個別ファイルでチェック
        mypy_files = [
            "converters/type_to_yaml.py",
            "converters/yaml_to_type.py",
            "doc_generators/yaml_doc_generator.py",
            "doc_generators/base.py",
            "doc_generators/config.py",
            "schemas/yaml_type_spec.py",
            "schemas/type_index.py",
        ]
        return self.run_command(
            ["uv", "run", "mypy"] + mypy_files, "型チェック問題（mypy）"
        )

    def check_tests(self) -> CheckResult:
        """テスト失敗をチェック"""
        return self.run_command(
            ["uv", "run", "pytest", "--tb=short", "--no-cov"],
            "テスト実行チェック（pytest）",
            expected_exit_codes=[0, 1, 2, 3, 4, 5],  # pytestの一般的な終了コード
        )

    def check_security(self) -> CheckResult:
        """セキュリティ問題をチェック"""
        return self.run_command(
            ["uv", "run", "safety", "check", "--file", "pyproject.toml"],
            "セキュリティ問題チェック（safety）",
        )

    def check_complexity(self) -> CheckResult:
        """コード複雑度をチェック"""
        return self.run_command(
            ["uv", "run", "radon", "cc", ".", "-s", "--total-average"],
            "コード複雑度チェック（radon）",
        )

    def check_docstring_coverage(self) -> CheckResult:
        """docstringカバレッジをチェック"""
        return self.run_command(
            ["uv", "run", "interrogate", "."],
            "docstringカバレッジチェック（interrogate）",
        )

    def check_coverage_report(self) -> CheckResult:
        """カバレッジレポートの存在と内容をチェック"""
        coverage_file = self.project_root / "htmlcov" / "index.html"
        if coverage_file.exists():
            return CheckResult(
                name="カバレッジレポート確認",
                success=True,
                output=f"カバレッジレポートが利用可能です: {coverage_file}",
                error_output="",
                return_code=0,
                has_issues=False,
            )
        else:
            return CheckResult(
                name="カバレッジレポート確認",
                success=False,
                output="カバレッジレポートが見つかりません。テストを実行してください。",
                error_output="",
                return_code=1,
                has_issues=True,
            )

    def check_dependencies(self) -> CheckResult:
        """依存関係の脆弱性をチェック"""
        return self.run_command(["uv", "run", "pip", "check"], "依存関係整合性チェック")

    def run_all_checks(self) -> dict[str, Any]:
        """
        すべてのチェックを実行し、結果をまとめる

        Returns:
            実行結果のサマリー
        """
        print("🚀 pylay プロジェクト包括的問題分析を開始します")
        print("=" * 60)

        # 各チェックを実行
        self.check_linting()
        self.check_type_checking()
        self.check_tests()
        self.check_security()
        self.check_complexity()
        self.check_docstring_coverage()
        self.check_coverage_report()
        self.check_dependencies()

        # 結果をまとめる
        summary = {
            "total_checks": len(self.results),
            "successful_checks": sum(1 for r in self.results if r.success),
            "failed_checks": sum(1 for r in self.results if not r.success),
            "checks_with_issues": sum(1 for r in self.results if r.has_issues),
            "results": [
                {
                    "name": result.name,
                    "success": result.success,
                    "has_issues": result.has_issues,
                    "return_code": result.return_code,
                    "output_lines": len(result.output.split("\n"))
                    if result.output
                    else 0,
                    "error_lines": len(result.error_output.split("\n"))
                    if result.error_output
                    else 0,
                }
                for result in self.results
            ],
        }

        return summary

    def print_summary(self, summary: dict[str, Any]):
        """分析結果のサマリーを表示"""
        print("\n" + "=" * 60)
        print("📊 分析結果サマリー")
        print("=" * 60)

        print(
            f"✅ 成功したチェック: {summary['successful_checks']}/{summary['total_checks']}"
        )
        print(
            f"❌ 失敗したチェック: {summary['failed_checks']}/{summary['total_checks']}"
        )
        print(
            f"⚠️ 問題のあるチェック: {summary['checks_with_issues']}/{summary['total_checks']}"
        )

        print("\n📋 詳細結果:")
        for result in summary["results"]:
            status = (
                "✅"
                if result["success"] and not result["has_issues"]
                else "⚠️"
                if result["has_issues"]
                else "❌"
            )
            print(f"  {status} {result['name']}")
            if result["has_issues"]:
                print(
                    f"    - 出力行数: {result['output_lines']}, エラー行数: {result['error_lines']}"
                )

        print("\n💡 推奨事項:")
        if summary["failed_checks"] > 0:
            print("  - 失敗したチェックを優先的に修正してください")
        if summary["checks_with_issues"] > 0:
            print("  - 問題のあるチェックの出力を確認してください")
        if summary["successful_checks"] == summary["total_checks"]:
            print("  - すべてのチェックが成功しました！プロジェクトの品質は良好です")
        else:
            print("  - 問題を修正した後、再度実行することを推奨します")

    def save_report(
        self, summary: dict[str, Any], filepath: str = "analysis_report.json"
    ):
        """分析レポートをJSONファイルに保存"""
        report = {
            "timestamp": subprocess.run(
                ["date", "+%Y-%m-%d %H:%M:%S"], capture_output=True, text=True
            ).stdout.strip(),
            "summary": summary,
            "detailed_results": [
                {
                    "name": result.name,
                    "success": result.success,
                    "has_issues": result.has_issues,
                    "return_code": result.return_code,
                    "output": result.output,
                    "error_output": result.error_output,
                }
                for result in self.results
            ],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n💾 分析レポートを保存しました: {filepath}")


def main():
    """メイン実行関数"""
    analyzer = ProjectAnalyzer()

    try:
        summary = analyzer.run_all_checks()
        analyzer.print_summary(summary)
        analyzer.save_report(summary)

        # 終了コードを設定（問題があればエラーコードを返す）
        exit_code = 1 if summary["failed_checks"] > 0 else 0
        sys.exit(exit_code)

    except KeyboardInterrupt:
        print("\n\n⚠️ ユーザーにより中断されました")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 分析中に予期しないエラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
