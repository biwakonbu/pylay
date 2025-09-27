"""
参照解決と循環参照検出のためのユーティリティモジュール。

このモジュールは、TypeSpec間の参照を解決し、循環参照を検出するための関数を提供します。
yaml_to_type.py から抽出・モジュール化されたものです。
"""

from typing import Any, Dict, List
from schemas.yaml_type_spec import TypeSpec, ListTypeSpec, DictTypeSpec, UnionTypeSpec, TypeContext


class RefResolver:
    """
    参照解決と循環参照検出を担当するクラス。

    このクラスは、TypeSpec間の参照を解決し、循環参照を検出するための静的メソッドを提供します。
    """

    @staticmethod
    def detect_cycles_from_data(types_data: Dict[str, Any]) -> None:
        """
        生のデータから循環参照を検出します。

        Args:
            types_data: 型データ辞書（キー: 型名, 値: 型仕様）

        Raises:
            ValueError: 循環参照が検出された場合
        """
        ref_graph = {}
        for name, spec_data in types_data.items():
            refs = RefResolver._collect_refs_from_data(spec_data)
            ref_graph[name] = refs

        RefResolver._dfs_cycle_detect(ref_graph)

    @staticmethod
    def detect_cycles(types: Dict[str, TypeSpec]) -> None:
        """
        TypeSpec辞書から循環参照を検出します。

        Args:
            types: 型マップ（キー: 型名, 値: TypeSpec）

        Raises:
            ValueError: 循環参照が検出された場合
        """
        ref_graph = {}
        for name, spec in types.items():
            refs = RefResolver._collect_refs_from_spec(spec)
            ref_graph[name] = refs

        RefResolver._dfs_cycle_detect(ref_graph)

    @staticmethod
    def resolve_all(types: Dict[str, TypeSpec]) -> Dict[str, TypeSpec]:
        """
        すべての参照を解決します。

        Args:
            types: 型マップ（キー: 型名, 値: TypeSpec）

        Returns:
            参照が解決されたTypeSpecマップ
        """
        # まず循環参照を検出
        RefResolver.detect_cycles(types)

        context = TypeContext()

        # すべての型をコンテキストに追加
        for name, spec in types.items():
            context.add_type(name, spec)

        # 参照解決を実行
        resolved_types = {}
        for name, spec in types.items():
            resolved_types[name] = context._resolve_nested_refs(spec)

        return resolved_types

    @staticmethod
    def _dfs_cycle_detect(ref_graph: Dict[str, List[str]]) -> None:
        """
        DFSアルゴリズムで循環参照を検出します。

        Args:
            ref_graph: 参照グラフ（キー: 型名, 値: 参照リスト）

        Raises:
            ValueError: 循環参照が検出された場合
        """
        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in ref_graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for node in ref_graph:
            if node not in visited:
                if has_cycle(node):
                    raise ValueError(f"Circular reference detected involving: {node}")

    @staticmethod
    def _collect_refs_from_data(spec_data: Any) -> List[str]:
        """
        生のデータから参照文字列を収集します。

        Args:
            spec_data: 型仕様データ

        Returns:
            参照文字列のリスト
        """
        refs = []

        if isinstance(spec_data, dict):
            for key, value in spec_data.items():
                if key == 'items' and isinstance(value, str):
                    refs.append(value)
                elif key == 'properties' and isinstance(value, dict):
                    for prop_value in value.values():
                        if isinstance(prop_value, str):
                            refs.append(prop_value)
                        elif isinstance(prop_value, dict):
                            # ネストされたproperties内の参照
                            refs.extend(RefResolver._collect_refs_from_data(prop_value))
                elif key == 'variants' and isinstance(value, list):
                    for variant in value:
                        if isinstance(variant, str):
                            refs.append(variant)
                        elif isinstance(variant, dict):
                            # ネストされたvariants内の参照
                            refs.extend(RefResolver._collect_refs_from_data(variant))
                elif isinstance(value, (dict, list)):
                    # ネストされた構造もチェック
                    refs.extend(RefResolver._collect_refs_from_data(value))
        elif isinstance(spec_data, list):
            for item in spec_data:
                if isinstance(item, str):
                    refs.append(item)
                elif isinstance(item, (dict, list)):
                    refs.extend(RefResolver._collect_refs_from_data(item))

        return refs

    @staticmethod
    def _collect_refs_from_spec(spec: TypeSpec) -> List[str]:
        """
        TypeSpecから参照文字列を収集します。

        Args:
            spec: TypeSpecインスタンス

        Returns:
            参照文字列のリスト
        """
        from schemas.yaml_type_spec import RefPlaceholder
        refs = []

        if isinstance(spec, ListTypeSpec):
            if isinstance(spec.items, RefPlaceholder):
                refs.append(spec.items.ref_name)
            elif isinstance(spec.items, str):
                refs.append(spec.items)
            elif hasattr(spec.items, '__class__'):  # TypeSpecの場合
                refs.extend(RefResolver._collect_refs_from_spec(spec.items))
        elif isinstance(spec, DictTypeSpec):
            for prop in spec.properties.values():
                if isinstance(prop, RefPlaceholder):
                    refs.append(prop.ref_name)
                elif isinstance(prop, str):
                    refs.append(prop)
                elif hasattr(prop, '__class__'):  # TypeSpecの場合
                    refs.extend(RefResolver._collect_refs_from_spec(prop))
        elif isinstance(spec, UnionTypeSpec):
            for variant in spec.variants:
                if isinstance(variant, RefPlaceholder):
                    refs.append(variant.ref_name)
                elif isinstance(variant, str):
                    refs.append(variant)
                elif hasattr(variant, '__class__'):  # TypeSpecの場合
                    refs.extend(RefResolver._collect_refs_from_spec(variant))

        return refs
