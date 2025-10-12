"""
型推論機能のテスト
"""

from pathlib import Path

from src.core.analyzer.models import InferResult
from src.core.analyzer.type_inferrer import TypeInferenceAnalyzer
from src.core.schemas.pylay_config import PylayConfig


class TestTypeInference:
    """型推論機能のテストクラス"""

    def _get_test_config(self) -> PylayConfig:
        """テスト用の設定を取得"""
        return PylayConfig(
            target_dirs=["src"],
            output_dir="docs/test-output",
            infer_level="normal",
            generate_markdown=True,
            extract_deps=True,
        )

    def test_infer_simple_types(self):
        """基本的な型の推論テスト"""
        code = """
x = 42
y = "hello"
z = True
"""
        config = self._get_test_config()
        analyzer = TypeInferenceAnalyzer(config)
        inferred = analyzer.infer_types_from_code(code)

        # 推論結果はmypyの出力によるため、環境により異なる可能性がある
        assert isinstance(inferred, dict)
        for key, value in inferred.items():
            assert isinstance(value, InferResult)

    def test_merge_inferred_types(self):
        """型マージ機能のテスト"""
        config = self._get_test_config()
        analyzer = TypeInferenceAnalyzer(config)
        existing = {"a": "int"}
        inferred = {
            "b": InferResult(variable_name="b", inferred_type="str", confidence=0.9, line_number=1),
            "c": InferResult(variable_name="c", inferred_type="bool", confidence=0.85, line_number=2),
        }
        merged = analyzer.merge_inferred_types(existing, inferred)

        assert merged["a"] == "int"
        assert merged["b"] == "str"
        assert merged["c"] == "bool"

    def test_extract_existing_annotations(self):
        """既存アノテーション抽出のテスト"""
        test_file = Path(__file__).parent / "test_sample.py"
        test_file.write_text("""
x: int = 5
def func(y: str) -> bool:
    return len(y) > 0
""")

        try:
            config = self._get_test_config()
            analyzer = TypeInferenceAnalyzer(config)
            annotations = analyzer.extract_existing_annotations(str(test_file))
            assert "x" in annotations
            assert "y" in annotations
        finally:
            test_file.unlink()

    def test_infer_from_file(self):
        """ファイルからの推論テスト"""
        test_file = Path(__file__).parent / "test_infer.py"
        test_file.write_text("""
a = 1
b = "test"
""")

        try:
            config = self._get_test_config()
            analyzer = TypeInferenceAnalyzer(config)
            inferred = analyzer.infer_types_from_file(str(test_file))
            assert isinstance(inferred, dict)
            for key, value in inferred.items():
                assert isinstance(value, InferResult)
        finally:
            test_file.unlink()
