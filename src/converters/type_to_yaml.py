import yaml
import inspect
from typing import Any, get_origin, get_args, Dict
from pydantic import ValidationError

from schemas.yaml_type_spec import TypeSpec, ListTypeSpec, DictTypeSpec, UnionTypeSpec

def type_to_spec(typ: type[Any]) -> TypeSpec:
    """Python型をTypeSpecに変換"""
    origin = get_origin(typ)
    args = get_args(typ)
    
    # __doc__ をdescriptionに設定
    description = inspect.getdoc(typ) or None
    
    if origin is None:
        # 基本型
        basic_types = {str: 'str', int: 'int', float: 'float', bool: 'bool'}
        type_str = basic_types.get(typ, 'any')
        return TypeSpec(name=typ.__name__, type=type_str, description=description)
    
    elif origin is list:
        if args:
            items_spec = type_to_spec(args[0])
            return ListTypeSpec(name=typ.__name__, items=items_spec, description=description)
        else:
            return ListTypeSpec(name=typ.__name__, items=TypeSpec(name='any', type='any'), description=description)
    
    elif origin is dict:
        if args:
            key_spec = type_to_spec(args[0])
            value_spec = type_to_spec(args[1])
            # 簡易的にpropertiesとして扱うが、実際はキー型による
            properties = {str(key_spec.name): value_spec}
            return DictTypeSpec(name=typ.__name__, properties=properties, description=description)
        else:
            return DictTypeSpec(name=typ.__name__, properties={}, description=description)
    
    elif origin is Union:
        variants = [type_to_spec(arg) for arg in args]
        return UnionTypeSpec(name=typ.__name__, variants=variants, description=description)
    
    else:
        # 未サポート
        return TypeSpec(name=typ.__name__, type='unknown', description=description)

def type_to_yaml(typ: type[Any], output_file: str = None, as_root: bool = True) -> str | Dict[str, dict]:
    """型をYAML文字列に変換、またはファイル出力 (v1.1対応)"""
    spec = type_to_spec(typ)
    
    # v1.1構造: nameをキーとして出力、nameフィールド除外
    spec_data = spec.model_dump(exclude={'name'})
    
    if as_root:
        yaml_data = {typ.__name__: spec_data}
        yaml_str = yaml.dump(yaml_data, default_flow_style=False, allow_unicode=True)
    else:
        # 従来形式 (互換性用)
        yaml_str = yaml.dump(spec.model_dump(), default_flow_style=False, allow_unicode=True)
        yaml_data = yaml_str  # 文字列
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(yaml_str)
    
    return yaml_str if as_root else yaml_data

# 例
if __name__ == "__main__":
    from typing import List, Dict, Union
    import datetime
    
    # テスト型
    UserId = str  # NewTypeではないが簡易
    Users = List[Dict[str, str]]
    Result = Union[int, str]
    
    print("v1.1形式出力:")
    print(type_to_yaml(Users, as_root=True))
    print("\n従来形式出力:")
    print(type_to_yaml(Result, as_root=False))
