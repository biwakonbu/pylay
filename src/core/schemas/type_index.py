# schemas/type_index.py - 型インデックス管理
"""
型インデックス管理モジュール

Pythonの組み込み型やプロジェクト固有の型をレイヤー別に分類・管理する
"""

from typing import Any, get_origin
from collections import defaultdict


# 型レジストリ - レイヤー別の型を管理
TYPE_REGISTRY: dict[str, dict[str, type[Any]]] = defaultdict(dict)

# レイヤー定義
LAYERS: dict[str, list[type[Any]]] = {
    "primitives": [str, int, float, bool, bytes, type(None)],
    "containers": [list, tuple, set, dict, frozenset],
    "typing": [
        # 一般的なtyping型は動的に検出
    ],
}


def build_registry() -> None:
    """
    型レジストリを構築する

    組み込み型や一般的な型をレイヤー別に分類
    """
    global TYPE_REGISTRY

    # プリミティブ型
    for layer, types in LAYERS.items():
        for typ in types:
            TYPE_REGISTRY[layer][typ.__name__] = typ

    # 追加の型を動的に検出（必要に応じて拡張）
    # 例: pydanticモデル、dataclassesなど


def get_type_layer(type_obj: type[Any]) -> str:
    """
    指定された型の適切なレイヤーを返す

    Args:
        type_obj: 判定対象の型

    Returns:
        レイヤー名（"primitives", "containers", "typing" など）
    """
    # プリミティブ型判定
    for layer, types in LAYERS.items():
        if type_obj in types:
            return layer

    # ジェネリック型の場合、originをチェック
    origin = get_origin(type_obj)
    if origin:
        return get_type_layer(origin)

    # デフォルトはtypingレイヤー
    return "typing"


def register_type(type_obj: type[Any], layer: str) -> None:
    """
    型を指定されたレイヤーに登録

    Args:
        type_obj: 登録する型
        layer: レイヤー名
    """
    if type_obj.__name__ not in TYPE_REGISTRY[layer]:
        TYPE_REGISTRY[layer][type_obj.__name__] = type_obj


def get_layer_types(layer: str) -> dict[str, type[Any]]:
    """
    指定されたレイヤーの型辞書を取得

    Args:
        layer: レイヤー名

    Returns:
        型辞書
    """
    return TYPE_REGISTRY.get(layer, {}).copy()


def get_all_layers() -> list[str]:
    """利用可能なすべてのレイヤー名を取得"""
    return list(TYPE_REGISTRY.keys())


def get_registry_stats() -> dict[str, int]:
    """レジストリの統計情報を取得"""
    return {layer: len(types) for layer, types in TYPE_REGISTRY.items()}


def get_available_types_all() -> list[str]:
    """すべての利用可能な型名を取得"""
    all_types: list[str] = []
    for layer_types in TYPE_REGISTRY.values():
        all_types.extend(layer_types.keys())
    return sorted(all_types)


# 初期化時にレジストリを構築
build_registry()
