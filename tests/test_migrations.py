#!/usr/bin/env python3
"""
マイグレーション統合テストスクリプト

以下のマイグレーション操作を検証：
1. 最新マイグレーションまでのUP実行
2. 1つ前のバージョンへのDOWN実行
3. 再度最新へのUP実行
4. スキーマ整合性検証
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """コマンド実行ヘルパー"""
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=30)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except Exception as e:
        return 1, "", str(e)


def get_current_revision() -> str | None:
    """現在のマイグレーションリビジョンを取得"""
    backend_dir = Path(__file__).parent.parent

    returncode, stdout, stderr = run_command(["uv", "run", "alembic", "current"], cwd=backend_dir)

    if returncode == 0:
        # "INFO  [alembic.runtime.migration] Context impl ..." の行を除外
        for line in stdout.strip().split("\n"):
            if line and not line.startswith("INFO") and "(head)" in line:
                # "revision_id (head)" の形式から revision_id を抽出
                return line.split()[0]
    return None


def get_revision_history() -> list[str]:
    """マイグレーション履歴を取得"""
    backend_dir = Path(__file__).parent.parent

    returncode, stdout, stderr = run_command(["uv", "run", "alembic", "history"], cwd=backend_dir)

    revisions = []
    if returncode == 0:
        for line in stdout.strip().split("\n"):
            if " -> " in line and not line.startswith("INFO"):
                # "prev_rev -> current_rev (head), description" の形式
                revision = line.split(" -> ")[1].split()[0]
                if revision != "<base>":
                    revisions.append(revision)

    return revisions


async def migration_up_test() -> bool:
    """最新マイグレーションまでのUP実行テスト"""
    print("📈 マイグレーション UP テスト開始...")
    backend_dir = Path(__file__).parent.parent

    returncode, stdout, stderr = run_command(["uv", "run", "alembic", "upgrade", "head"], cwd=backend_dir)

    if returncode == 0:
        print("✅ マイグレーション UP 成功")
        if stdout.strip():
            print(f"   {stdout.strip()}")
        return True
    else:
        print("❌ マイグレーション UP 失敗")
        print(f"   Error: {stderr}")
        return False


async def migration_down_test() -> bool:
    """1つ前のバージョンへのDOWN実行テスト"""
    print("\n📉 マイグレーション DOWN テスト開始...")
    backend_dir = Path(__file__).parent.parent

    # リビジョン履歴を取得
    revisions = get_revision_history()
    if len(revisions) < 2:
        print("⚠️  マイグレーション履歴が不足（DOWNテストスキップ）")
        return True  # テスト対象がないためスキップ

    # 1つ前のリビジョンにダウングレード
    previous_revision = revisions[-2]  # 最新から2番目

    returncode, stdout, stderr = run_command(["uv", "run", "alembic", "downgrade", previous_revision], cwd=backend_dir)

    if returncode == 0:
        print(f"✅ マイグレーション DOWN 成功 (-> {previous_revision})")
        if stdout.strip():
            print(f"   {stdout.strip()}")
        return True
    else:
        print("❌ マイグレーション DOWN 失敗")
        print(f"   Error: {stderr}")
        return False


async def migration_up_again_test() -> bool:
    """再度最新へのUP実行テスト"""
    print("\n🔄 マイグレーション 再UP テスト開始...")
    backend_dir = Path(__file__).parent.parent

    returncode, stdout, stderr = run_command(["uv", "run", "alembic", "upgrade", "head"], cwd=backend_dir)

    if returncode == 0:
        print("✅ マイグレーション 再UP 成功")
        if stdout.strip():
            print(f"   {stdout.strip()}")
        return True
    else:
        print("❌ マイグレーション 再UP 失敗")
        print(f"   Error: {stderr}")
        return False


async def verify_schema_integrity() -> bool:
    """スキーマ整合性検証"""
    print("\n🔍 スキーマ整合性検証開始...")
    backend_dir = Path(__file__).parent.parent

    # alembic check コマンドでスキーマ整合性をチェック
    returncode, stdout, stderr = run_command(["uv", "run", "alembic", "check"], cwd=backend_dir)

    if returncode == 0:
        print("✅ スキーマ整合性検証成功")
        return True
    else:
        print("❌ スキーマ整合性検証失敗")
        print(f"   Error: {stderr}")
        return False


async def main() -> int:
    """メイン処理"""
    print("🚀 マイグレーション統合テスト開始")

    try:
        # 現在のリビジョンを確認
        current_revision = get_current_revision()
        print(f"📋 現在のリビジョン: {current_revision or 'Unknown'}")

        # テスト実行
        tests = [
            ("UP Migration", migration_up_test),
            ("DOWN Migration", migration_down_test),
            ("Re-UP Migration", migration_up_again_test),
            ("Schema Integrity", verify_schema_integrity),
        ]

        for test_name, test_func in tests:
            success = await test_func()
            if not success:
                print(f"\n❌ {test_name} テストが失敗しました")
                return 1

        print("\n🎉 全てのマイグレーションテストが成功しました")
        return 0

    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        return 1


if __name__ == "__main__":
    # 環境変数の確認
    if not os.getenv("DATABASE_URL"):
        print("❌ DATABASE_URL環境変数が設定されていません")
        sys.exit(1)

    exit_code = asyncio.run(main())
    sys.exit(exit_code)
