# 型仕様: User
ユーザー情報を表す型
## 型情報
```yaml
additional_properties: false
description: ユーザー情報を表す型
name: User
properties:
  email:
    description: メールアドレス
    name: email
    required: false
    type: str
  id:
    description: ユーザーID
    name: id
    required: true
    type: int
  name:
    description: ユーザー名
    name: name
    required: true
    type: str
required: true
type: dict

```
## プロパティ
### id
## 型情報
```yaml
description: ユーザーID
name: id
required: true
type: int

```
### name
## 型情報
```yaml
description: ユーザー名
name: name
required: true
type: str

```
### email
## 型情報
```yaml
description: メールアドレス
name: email
required: false
type: str

```
---
このドキュメントは自動生成されました。
