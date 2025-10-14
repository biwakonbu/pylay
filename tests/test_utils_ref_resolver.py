"""
utils/ref_resolver.py のテスト
"""

import pytest

from src.core.schemas.yaml_spec import DictTypeSpec, ListTypeSpec, TypeSpec
from utils.ref_resolver import RefResolver


class TestRefResolver:
    """RefResolverクラスのテスト"""

    def test_detect_cycles_from_data_no_cycles(self):
        """循環参照がないデータのテスト"""
        types_data = {
            "User": {
                "type": "dict",
                "properties": {"id": {"type": "int"}, "name": {"type": "str"}},
            },
            "Order": {
                "type": "dict",
                "properties": {
                    "user_id": {"type": "str"},  # 参照なし
                    "amount": {"type": "float"},
                },
            },
        }
        # 例外が発生しないことを確認
        RefResolver.detect_cycles_from_data(types_data)

    def test_detect_cycles_from_data_with_cycles(self):
        """循環参照があるデータのテスト"""
        types_data = {
            "A": {
                "type": "dict",
                "properties": {
                    "b": "B",  # Bを参照
                },
            },
            "B": {
                "type": "dict",
                "properties": {
                    "a": "A",  # Aを参照 -> 循環
                },
            },
        }
        with pytest.raises(ValueError, match="Circular reference detected"):
            RefResolver.detect_cycles_from_data(types_data)

    def test_collect_refs_from_data_basic(self):
        """基本的な参照収集のテスト"""
        spec_data = {
            "type": "list",
            "items": "User",  # 参照
        }
        refs = RefResolver._collect_refs_from_data(spec_data)
        assert "User" in refs

    def test_collect_refs_from_data_nested(self):
        """ネストされた参照収集のテスト"""
        spec_data = {
            "type": "dict",
            "properties": {
                "user": "User",
                "orders": {"type": "list", "items": "Order"},
            },
        }
        refs = RefResolver._collect_refs_from_data(spec_data)
        assert "User" in refs
        assert "Order" in refs

    def test_collect_refs_from_data_union(self):
        """Union型の参照収集のテスト"""
        spec_data = {"type": "union", "variants": ["User", "Admin"]}
        refs = RefResolver._collect_refs_from_data(spec_data)
        assert "User" in refs
        assert "Admin" in refs

    def test_detect_cycles_types_no_cycles(self):
        """TypeSpecベースの循環参照検出（なし）のテスト"""
        user_spec = DictTypeSpec(name="User", type="dict", properties={"id": TypeSpec(name="id", type="int")})
        order_spec = DictTypeSpec(
            name="Order",
            type="dict",
            properties={"user_id": TypeSpec(name="user_id", type="str")},
        )
        types = {"User": user_spec, "Order": order_spec}

        # 例外が発生しないことを確認
        RefResolver.detect_cycles(types)

    def test_detect_cycles_types_with_cycles(self):
        """TypeSpecベースの循環参照検出（あり）のテスト"""
        user_spec = DictTypeSpec(
            name="User",
            type="dict",
            properties={"order": "Order"},  # 参照
        )
        order_spec = DictTypeSpec(
            name="Order",
            type="dict",
            properties={"user": "User"},  # 参照 -> 循環
        )
        types = {"User": user_spec, "Order": order_spec}

        with pytest.raises(ValueError, match="Circular reference detected"):
            RefResolver.detect_cycles(types)

    def test_collect_refs_from_spec_basic(self):
        """TypeSpecからの参照収集（基本）のテスト"""
        spec = ListTypeSpec(name="UserList", type="list", items="User")
        refs = RefResolver._collect_refs_from_spec(spec)
        assert "User" in refs

    def test_collect_refs_from_spec_nested(self):
        """TypeSpecからの参照収集（ネスト）のテスト"""
        user_spec = DictTypeSpec(name="User", type="dict", properties={"id": TypeSpec(name="id", type="int")})
        order_spec = DictTypeSpec(name="Order", type="dict", properties={"user": user_spec})
        refs = RefResolver._collect_refs_from_spec(order_spec)
        # ネストされたTypeSpecからの参照は収集されない（str参照のみ）
        assert len(refs) == 0

    def test_resolve_all_basic(self):
        """基本的な参照解決のテスト"""
        user_spec = DictTypeSpec(name="User", type="dict", properties={"id": TypeSpec(name="id", type="int")})
        types = {"User": user_spec}

        resolved = RefResolver.resolve_all(types)
        assert "User" in resolved
        assert resolved["User"] == user_spec  # 参照なしなのでそのまま

    def test_resolve_all_with_refs(self):
        """参照を含む参照解決のテスト"""
        # 実際のTypeContextが必要なので、簡易テスト
        # 詳細なテストは統合テストでカバー
        user_spec = DictTypeSpec(name="User", type="dict", properties={"id": TypeSpec(name="id", type="int")})
        types = {"User": user_spec}

        resolved = RefResolver.resolve_all(types)
        assert len(resolved) == 1
