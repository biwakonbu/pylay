# ORM統合ガイド

このガイドでは、pylayのドメイン型をORM（Object-Relational Mapping）フレームワークと統合する方法を説明します。

## 目次

- [背景](#背景)
- [基本原則](#基本原則)
- [統合パターン](#統合パターン)
  - [パターン1: TypeDecorator（型の一貫性重視）](#パターン1-typedecorator型の一貫性重視)
  - [パターン2: hybrid_property（互換性重視）](#パターン2-hybrid_property互換性重視)
  - [パターン3: composite types（DDD重視）](#パターン3-composite-typesddd重視)
  - [パターン4: レイヤー分離（シンプルさ重視）](#パターン4-レイヤー分離シンプルさ重視)
- [設計パターンの選択基準](#設計パターンの選択基準)
- [ORM別実装例](#orm別実装例)
  - [SQLAlchemy 2.0](#sqlalchemy-20)
  - [Django ORM](#django-orm)
- [マイグレーション統合の共通原則](#マイグレーション統合の共通原則)
- [ベストプラクティス](#ベストプラクティス)
- [よくある質問](#よくある質問)

## 背景

pylayでは、プリミティブ型の直接使用を避け、`NewType`、`Annotated`、`BaseModel`などを活用したドメイン型の定義を推奨しています。一方で、ORMフレームワークはデータベースとのマッピングのため、特定の型制約を持つことがあります。

**結論**: 現代的なORMでは、ドメイン型を使用可能です。適切なパターンを選択することで、型の一貫性とORM統合を両立できます。

## 基本原則

1. **型の一貫性を優先**: 可能な限り、全レイヤーで同じドメイン型を使用する
2. **段階的な移行**: 既存プロジェクトでは、レイヤー分離パターンから始める
3. **バリデーションの適切な配置**: ビジネスロジックのバリデーションはドメイン層で実行
4. **ドキュメントの維持**: 型定義には必ずdocstringを記述

## 統合パターン

### パターン1: TypeDecorator（型の一貫性重視）

**特徴**:

- 全レイヤーで同じドメイン型を使用
- ORM層でもドメイン型のバリデーションが効く
- 型の一貫性が最も高い

**適用場面**:

- 新規プロジェクト
- 型安全性を最優先する場合
- チーム全体で型システムの理解が深い場合

**実装例（SQLAlchemy 2.0）**:

```python
from typing import NewType, Annotated
from pydantic import Field, TypeAdapter
from sqlalchemy import TypeDecorator, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# ドメイン型の定義（pylayスタイル）
UserId = NewType('UserId', int)
UserIdValidator: TypeAdapter[int] = TypeAdapter(
    Annotated[int, Field(gt=0, description="ユーザーID（正の整数）")]
)

def create_user_id(value: int) -> UserId:
    """ユーザーIDを生成

    Args:
        value: ユーザーID値（正の整数）

    Returns:
        検証済みのUserId型

    Raises:
        ValidationError: 値が正の整数でない場合
    """
    validated = UserIdValidator.validate_python(value)
    return UserId(validated)

Email = NewType('Email', str)
EmailValidator: TypeAdapter[str] = TypeAdapter(
    Annotated[str, Field(pattern=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')]
)

def create_email(value: str) -> Email:
    """メールアドレスを生成

    Args:
        value: メールアドレス文字列

    Returns:
        検証済みのEmail型

    Raises:
        ValidationError: 値が正しいメールアドレス形式でない場合
    """
    validated = EmailValidator.validate_python(value)
    return Email(validated)

# SQLAlchemy TypeDecorator
class UserIdType(TypeDecorator):
    """UserId型のTypeDecorator

    データベースからの読み込み時に自動的にUserId型に変換します。
    """
    impl = Integer
    cache_ok = True

    def process_result_value(
        self, value: int | None, dialect
    ) -> UserId | None:
        """データベースからの読み込み時の処理"""
        if value is not None:
            return create_user_id(value)
        return None

class EmailType(TypeDecorator):
    """Email型のTypeDecorator

    データベースからの読み込み時に自動的にEmail型に変換します。
    """
    impl = String
    cache_ok = True

    def process_result_value(self, value: str | None, dialect) -> Email | None:
        """データベースからの読み込み時の処理"""
        if value is not None:
            return create_email(value)
        return None

# ORM モデル
class Base(DeclarativeBase):
    pass

class User(Base):
    """ユーザーモデル

    全レイヤーでドメイン型（UserId, Email）を使用します。
    """
    __tablename__ = 'users'

    # 型ヒント: UserId、ランタイムでも型変換される
    id: Mapped[UserId] = mapped_column(UserIdType, primary_key=True)
    email: Mapped[Email] = mapped_column(EmailType, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100))

# 使用例
def get_user_by_id(session, user_id: UserId) -> User | None:
    """ユーザーIDでユーザーを取得

    Args:
        session: SQLAlchemyセッション
        user_id: ユーザーID（UserId型）

    Returns:
        ユーザーオブジェクト、存在しない場合はNone
    """
    return session.query(User).filter(User.id == user_id).first()

# 型の一貫性が保たれる
user = get_user_by_id(session, create_user_id(1))
if user:
    # user.id は UserId型
    print(f"User ID: {user.id}")  # 型チェッカーがUserId型と認識
```

**利点**:

- 全レイヤーで型の一貫性が保たれる
- ORM層でもドメイン型のバリデーションが実行される
- 型チェッカーが正確に型を追跡できる

**欠点**:

- TypeDecoratorの実装が必要
- 既存プロジェクトへの適用は影響範囲が大きい

### パターン2: hybrid_property（互換性重視）

**特徴**:

- ORM層では内部的にプリミティブ型を使用
- プロパティアクセスでドメイン型に変換
- 既存のORM設定を変更せずに段階的に導入可能

**適用場面**:

- 既存プロジェクトへの段階的導入
- ORM設定の変更が難しい場合
- 互換性を重視する場合

**実装例（SQLAlchemy 2.0）**:

```python
from typing import NewType, Annotated
from pydantic import Field, TypeAdapter
from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.hybrid import hybrid_property

# ドメイン型の定義
UserId = NewType('UserId', int)
UserIdValidator: TypeAdapter[int] = TypeAdapter(Annotated[int, Field(gt=0)])

def create_user_id(value: int) -> UserId:
    """ユーザーIDを生成"""
    validated = UserIdValidator.validate_python(value)
    return UserId(validated)

class Base(DeclarativeBase):
    pass

class User(Base):
    """ユーザーモデル（hybrid_propertyパターン）

    内部的にはプリミティブ型、アクセス時にドメイン型に変換します。
    """
    __tablename__ = 'users'

    # 内部カラム（プリミティブ型）
    _id: Mapped[int] = mapped_column('id', Integer, primary_key=True)
    _email: Mapped[str] = mapped_column('email', String(255), unique=True)

    @hybrid_property
    def id(self) -> UserId:
        """ユーザーID（UserId型）"""
        return create_user_id(self._id)

    @id.setter
    def id(self, value: UserId) -> None:
        """ユーザーIDを設定"""
        self._id = int(value)  # NewTypeはruntimeではintとして扱われる

    @hybrid_property
    def email(self) -> str:
        """メールアドレス"""
        return self._email

    @email.setter
    def email(self, value: str) -> None:
        """メールアドレスを設定"""
        self._email = value

# 使用例
user = User(_id=1, _email="test@example.com")
user_id: UserId = user.id  # UserId型として取得
```

**利点**:

- 既存のORM設定を変更せずに導入可能
- 段階的な移行が容易
- データベース層との互換性が高い

**欠点**:

- 内部カラム（_id）とプロパティ（id）の二重管理
- クエリ時に内部カラム名を意識する必要がある
- 型チェッカーの推論が一部制限される場合がある

### パターン3: composite types（DDD重視）

**特徴**:

- 複数のカラムを1つのドメインオブジェクトとして扱う
- 値オブジェクト（Value Object）の実装に最適
- DDDの原則に沿った設計

**適用場面**:

- ドメイン駆動設計（DDD）を採用している場合
- 複数のフィールドを1つの概念として扱いたい場合
- 値オブジェクトを明示的にモデリングする場合

**実装例（SQLAlchemy 2.0）**:

```python
from typing import NewType
from dataclasses import dataclass
from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, composite

# 値オブジェクト（Value Object）
@dataclass(frozen=True)
class Address:
    """住所（値オブジェクト）

    複数のフィールドを1つの不変オブジェクトとして扱います。
    """
    street: str
    city: str
    postal_code: str

    def __composite_values__(self):
        """SQLAlchemyのcomposite型のための特殊メソッド"""
        return (self.street, self.city, self.postal_code)

class Base(DeclarativeBase):
    pass

class User(Base):
    """ユーザーモデル（composite typesパターン）

    複数のカラムを1つの値オブジェクト（Address）として扱います。
    """
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))

    # 複数カラムを1つのドメインオブジェクトとしてマッピング
    _street: Mapped[str] = mapped_column('street', String(255))
    _city: Mapped[str] = mapped_column('city', String(100))
    _postal_code: Mapped[str] = mapped_column('postal_code', String(20))

    address: Mapped[Address] = composite(Address, _street, _city, _postal_code)

# 使用例
user = User(id=1, name="田中太郎", address=Address("1-2-3", "東京都", "100-0001"))
print(f"住所: {user.address.street}, {user.address.city} {user.address.postal_code}")
```

**利点**:

- ドメインモデルとして自然な表現
- 値オブジェクトの不変性を保証
- ビジネスロジックをドメインオブジェクトに集約できる

**欠点**:

- 複数カラムの管理が複雑になる
- データベーススキーマとの対応が直感的でない場合がある
- 一部のORMでサポートが限定的

### パターン4: レイヤー分離（シンプルさ重視）

**特徴**:

- ORM層とAPI/ドメイン層を明確に分離
- 変換層で型変換を明示的に実行
- シンプルで理解しやすい

**適用場面**:

- 既存プロジェクトへの段階的導入
- チーム全体のスキルレベルが多様
- シンプルさと保守性を重視する場合

**実装例**:

```python
from typing import NewType, Annotated
from pydantic import BaseModel, Field, TypeAdapter
from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# ドメイン層（pylayスタイル）
UserId = NewType('UserId', int)
UserIdValidator: TypeAdapter[int] = TypeAdapter(Annotated[int, Field(gt=0)])

def create_user_id(value: int) -> UserId:
    """ユーザーIDを生成"""
    validated = UserIdValidator.validate_python(value)
    return UserId(validated)

Email = NewType('Email', str)
EmailValidator: TypeAdapter[str] = TypeAdapter(
    Annotated[str, Field(pattern=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')]
)

def create_email(value: str) -> Email:
    """メールアドレスを生成"""
    validated = EmailValidator.validate_python(value)
    return Email(validated)

# ORM層（プリミティブ型）
class Base(DeclarativeBase):
    pass

class UserORM(Base):
    """ユーザーORMモデル（データベース層）

    データベースとのマッピングに特化し、プリミティブ型を使用します。
    """
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(100))

# API層（ドメイン型）
class UserResponse(BaseModel):
    """ユーザーレスポンス（API層）

    APIレスポンスに使用するドメイン型を持つモデルです。
    """
    id: UserId
    email: Email
    name: str

# 変換層（明示的な型変換）
def user_orm_to_response(user_orm: UserORM) -> UserResponse:
    """ORMモデルからAPIレスポンスモデルへ変換

    Args:
        user_orm: ORMモデル（データベース層）

    Returns:
        APIレスポンスモデル（ドメイン層）
    """
    return UserResponse(
        id=create_user_id(user_orm.id),
        email=create_email(user_orm.email),
        name=user_orm.name
    )

def user_response_to_orm(user: UserResponse) -> UserORM:
    """APIレスポンスモデルからORMモデルへ変換

    Args:
        user: APIレスポンスモデル（ドメイン層）

    Returns:
        ORMモデル（データベース層）
    """
    return UserORM(
        id=int(user.id),  # NewTypeはruntimeではintとして扱われる
        email=str(user.email),
        name=user.name
    )

# 使用例
def get_user_by_id(session, user_id: UserId) -> UserResponse | None:
    """ユーザーIDでユーザーを取得（ドメイン型で返却）

    Args:
        session: SQLAlchemyセッション
        user_id: ユーザーID（ドメイン型）

    Returns:
        ユーザーレスポンス、存在しない場合はNone
    """
    user_orm = session.query(UserORM).filter(UserORM.id == int(user_id)).first()
    if user_orm:
        return user_orm_to_response(user_orm)
    return None
```

**利点**:

- シンプルで理解しやすい
- 各レイヤーの責任が明確
- 既存コードへの影響が最小限
- 段階的な移行が容易

**欠点**:

- 変換コードの追加が必要
- 型変換のオーバーヘッド
- レイヤー間での型の不一致の可能性

## 設計パターンの選択基準

| 要件 | 推奨アプローチ | 理由 |
|------|--------------|------|
| 型の一貫性を最優先 | TypeDecorator + ドメイン型 | 全レイヤーで同じ型を使用 |
| シンプルさを優先 | レイヤー分離 + 変換層 | ORMの設定が最小限 |
| 既存ORMプロジェクト | レイヤー分離（段階的移行） | 既存コードへの影響を最小化 |
| 新規プロジェクト | TypeDecorator（最初から型安全） | 初期設計から型安全性を確保 |
| DDD重視 | composite types | ドメインモデルとして自然な表現 |
| 互換性重視 | hybrid_property | 既存ORM設定を変更せずに導入 |

## ORM別実装例

### SQLAlchemy 2.0

SQLAlchemy 2.0は、上記のすべてのパターンをサポートしています。

**推奨パターン**:

- 新規プロジェクト: TypeDecorator
- 既存プロジェクト: レイヤー分離 → hybrid_property → TypeDecorator（段階的移行）

#### Alembicマイグレーション連携

**基本設定**:

```python
# alembic/env.py
from sqlalchemy import engine_from_config, pool
from alembic import context
from your_app.models import Base  # TypeDecoratorを使用したモデル

# ターゲットメタデータを設定
target_metadata = Base.metadata

def run_migrations_online():
    """オンラインモードでマイグレーションを実行"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()
```

**マイグレーション例**:

```python
# alembic/versions/xxx_add_user_table.py
"""Add user table with domain types

Revision ID: xxx
Revises:
Create Date: 2025-10-09
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    """ユーザーテーブルを追加（ドメイン型対応）"""
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

def downgrade():
    """ユーザーテーブルを削除"""
    op.drop_table('users')
```

**ドメイン型を使用したマイグレーションのベストプラクティス**:

1. TypeDecoratorは内部的にプリミティブ型として扱われるため、マイグレーションファイルではプリミティブ型を使用
2. モデル定義でドメイン型を使用することで、アプリケーション層で型安全性を確保
3. マイグレーション実行前に、モデル定義とマイグレーションファイルの整合性をチェック

```bash
# マイグレーションファイルを生成（自動検出）
alembic revision --autogenerate -m "Add user table"

# マイグレーションを適用
alembic upgrade head

# マイグレーション履歴を確認
alembic history
```

#### トラブルシューティング例

##### 問題1: TypeDecoratorの型変換エラー

**症状**:

```python
# エラー例
sqlalchemy.exc.StatementError: (builtins.TypeError) UserId.__init__() missing 1 required positional argument: 'value'
```

**原因**: `process_bind_param`メソッドが実装されていない、または誤った値を返している

**解決策**:

```python
class UserIdType(TypeDecorator):
    impl = Integer
    cache_ok = True

    def process_bind_param(self, value: UserId | None, dialect) -> int | None:
        """データベースへの保存時の処理を追加"""
        if value is None:
            return None
        return int(value)  # NewTypeをintに変換

    def process_result_value(
        self, value: int | None, dialect
    ) -> UserId | None:
        """データベースからの読み込み時の処理"""
        if value is not None:
            return create_user_id(value)
        return None
```

##### 問題2: マイグレーション時の型不一致

**症状**:

```text
alembic.util.exc.CommandError: Target database is not up to date.
```

**原因**: モデル定義とデータベーススキーマが不一致

**解決策**:

```bash
# 現在の状態を確認
alembic current

# マイグレーション差分を確認
alembic check

# マイグレーションを再生成
alembic revision --autogenerate -m "Fix schema mismatch"

# マイグレーションを適用
alembic upgrade head
```

##### 問題3: クエリ時の型エラー

**症状**:

```python
# エラー例
TypeError: argument of type 'UserId' is not iterable
```

**原因**: ドメイン型を直接比較演算子で使用している

**解決策**:

```python
# ❌ 誤った使用方法
user = session.query(User).filter(User.id == user_id).first()

# ✅ 正しい使用方法（ドメイン型はそのまま使用可能）
user_id = create_user_id(1)
user = session.query(User).filter(User.id == user_id).first()

# または、明示的にintに変換
user = session.query(User).filter(User.id == int(user_id)).first()
```

**参考リンク**:

- [TypeDecorator](https://docs.sqlalchemy.org/en/20/core/custom_types.html#typedecorator-recipes)
- [Hybrid Attributes](https://docs.sqlalchemy.org/en/20/orm/extensions/hybrid.html)
- [Composite Column Types](https://docs.sqlalchemy.org/en/20/orm/composites.html)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)

### Django ORM

Django ORMでは、カスタムフィールド型を定義することでドメイン型を使用できます。

**実装例**:

```python
from typing import NewType, Annotated
from pydantic import Field, TypeAdapter
from django.db import models
from django.core.exceptions import ValidationError

# ドメイン型の定義
UserId = NewType('UserId', int)
UserIdValidator: TypeAdapter[int] = TypeAdapter(Annotated[int, Field(gt=0)])

def create_user_id(value: int) -> UserId:
    """ユーザーIDを生成"""
    validated = UserIdValidator.validate_python(value)
    return UserId(validated)

# Djangoカスタムフィールド
class UserIdField(models.IntegerField):
    """UserId型のDjangoフィールド

    データベースからの読み込み時に自動的にUserId型に変換します。
    """

    def from_db_value(self, value, expression, connection):
        """データベースからの読み込み時の処理"""
        if value is None:
            return value
        try:
            return create_user_id(value)
        except Exception as e:
            raise ValidationError(f"無効なUserId: {e}")

    def to_python(self, value):
        """Pythonオブジェクトへの変換"""
        if isinstance(value, UserId):
            return value
        if value is None:
            return value
        try:
            return create_user_id(int(value))
        except Exception as e:
            raise ValidationError(f"無効なUserId: {e}")

    def get_prep_value(self, value):
        """データベースへの保存時の処理"""
        if value is None:
            return value
        return int(value)

# Djangoモデル
class User(models.Model):
    """ユーザーモデル

    カスタムフィールドを使用してドメイン型を扱います。
    """
    id = UserIdField(primary_key=True)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100)

    class Meta:
        db_table = 'users'
```

**推奨パターン**:

- カスタムフィールド型（TypeDecoratorと同等）
- レイヤー分離（シンプルさ重視）

**参考リンク**:

- [Custom model fields](https://docs.djangoproject.com/en/stable/howto/custom-model-fields/)

## マイグレーション統合の共通原則

各ORMのマイグレーションツールでドメイン型を使用する際の共通原則とベストプラクティスを紹介します。

### マイグレーション基本原則

1. **マイグレーションファイルではプリミティブ型を使用**
   - TypeDecorator、カスタムフィールドは内部的にプリミティブ型として扱われる
   - マイグレーションファイルでは、データベーススキーマの変更に集中
   - ドメイン型のバリデーションはアプリケーション層で実行

2. **モデル定義でドメイン型を使用**
   - アプリケーション層では型安全性を確保
   - ドメイン型を使用することで、ビジネスロジックの表現力向上
   - 型チェッカー（mypy、pyright）による静的解析が可能

3. **マイグレーションの自動生成を活用**
   - 各ORMの自動生成機能を使用し、手動でのSQLエラーを防ぐ
   - 自動生成されたマイグレーションファイルをレビューし、必要に応じて調整

### ORM別マイグレーションツール比較

| ORM | マイグレーションツール | 自動生成 | 推奨度 |
|-----|----------------------|---------|-------|
| SQLAlchemy | Alembic | ✅ | ⭐⭐⭐⭐⭐ |
| Django ORM | Django Migrations | ✅ | ⭐⭐⭐⭐⭐ |

### マイグレーション戦略

#### 戦略1: スキーマ駆動（推奨）

**特徴**:

- モデル定義を変更してからマイグレーションを自動生成
- 型安全性を最優先
- 開発スピードが速い

**手順**:

```python
# 1. モデル定義を変更
class User(Base):
    id: Mapped[UserId] = mapped_column(UserIdType, primary_key=True)
    email: Mapped[Email] = mapped_column(EmailType, unique=True)

# 2. マイグレーションを自動生成
# Alembic: alembic revision --autogenerate -m "Add user table"

# 3. マイグレーションを確認・調整

# 4. マイグレーションを適用
# Alembic: alembic upgrade head
```

#### 戦略2: スキーマファースト

**特徴**:

- データベーススキーマを先に設計
- マイグレーションファイルを手動で作成
- データベース設計を重視する場合に適している

**手順**:

```python
# 1. マイグレーションファイルを手動作成
def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

# 2. マイグレーションを適用

# 3. モデル定義を作成・調整
class User(Base):
    id: Mapped[UserId] = mapped_column(UserIdType, primary_key=True)
    email: Mapped[Email] = mapped_column(EmailType, unique=True)
```

### マイグレーション時の注意点

#### 注意点1: 既存データの移行

**問題**: ドメイン型を導入する際、既存のプリミティブ型データをどう扱うか？

**解決策**:

```python
# マイグレーションファイルでデータ移行を実行
def upgrade():
    # 既存データは変更不要（プリミティブ型として保存されているため）
    # TypeDecoratorが自動的にドメイン型に変換
    pass

# または、バリデーションエラーを回避するために事前にデータをクリーンアップ
def upgrade():
    # 無効なデータを削除またはデフォルト値で更新
    op.execute("DELETE FROM users WHERE id <= 0")
```

#### 注意点2: NULL値の扱い

**問題**: ドメイン型がNULL値を受け入れるか？

**解決策**:

```python
# ドメイン型定義でNULLを許可
UserId = NewType('UserId', int)

def create_user_id(value: int | None) -> UserId | None:
    """ユーザーIDを生成（NULL許可）"""
    if value is None:
        return None
    validated = UserIdValidator.validate_python(value)
    return UserId(validated)

# TypeDecoratorでNULL処理
class UserIdType(TypeDecorator):
    impl = Integer

    def process_result_value(self, value: int | None, dialect) -> UserId | None:
        if value is None:
            return None
        return create_user_id(value)
```

#### 注意点3: マイグレーションのロールバック

**問題**: マイグレーションを元に戻す場合、ドメイン型の影響は？

**解決策**:

```python
# ドメイン型はランタイムではプリミティブ型として扱われるため、
# ロールバック時に特別な処理は不要

def downgrade():
    # 通常のロールバック処理
    op.drop_table('users')
```

### マイグレーション自動テスト

**テスト例**:

```python
import pytest
from sqlalchemy import create_engine
from alembic import command
from alembic.config import Config

def test_migration_upgrade():
    """マイグレーションの適用テスト"""
    # テスト用データベースを作成
    engine = create_engine('sqlite:///:memory:')

    # Alembic設定
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", str(engine.url))

    # マイグレーションを適用
    command.upgrade(alembic_cfg, "head")

    # テーブルが作成されたことを確認
    with engine.connect() as conn:
        result = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in result]
        assert 'users' in tables

def test_migration_downgrade():
    """マイグレーションのロールバックテスト"""
    engine = create_engine('sqlite:///:memory:')
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", str(engine.url))

    # マイグレーションを適用してからロールバック
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")

    # テーブルが削除されたことを確認
    with engine.connect() as conn:
        result = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in result]
        assert 'users' not in tables
```

### CI/CD統合

**GitHub Actions例**:

```yaml
name: Database Migration Test

on: [push, pull_request]

jobs:
  test-migrations:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install alembic pytest

      - name: Run migration tests
        run: pytest tests/test_migrations.py

      - name: Apply migrations
        run: alembic upgrade head
```

## ベストプラクティス

1. **段階的な導入**
   - 既存プロジェクトでは、まずレイヤー分離パターンから始める
   - 型の一貫性が必要な部分から順次TypeDecoratorに移行

2. **バリデーションの適切な配置**
   - ビジネスロジックのバリデーション: ドメイン層（create_user_id等のファクトリ関数）
   - データベース制約: ORM層（unique, nullable等）
   - API入力バリデーション: API層（Pydantic BaseModel）

3. **ドキュメントの維持**
   - すべてのドメイン型にdocstringを記述
   - TypeDecoratorやカスタムフィールドにも説明を追加
   - 型変換の意図を明確に記述

4. **型チェッカーの活用**
   - mypy、pyrightで型チェックを実行
   - pylayの品質チェック機能を活用（`pylay check --focus quality`）

5. **テストの充実**
   - ドメイン型のバリデーションテスト
   - ORM層との型変換テスト
   - エンドツーエンドの統合テスト

## よくある質問

### Q1: 既存プロジェクトにどのように導入すればよいですか？

**A**: 段階的な導入をお勧めします：

1. **Phase 1**: レイヤー分離パターンで開始
   - API層でドメイン型を使用
   - ORM層は既存のまま
   - 変換層で型変換を明示的に実行

2. **Phase 2**: hybrid_propertyを導入
   - 重要なエンティティから順次適用
   - 型の一貫性を段階的に向上

3. **Phase 3**: TypeDecoratorへ移行
   - 全レイヤーで型の一貫性を確保
   - ORM設定を完全に型安全化

### Q2: パフォーマンスへの影響はありますか？

**A**: 実用上、影響は軽微です：

- **TypeDecorator**: データベースからの読み込み時のみ型変換が発生
- **hybrid_property**: プロパティアクセス時のオーバーヘッドは最小限
- **レイヤー分離**: 変換関数の実行コストは小さい

ボトルネックになる場合は、プロファイリングして最適化してください。

### Q3: FastAPIとの統合はどうすればよいですか？

**A**: FastAPIはPydanticを標準で使用しているため、ドメイン型をそのまま使用できます：

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class UserResponse(BaseModel):
    """ユーザーレスポンス

    ドメイン型をそのまま使用できます。
    """
    id: UserId
    email: Email
    name: str

@app.get("/users/{user_id}")
def get_user(user_id: int) -> UserResponse:
    """ユーザーを取得"""
    # ORM層から取得
    user_orm = session.query(UserORM).filter(UserORM.id == user_id).first()
    # ドメイン型に変換して返却
    return user_orm_to_response(user_orm)
```

詳細は[フレームワーク別パターン集](framework-patterns.md)を参照してください。

### Q4: pylayの品質チェック機能はORMモデルにも使えますか？

**A**: はい、使用できます：

```bash
# プロジェクト全体の型品質チェック
pylay check --focus quality

# ORM層のファイルを指定
pylay check --focus quality src/models/orm.py
```

レイヤー分離パターンの場合、API層（ドメイン型）とORM層（プリミティブ型）で品質スコアが異なる可能性があります。これは設計上の意図であり、問題ありません。

### Q5: 複数のORMを併用する場合はどうすればよいですか？

**A**: レイヤー分離パターンが最適です：

```python
# 共通ドメイン層
class UserResponse(BaseModel):
    id: UserId
    email: Email
    name: str

# SQLAlchemy ORM層
class UserSQLAlchemy(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # ...

# Django ORM層
class UserDjango(models.Model):
    id = models.IntegerField(primary_key=True)
    # ...

# 変換層
def sqlalchemy_to_response(user: UserSQLAlchemy) -> UserResponse:
    return UserResponse(id=create_user_id(user.id), ...)

def django_to_response(user: UserDjango) -> UserResponse:
    return UserResponse(id=create_user_id(user.id), ...)
```

ドメイン層を共通化することで、複数のORMを統一的に扱えます。

### Q6: 非同期ORMとの統合はどうすればよいですか？

**A**: 非同期ORM（Tortoise ORM、SQLAlchemy 2.0の非同期サポート）では、async/awaitを使用します：

```python
# Tortoise ORM（非同期）
async def get_user_by_id(user_id: UserId) -> User | None:
    """ユーザーIDでユーザーを取得"""
    return await User.filter(id=user_id).first()

# SQLAlchemy 2.0（非同期）
from sqlalchemy.ext.asyncio import AsyncSession

async def get_user_by_id(session: AsyncSession, user_id: UserId) -> User | None:
    """ユーザーIDでユーザーを取得"""
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
```

ドメイン型はランタイムではプリミティブ型として扱われるため、非同期処理と互換性があります。

### Q7: 型ヒントが複雑になりすぎる場合の対処法は？

**A**: 型エイリアスを活用して可読性を向上させます：

```python
# ❌ 複雑な型ヒント
def get_users(
    session: Session,
    filters: dict[str, str | int | None] | None = None
) -> list[tuple[UserId, Email, str]]:
    pass

# ✅ 型エイリアスを使用
type UserFilters = dict[str, str | int | None]
type UserTuple = tuple[UserId, Email, str]

def get_users(
    session: Session,
    filters: UserFilters | None = None
) -> list[UserTuple]:
    pass
```

### Q8: 既存のプリミティブ型を一括でドメイン型に置き換える方法は？

**A**: 段階的な置き換えを推奨します：

1. **Phase 1**: ドメイン型を定義

   ```python
   UserId = NewType('UserId', int)
   UserIdValidator: TypeAdapter[int] = TypeAdapter(Annotated[int, Field(gt=0)])

   def create_user_id(value: int) -> UserId:
       validated = UserIdValidator.validate_python(value)
       return UserId(validated)
   ```

2. **Phase 2**: API層から順次置き換え

   ```python
   # Before
   def get_user(user_id: int) -> User:
       pass

   # After
   def get_user(user_id: UserId) -> User:
       pass
   ```

3. **Phase 3**: ORM層にTypeDecoratorを導入

   ```python
   class User(Base):
       id: Mapped[UserId] = mapped_column(UserIdType, primary_key=True)
   ```

一括置き換えではなく、重要度の高い部分から順次適用することで、リスクを最小化できます。

### Q9: ORMモデルとPydanticモデルの役割分担は？

**A**: 以下のように役割を分けることを推奨します：

| モデル | 役割 | 使用場面 |
|--------|------|---------|
| ORMモデル | データベースとのマッピング | データ永続化、クエリ実行 |
| Pydantic BaseModel | ビジネスロジック、API入出力 | API層、ドメイン層 |

**実装例**:

```python
# ORM層（データベース層）
class UserORM(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255))

# ドメイン層（ビジネスロジック）
class User(BaseModel):
    id: UserId
    email: Email

    def is_admin(self) -> bool:
        """管理者かどうかを判定"""
        return self.email.endswith("@admin.example.com")

# 変換層
def orm_to_domain(user_orm: UserORM) -> User:
    return User(
        id=create_user_id(user_orm.id),
        email=create_email(user_orm.email)
    )
```

### Q10: 型定義の粒度はどの程度が適切ですか？

**A**: 以下の基準で判断してください：

**細かすぎる場合（アンチパターン）**:

```python
# ❌ 過度に細分化
FirstName = NewType('FirstName', str)
LastName = NewType('LastName', str)
MiddleName = NewType('MiddleName', str)

# 使いづらい
def get_full_name(first: FirstName, middle: MiddleName, last: LastName) -> str:
    pass
```

**適切な粒度**:

```python
# ✅ 適切な粒度
@dataclass(frozen=True)
class FullName:
    first: str
    middle: str | None
    last: str

    def display_name(self) -> str:
        """フルネームを表示形式で返す"""
        if self.middle:
            return f"{self.first} {self.middle} {self.last}"
        return f"{self.first} {self.last}"
```

**判断基準**:

- ビジネスロジックが必要な場合 → Level 3（BaseModel、dataclass）
- バリデーションが必要な場合 → Level 2（NewType + ファクトリ）
- 単なる別名の場合 → Level 1（type エイリアス）

詳細は[typing-rule.md](../typing-rule.md)を参照してください。

---

**関連ドキュメント**:

- [フレームワーク別パターン集](framework-patterns.md)
- [typing-rule.md](../typing-rule.md)
- [CLAUDE.md](../../CLAUDE.md)

**更新履歴**:

- 2025-10-09: SQLAlchemy統合の詳細化（Issue #59対応）- Alembicマイグレーション連携、トラブルシューティング拡充、マイグレーション統合の共通原則追加
- 2025-10-08: 初版作成（Issue #54対応）
