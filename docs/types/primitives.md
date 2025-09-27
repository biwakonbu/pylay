# PRIMITIVES レイヤー型カタログ（完全自動成長）

## 🎯 完全自動成長について

このレイヤーの型は、定義を追加するだけで自動的に利用可能になります。
新しい型を追加すると、以下の方法ですぐに使用できます：

```python
from schemas.core_types import TypeFactory

# 完全自動成長（レイヤー自動検知）
MyNewType = TypeFactory.get_auto('MyNewType')
```

## 💡 このレイヤーでの型取得

```python
from schemas.core_types import TypeFactory

# レイヤー指定での取得（オプション）
MyType = TypeFactory.get_primitive('MyTypeName')
```

## str

### 説明
str(object='') -> str str(bytes_or_buffer[, encoding[, errors]]) -> str Create a new string object from the given object. If encoding or errors is specified, then the object must expose a data buffer that will be decoded using the given encoding and error handler. Otherwise, returns the result of object.__str__() (if defined) or repr(object). encoding defaults to 'utf-8'. errors defaults to 'strict'.

### 利用方法（完全自動成長）
```python
from schemas.core_types import TypeFactory

# 完全自動成長（レイヤー自動検知）
strType = TypeFactory.get_auto('str')
instance = strType("example_value")
```

### レイヤー指定方法（オプション）
```python
strType = TypeFactory.get_by_layer('primitives', 'str')
```

### 型定義
```python
str (型情報: <class 'str'>)
```
## int

### 説明
int([x]) -> integer int(x, base=10) -> integer Convert a number or string to an integer, or return 0 if no arguments are given.  If x is a number, return x.__int__().  For floating-point numbers, this truncates towards zero. If x is not a number or if base is given, then x must be a string, bytes, or bytearray instance representing an integer literal in the given base.  The literal can be preceded by '+' or '-' and be surrounded by whitespace.  The base defaults to 10.  Valid bases are 0 and 2-36. Base 0 means to interpret the base from the string as an integer literal. >>> int('0b100', base=0) 4

### 利用方法（完全自動成長）
```python
from schemas.core_types import TypeFactory

# 完全自動成長（レイヤー自動検知）
intType = TypeFactory.get_auto('int')
instance = intType("example_value")
```

### レイヤー指定方法（オプション）
```python
intType = TypeFactory.get_by_layer('primitives', 'int')
```

### 型定義
```python
int (型情報: <class 'int'>)
```
## float

### 説明
Convert a string or number to a floating-point number, if possible.

### 利用方法（完全自動成長）
```python
from schemas.core_types import TypeFactory

# 完全自動成長（レイヤー自動検知）
floatType = TypeFactory.get_auto('float')
instance = floatType("example_value")
```

### レイヤー指定方法（オプション）
```python
floatType = TypeFactory.get_by_layer('primitives', 'float')
```

### 型定義
```python
float (型情報: <class 'float'>)
```
## bool

### 説明
Returns True when the argument is true, False otherwise. The builtins True and False are the only two instances of the class bool. The class bool is a subclass of the class int, and cannot be subclassed.

### 利用方法（完全自動成長）
```python
from schemas.core_types import TypeFactory

# 完全自動成長（レイヤー自動検知）
boolType = TypeFactory.get_auto('bool')
instance = boolType("example_value")
```

### レイヤー指定方法（オプション）
```python
boolType = TypeFactory.get_by_layer('primitives', 'bool')
```

### 型定義
```python
bool (型情報: <class 'bool'>)
```
## bytes

### 説明
bytes(iterable_of_ints) -> bytes bytes(string, encoding[, errors]) -> bytes bytes(bytes_or_buffer) -> immutable copy of bytes_or_buffer bytes(int) -> bytes object of size given by the parameter initialized with null bytes bytes() -> empty bytes object Construct an immutable array of bytes from: - an iterable yielding integers in range(256) - a text string encoded using the specified encoding - any object implementing the buffer API. - an integer

### 利用方法（完全自動成長）
```python
from schemas.core_types import TypeFactory

# 完全自動成長（レイヤー自動検知）
bytesType = TypeFactory.get_auto('bytes')
instance = bytesType("example_value")
```

### レイヤー指定方法（オプション）
```python
bytesType = TypeFactory.get_by_layer('primitives', 'bytes')
```

### 型定義
```python
bytes (型情報: <class 'bytes'>)
```
## NoneType

### 説明
The type of the None singleton.

### 利用方法（完全自動成長）
```python
from schemas.core_types import TypeFactory

# 完全自動成長（レイヤー自動検知）
NoneTypeType = TypeFactory.get_auto('NoneType')
instance = NoneTypeType("example_value")
```

### レイヤー指定方法（オプション）
```python
NoneTypeType = TypeFactory.get_by_layer('primitives', 'NoneType')
```

### 型定義
```python
NoneType (型情報: <class 'NoneType'>)
```
**生成日**: 2025-09-27T14:32:40.615502
