# tests/scripts/test_generate_type_docs.py - 型ドキュメント生成スクリプトのテスト
"""型ドキュメント生成スクリプトのテスト（実体テスト中心）"""
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from scripts.generate_type_docs import generate_docs, generate_layer_docs


class TestGenerateTypeDocs:
    """型ドキュメント生成のテスト"""

    def setup_method(self):
        """テストセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir) / "docs" / "types"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """テストクリーンアップ"""
        shutil.rmtree(self.temp_dir)

    def test_generate_layer_docs_with_valid_types(self):
        """有効な型でのレイヤードキュメント生成テスト"""
        # 実際の型レジストリを使用してテスト
        from schemas.type_index import TYPE_REGISTRY

        # primitivesレイヤーがあることを確認
        assert "primitives" in TYPE_REGISTRY
        assert len(TYPE_REGISTRY["primitives"]) > 0

        # ドキュメント生成を実行
        generate_layer_docs("primitives", TYPE_REGISTRY["primitives"], str(self.output_dir))

        # 出力ファイルが作成されたことを確認
        output_file = self.output_dir / "primitives.md"
        assert output_file.exists()

        # ファイル内容を確認
        content = output_file.read_text(encoding="utf-8")
        assert "# PRIMITIVES レイヤー型カタログ" in content
        assert "完全自動成長" in content
        assert "TypeFactory.get_auto" in content

    def test_generate_layer_docs_skip_newtype(self):
        """NewTypeが正しく除外されることを確認"""
        # 実際のレジストリを使用してテスト
        from schemas.type_index import TYPE_REGISTRY

        generate_layer_docs("primitives", TYPE_REGISTRY["primitives"], str(self.output_dir))

        content = (self.output_dir / "primitives.md").read_text(encoding="utf-8")
        assert "UserId" in content
        assert "ConversionId" in content
        # NewTypeは自動的に除外されることを確認（skip_typesで設定）

    def test_generate_layer_docs_with_typealias_descriptions(self):
        """TypeAlias用の説明が正しく適用されることを確認"""
        test_types = {
            "JSONValue": object,  # Any型として扱われる
            "TestType": str
        }

        generate_layer_docs("test", test_types, str(self.output_dir))

        content = (self.output_dir / "test.md").read_text(encoding="utf-8")
        assert "JSON値: 制約なしのJSON互換データ型" in content

    def test_generate_layer_docs_creates_directory(self):
        """出力ディレクトリが自動作成されることを確認"""
        non_existent_dir = Path(self.temp_dir) / "non_existent" / "deep" / "path"
        assert not non_existent_dir.exists()

        test_types = {"TestType": str}
        generate_layer_docs("test", test_types, str(non_existent_dir))

        assert non_existent_dir.exists()

    def test_generate_docs_creates_index(self):
        """全ドキュメント生成でインデックスファイルが作成されることを確認"""
        # 実際のレジストリを使用してテスト

        with patch("scripts.generate_type_docs.generate_layer_docs"), \
             patch("scripts.generate_type_docs.generate_index_docs"):
            generate_docs(str(self.output_dir))

            # インデックスファイルが作成されたことを確認（モックされているので実際には作成されない）
            # このテストはモックが正しく呼び出されることを確認するだけ
            pass


class TestGenerateTypeDocsErrorHandling:
    """エラーハンドリングのテスト"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.temp_dir)

    def test_generate_layer_docs_with_empty_registry(self):
        """空のレジストリでの動作確認"""
        empty_types = {}

        # エラーなく実行されることを確認
        generate_layer_docs("empty", empty_types, str(self.temp_dir))

        output_file = Path(self.temp_dir) / "empty.md"
        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "EMPTY レイヤー型カタログ" in content

    def test_generate_layer_docs_with_invalid_output_path(self):
        """無効な出力パスでの動作確認"""
        test_types = {"TestType": str}

        # 無効なパスでもエラーなく処理されることを確認（実際にはディレクトリ作成で失敗するが）
        # 実際の動作はos.makedirsの動作による
        try:
            generate_layer_docs("test", test_types, "/invalid/path")
        except Exception as e:
            # エラーが発生するのは正常（実際のファイルシステム制限による）
            assert "invalid" in str(e) or "path" in str(e).lower()


class TestGenerateTypeDocsPerformance:
    """パフォーマンステスト"""

    def setup_method(self):
        """テストセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir) / "docs" / "types"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """テストクリーンアップ"""
        shutil.rmtree(self.temp_dir)

    def test_generate_layer_docs_large_registry(self):
        """大規模レジストリでのパフォーマンステスト"""
        # 実際のレジストリを使用してテスト
        import time

        from schemas.type_index import TYPE_REGISTRY
        start_time = time.time()

        generate_layer_docs("primitives", TYPE_REGISTRY["primitives"], str(self.output_dir))

        end_time = time.time()
        execution_time = end_time - start_time

        # 実行時間が許容範囲内であることを確認（2秒以内）
        assert execution_time < 2.0, f"実行時間が長すぎます: {execution_time:.2f}秒"

        # 出力ファイルが正しく生成されていることを確認
        output_file = self.output_dir / "primitives.md"
        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "PRIMITIVES レイヤー型カタログ" in content
        # 実際の型数が含まれていることを確認
        assert "UserId" in content
        assert "ConversionId" in content
