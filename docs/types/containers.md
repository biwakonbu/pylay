# CONTAINERS レイヤー型カタログ（完全自動成長）

## 🎯 完全自動成長について

このレイヤーの型は、定義を追加するだけで自動的に利用可能になります。
新しい型を追加すると、以下の方法ですぐに使用できます：

```python
from schemas.core_types import TypeFactory

# 完全自動成長（レイヤー自動検知）
MyNewType = TypeFactory.get_auto('MyNewType')
```

## list

### 説明
Built-in mutable sequence. If no argument is given, the constructor creates a new empty list. The argument must be an iterable if specified.

### 利用方法（完全自動成長）
```python
from schemas.core_types import TypeFactory

# 完全自動成長（レイヤー自動検知）
listType = TypeFactory.get_auto('list')
instance = listType()
```

### レイヤー指定方法（オプション）
```python
listType = TypeFactory.get_by_layer('containers', 'list')
```

### 型定義
```python
list (型情報: <class 'list'>)
```
## tuple

### 説明
Built-in immutable sequence. If no argument is given, the constructor returns an empty tuple. If iterable is specified the tuple is initialized from iterable's items. If the argument is a tuple, the return value is the same object.

### 利用方法（完全自動成長）
```python
from schemas.core_types import TypeFactory

# 完全自動成長（レイヤー自動検知）
tupleType = TypeFactory.get_auto('tuple')
instance = tupleType()
```

### レイヤー指定方法（オプション）
```python
tupleType = TypeFactory.get_by_layer('containers', 'tuple')
```

### 型定義
```python
tuple (型情報: <class 'tuple'>)
```
## set

### 説明
Build an unordered collection of unique elements.

### 利用方法（完全自動成長）
```python
from schemas.core_types import TypeFactory

# 完全自動成長（レイヤー自動検知）
setType = TypeFactory.get_auto('set')
instance = setType()
```

### レイヤー指定方法（オプション）
```python
setType = TypeFactory.get_by_layer('containers', 'set')
```

### 型定義
```python
set (型情報: <class 'set'>)
```
## dict

### 説明
dict() -> new empty dictionary dict(mapping) -> new dictionary initialized from a mapping object's (key, value) pairs dict(iterable) -> new dictionary initialized as if via: d = {} for k, v in iterable: d[k] = v dict(**kwargs) -> new dictionary initialized with the name=value pairs in the keyword argument list.  For example:  dict(one=1, two=2)

### 利用方法（完全自動成長）
```python
from schemas.core_types import TypeFactory

# 完全自動成長（レイヤー自動検知）
dictType = TypeFactory.get_auto('dict')
instance = dictType()
```

### レイヤー指定方法（オプション）
```python
dictType = TypeFactory.get_by_layer('containers', 'dict')
```

### 型定義
```python
dict (型情報: <class 'dict'>)
```
## frozenset

### 説明
Build an immutable unordered collection of unique elements.

### 利用方法（完全自動成長）
```python
from schemas.core_types import TypeFactory

# 完全自動成長（レイヤー自動検知）
frozensetType = TypeFactory.get_auto('frozenset')
instance = frozensetType()
```

### レイヤー指定方法（オプション）
```python
frozensetType = TypeFactory.get_by_layer('containers', 'frozenset')
```

### 型定義
```python
frozenset (型情報: <class 'frozenset'>)
```
**生成日**: 2025-09-27T14:32:40.615796
