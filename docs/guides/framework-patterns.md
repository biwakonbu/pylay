# フレームワーク別パターン集

このドキュメントでは、主要なPythonフレームワーク（FastAPI、Flask、Django）とpylayのドメイン型を統合する具体的なパターンを紹介します。

## 目次

- [FastAPI統合パターン](#fastapi統合パターン)
  - [基本パターン](#基本パターン-fastapi)
  - [依存性注入との統合](#依存性注入との統合)
  - [バリデーションエラーのハンドリング](#バリデーションエラーのハンドリング-fastapi)
- [Flask統合パターン](#flask統合パターン)
  - [基本パターン](#基本パターン-flask)
  - [リクエスト/レスポンスのバリデーション](#リクエストレスポンスのバリデーション)
  - [エラーハンドリング](#エラーハンドリング-flask)
- [Django統合パターン](#django統合パターン)
  - [基本パターン](#基本パターン-django)
  - [Django REST frameworkとの統合](#django-rest-frameworkとの統合)
  - [フォームバリデーション](#フォームバリデーション)
- [共通パターン](#共通パターン)
  - [ドメイン型の定義](#ドメイン型の定義)
  - [レイヤーアーキテクチャ](#レイヤーアーキテクチャ)
  - [テスト戦略](#テスト戦略)

## FastAPI統合パターン

FastAPIはPydanticをネイティブサポートしているため、pylayのドメイン型と最も相性が良いフレームワークです。

### 基本パターン (FastAPI)

**特徴**:
- Pydantic BaseModelをそのまま使用可能
- 自動的な型バリデーションとドキュメント生成
- ドメイン型を直接使用できる

**実装例**:

```python
from typing import NewType, Annotated
from pydantic import BaseModel, Field, TypeAdapter
from fastapi import FastAPI, HTTPException, Path, Query
from sqlalchemy.orm import Session

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
    """メールアドレスを生成"""
    validated = EmailValidator.validate_python(value)
    return Email(validated)

# APIレスポンスモデル
class UserResponse(BaseModel):
    """ユーザーレスポンスモデル

    API応答に使用するドメインモデルです。
    """
    id: UserId
    email: Email
    name: str
    age: int | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "email": "user@example.com",
                "name": "田中太郎",
                "age": 30
            }
        }

class UserCreateRequest(BaseModel):
    """ユーザー作成リクエストモデル

    新規ユーザー作成時のリクエストボディです。
    """
    email: Email
    name: str
    age: int | None = None

# FastAPIアプリケーション
app = FastAPI(title="User API", version="1.0.0")

@app.post("/users", response_model=UserResponse, status_code=201)
def create_user(user: UserCreateRequest, db: Session = Depends(get_db)) -> UserResponse:
    """新規ユーザーを作成

    Args:
        user: ユーザー作成リクエスト
        db: データベースセッション

    Returns:
        作成されたユーザー情報

    Raises:
        HTTPException: ユーザー作成に失敗した場合
    """
    # ORM層でユーザーを作成
    user_orm = UserORM(email=str(user.email), name=user.name, age=user.age)
    db.add(user_orm)
    db.commit()
    db.refresh(user_orm)

    # ドメイン型に変換して返却
    return UserResponse(
        id=create_user_id(user_orm.id),
        email=create_email(user_orm.email),
        name=user_orm.name,
        age=user_orm.age
    )

@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: Annotated[int, Path(gt=0, description="ユーザーID")],
    db: Session = Depends(get_db)
) -> UserResponse:
    """ユーザーIDでユーザーを取得

    Args:
        user_id: ユーザーID（正の整数）
        db: データベースセッション

    Returns:
        ユーザー情報

    Raises:
        HTTPException: ユーザーが見つからない場合（404）
    """
    user_orm = db.query(UserORM).filter(UserORM.id == user_id).first()
    if not user_orm:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    return UserResponse(
        id=create_user_id(user_orm.id),
        email=create_email(user_orm.email),
        name=user_orm.name,
        age=user_orm.age
    )

@app.get("/users", response_model=list[UserResponse])
def list_users(
    limit: Annotated[int, Query(gt=0, le=100)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_db)
) -> list[UserResponse]:
    """ユーザー一覧を取得

    Args:
        limit: 取得件数（1〜100）
        offset: オフセット（0以上）
        db: データベースセッション

    Returns:
        ユーザー情報のリスト
    """
    users_orm = db.query(UserORM).limit(limit).offset(offset).all()
    return [
        UserResponse(
            id=create_user_id(user.id),
            email=create_email(user.email),
            name=user.name,
            age=user.age
        )
        for user in users_orm
    ]
```

**利点**:
- 自動的なOpenAPIドキュメント生成
- 型安全なリクエスト/レスポンス
- Pydanticのバリデーション機能をフル活用

### 依存性注入との統合

FastAPIの依存性注入（Dependency Injection）システムとドメイン型を組み合わせます。

**実装例**:

```python
from typing import NewType, Annotated
from fastapi import Depends, HTTPException, Path
from sqlalchemy.orm import Session

UserId = NewType('UserId', int)

def create_user_id(value: int) -> UserId:
    """ユーザーIDを生成"""
    validated = UserIdValidator.validate_python(value)
    return UserId(validated)

# 依存性注入で使用する関数
async def get_user_or_404(
    user_id: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_db)
) -> UserResponse:
    """ユーザーを取得、存在しない場合は404エラー

    Args:
        user_id: ユーザーID
        db: データベースセッション

    Returns:
        ユーザー情報

    Raises:
        HTTPException: ユーザーが見つからない場合（404）
    """
    user_orm = db.query(UserORM).filter(UserORM.id == user_id).first()
    if not user_orm:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    return UserResponse(
        id=create_user_id(user_orm.id),
        email=create_email(user_orm.email),
        name=user_orm.name,
        age=user_orm.age
    )

# エンドポイントで依存性注入を使用
@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_update: UserCreateRequest,
    current_user: Annotated[UserResponse, Depends(get_user_or_404)],
    db: Session = Depends(get_db)
) -> UserResponse:
    """ユーザー情報を更新

    Args:
        user_update: 更新するユーザー情報
        current_user: 現在のユーザー情報（依存性注入）
        db: データベースセッション

    Returns:
        更新後のユーザー情報
    """
    # ORM層を更新
    user_orm = db.query(UserORM).filter(UserORM.id == int(current_user.id)).first()
    user_orm.email = str(user_update.email)
    user_orm.name = user_update.name
    user_orm.age = user_update.age
    db.commit()
    db.refresh(user_orm)

    # ドメイン型に変換して返却
    return UserResponse(
        id=create_user_id(user_orm.id),
        email=create_email(user_orm.email),
        name=user_orm.name,
        age=user_orm.age
    )
```

### バリデーションエラーのハンドリング (FastAPI)

Pydanticのバリデーションエラーをカスタマイズします。

**実装例**:

```python
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Pydanticバリデーションエラーのカスタムハンドラ

    Args:
        request: リクエストオブジェクト
        exc: バリデーションエラー

    Returns:
        カスタマイズされたエラーレスポンス
    """
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "バリデーションエラー",
            "errors": errors
        }
    )

@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    """Pydantic ValidationErrorのカスタムハンドラ

    Args:
        request: リクエストオブジェクト
        exc: Pydantic ValidationError

    Returns:
        カスタマイズされたエラーレスポンス
    """
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": "無効なデータ",
            "errors": exc.errors()
        }
    )
```

## Flask統合パターン

FlaskはPydanticをネイティブサポートしていませんが、手動でバリデーションを実行することで統合できます。

### 基本パターン (Flask)

**特徴**:
- 手動でのリクエスト/レスポンスバリデーション
- Pydanticモデルを明示的に使用
- シンプルで柔軟な統合

**実装例**:

```python
from typing import NewType, Annotated
from flask import Flask, request, jsonify
from pydantic import BaseModel, Field, ValidationError, TypeAdapter

# ドメイン型の定義
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

# APIモデル
class UserResponse(BaseModel):
    """ユーザーレスポンスモデル"""
    id: UserId
    email: Email
    name: str
    age: int | None = None

class UserCreateRequest(BaseModel):
    """ユーザー作成リクエストモデル"""
    email: Email
    name: str
    age: int | None = None

# Flaskアプリケーション
app = Flask(__name__)

@app.route('/users', methods=['POST'])
def create_user():
    """新規ユーザーを作成

    Returns:
        JSONレスポンス（ユーザー情報 or エラー）
    """
    try:
        # リクエストボディをPydanticモデルでバリデーション
        user_data = UserCreateRequest(**request.get_json())
    except ValidationError as e:
        return jsonify({"errors": e.errors()}), 422

    # ORM層でユーザーを作成
    user_orm = UserORM(email=str(user_data.email), name=user_data.name, age=user_data.age)
    db.session.add(user_orm)
    db.session.commit()

    # ドメイン型に変換してレスポンス
    response = UserResponse(
        id=create_user_id(user_orm.id),
        email=create_email(user_orm.email),
        name=user_orm.name,
        age=user_orm.age
    )
    return jsonify(response.model_dump()), 201

@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id: int):
    """ユーザーIDでユーザーを取得

    Args:
        user_id: ユーザーID

    Returns:
        JSONレスポンス（ユーザー情報 or エラー）
    """
    try:
        # URLパラメータをバリデーション
        validated_user_id = create_user_id(user_id)
    except ValidationError as e:
        return jsonify({"errors": e.errors()}), 400

    # ORM層からユーザーを取得
    user_orm = db.session.query(UserORM).filter(UserORM.id == user_id).first()
    if not user_orm:
        return jsonify({"error": "ユーザーが見つかりません"}), 404

    # ドメイン型に変換してレスポンス
    response = UserResponse(
        id=create_user_id(user_orm.id),
        email=create_email(user_orm.email),
        name=user_orm.name,
        age=user_orm.age
    )
    return jsonify(response.model_dump()), 200

@app.route('/users', methods=['GET'])
def list_users():
    """ユーザー一覧を取得

    Query Parameters:
        limit: 取得件数（デフォルト: 10）
        offset: オフセット（デフォルト: 0）

    Returns:
        JSONレスポンス（ユーザーリスト）
    """
    limit = request.args.get('limit', 10, type=int)
    offset = request.args.get('offset', 0, type=int)

    # クエリパラメータのバリデーション
    if limit <= 0 or limit > 100:
        return jsonify({"error": "limitは1〜100の範囲で指定してください"}), 400
    if offset < 0:
        return jsonify({"error": "offsetは0以上で指定してください"}), 400

    # ORM層からユーザーを取得
    users_orm = db.session.query(UserORM).limit(limit).offset(offset).all()

    # ドメイン型に変換してレスポンス
    responses = [
        UserResponse(
            id=create_user_id(user.id),
            email=create_email(user.email),
            name=user.name,
            age=user.age
        ).model_dump()
        for user in users_orm
    ]
    return jsonify(responses), 200
```

### リクエスト/レスポンスのバリデーション

Flaskでリクエスト/レスポンスを統一的にバリデーションするデコレータを作成します。

**実装例**:

```python
from functools import wraps
from flask import request, jsonify
from pydantic import BaseModel, ValidationError

def validate_request(model: type[BaseModel]):
    """リクエストボディをPydanticモデルでバリデーションするデコレータ

    Args:
        model: バリデーションに使用するPydanticモデル

    Returns:
        デコレータ関数
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # リクエストボディをバリデーション
                validated_data = model(**request.get_json())
                # バリデーション済みデータを関数に渡す
                return f(*args, validated_data=validated_data, **kwargs)
            except ValidationError as e:
                return jsonify({"errors": e.errors()}), 422
        return decorated_function
    return decorator

def validate_response(model: type[BaseModel]):
    """レスポンスをPydanticモデルでシリアライズするデコレータ

    Args:
        model: シリアライズに使用するPydanticモデル

    Returns:
        デコレータ関数
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            result = f(*args, **kwargs)
            # Pydanticモデルの場合、model_dump()でシリアライズ
            if isinstance(result, BaseModel):
                return jsonify(result.model_dump()), 200
            return result
        return decorated_function
    return decorator

# デコレータを使用
@app.route('/users', methods=['POST'])
@validate_request(UserCreateRequest)
@validate_response(UserResponse)
def create_user(validated_data: UserCreateRequest):
    """新規ユーザーを作成

    Args:
        validated_data: バリデーション済みのリクエストデータ

    Returns:
        UserResponseオブジェクト
    """
    # ORM層でユーザーを作成
    user_orm = UserORM(
        email=str(validated_data.email),
        name=validated_data.name,
        age=validated_data.age
    )
    db.session.add(user_orm)
    db.session.commit()

    # ドメイン型に変換して返却（デコレータがJSONに変換）
    return UserResponse(
        id=create_user_id(user_orm.id),
        email=create_email(user_orm.email),
        name=user_orm.name,
        age=user_orm.age
    )
```

### エラーハンドリング (Flask)

Flaskでグローバルなエラーハンドラを設定します。

**実装例**:

```python
from flask import Flask, jsonify
from pydantic import ValidationError

app = Flask(__name__)

@app.errorhandler(ValidationError)
def handle_validation_error(e: ValidationError):
    """Pydantic ValidationErrorのグローバルハンドラ

    Args:
        e: ValidationError

    Returns:
        JSONレスポンス（エラー情報）
    """
    return jsonify({
        "error": "バリデーションエラー",
        "details": e.errors()
    }), 422

@app.errorhandler(404)
def handle_not_found(e):
    """404エラーのハンドラ

    Returns:
        JSONレスポンス（エラー情報）
    """
    return jsonify({"error": "リソースが見つかりません"}), 404

@app.errorhandler(500)
def handle_internal_error(e):
    """500エラーのハンドラ

    Returns:
        JSONレスポンス（エラー情報）
    """
    return jsonify({"error": "内部サーバーエラー"}), 500
```

## Django統合パターン

DjangoはカスタムフィールドやシリアライザでPydanticモデルを統合できます。

### 基本パターン (Django)

**特徴**:
- Django ORMのカスタムフィールドでドメイン型を使用
- Django REST frameworkのシリアライザと統合
- Djangoの既存機能を活用

**実装例**:

```python
from typing import NewType, Annotated
from pydantic import Field, TypeAdapter
from django.db import models
from django.core.exceptions import ValidationError as DjangoValidationError

# ドメイン型の定義
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
            raise DjangoValidationError(f"無効なUserId: {e}")

    def to_python(self, value):
        """Pythonオブジェクトへの変換"""
        if isinstance(value, UserId):
            return value
        if value is None:
            return value
        try:
            return create_user_id(int(value))
        except Exception as e:
            raise DjangoValidationError(f"無効なUserId: {e}")

    def get_prep_value(self, value):
        """データベースへの保存時の処理"""
        if value is None:
            return value
        return int(value)

class EmailField(models.EmailField):
    """Email型のDjangoフィールド

    データベースからの読み込み時に自動的にEmail型に変換します。
    """

    def from_db_value(self, value, expression, connection):
        """データベースからの読み込み時の処理"""
        if value is None:
            return value
        try:
            return create_email(value)
        except Exception as e:
            raise DjangoValidationError(f"無効なEmail: {e}")

    def to_python(self, value):
        """Pythonオブジェクトへの変換"""
        if isinstance(value, Email):
            return value
        if value is None:
            return value
        try:
            return create_email(str(value))
        except Exception as e:
            raise DjangoValidationError(f"無効なEmail: {e}")

    def get_prep_value(self, value):
        """データベースへの保存時の処理"""
        if value is None:
            return value
        return str(value)

# Djangoモデル
class User(models.Model):
    """ユーザーモデル

    カスタムフィールドを使用してドメイン型を扱います。
    """
    id = UserIdField(primary_key=True)
    email = EmailField(unique=True, max_length=255)
    name = models.CharField(max_length=100)
    age = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.name
```

### Django REST frameworkとの統合

Django REST frameworkのシリアライザとPydanticモデルを統合します。

**実装例**:

```python
from rest_framework import serializers, viewsets, status
from rest_framework.response import Response
from pydantic import BaseModel, ValidationError as PydanticValidationError

# Pydanticモデル
class UserResponse(BaseModel):
    """ユーザーレスポンスモデル"""
    id: UserId
    email: Email
    name: str
    age: int | None = None

# Django REST frameworkシリアライザ
class UserSerializer(serializers.ModelSerializer):
    """ユーザーシリアライザ

    Django ORMモデルとPydanticモデルの相互変換を担当します。
    """
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'age']

    def to_representation(self, instance):
        """ORMモデルからPydanticモデルへ変換

        Args:
            instance: Djangoモデルインスタンス

        Returns:
            シリアライズされた辞書
        """
        # Pydanticモデルを経由してシリアライズ
        user_response = UserResponse(
            id=instance.id,  # すでにUserId型
            email=instance.email,  # すでにEmail型
            name=instance.name,
            age=instance.age
        )
        return user_response.model_dump()

# ViewSet
class UserViewSet(viewsets.ModelViewSet):
    """ユーザーViewSet

    CRUDエンドポイントを提供します。
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        """新規ユーザーを作成

        Args:
            request: リクエストオブジェクト

        Returns:
            レスポンスオブジェクト
        """
        try:
            # Pydanticモデルでバリデーション
            email = create_email(request.data['email'])
            name = request.data['name']
            age = request.data.get('age')

            # Djangoモデルで作成
            user = User.objects.create(email=email, name=name, age=age)

            # シリアライザでレスポンス生成
            serializer = self.get_serializer(user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except PydanticValidationError as e:
            return Response({"errors": e.errors()}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

### フォームバリデーション

Djangoフォームとドメイン型を統合します。

**実装例**:

```python
from django import forms
from pydantic import ValidationError as PydanticValidationError

class UserForm(forms.ModelForm):
    """ユーザーフォーム

    Djangoフォームでドメイン型のバリデーションを実行します。
    """
    class Meta:
        model = User
        fields = ['email', 'name', 'age']

    def clean_email(self):
        """emailフィールドのカスタムバリデーション

        Returns:
            バリデーション済みのEmail型

        Raises:
            forms.ValidationError: バリデーションエラー
        """
        email_value = self.cleaned_data['email']
        try:
            return create_email(email_value)
        except PydanticValidationError as e:
            raise forms.ValidationError(f"無効なメールアドレス: {e}")

    def save(self, commit=True):
        """フォームデータを保存

        Args:
            commit: データベースに保存するかどうか

        Returns:
            保存されたユーザーインスタンス
        """
        user = super().save(commit=False)
        # emailはすでにEmail型に変換済み
        if commit:
            user.save()
        return user
```

## 共通パターン

### ドメイン型の定義

すべてのフレームワークで共通のドメイン型定義パターンです。

**実装例**:

```python
# src/domain/types.py
"""ドメイン型定義モジュール

プロジェクト全体で使用するドメイン型を定義します。
"""

from typing import NewType, Annotated
from pydantic import Field, TypeAdapter

# Level 2: NewType + ファクトリ関数 + TypeAdapter
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
    Annotated[str, Field(
        pattern=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$',
        description="メールアドレス"
    )]
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
```

### レイヤーアーキテクチャ

3層アーキテクチャでのドメイン型の使用パターンです。

```
┌─────────────────────────────────────┐
│     API層（FastAPI/Flask/Django）    │
│  - UserResponse（ドメイン型）        │
│  - UserCreateRequest（ドメイン型）   │
└─────────────────┬───────────────────┘
                  │
                  ↓
┌─────────────────────────────────────┐
│        ドメイン層（ビジネスロジック） │
│  - UserId, Email（ドメイン型）       │
│  - create_user_id(), create_email() │
└─────────────────┬───────────────────┘
                  │
                  ↓
┌─────────────────────────────────────┐
│         ORM層（データベース）         │
│  - UserORM（プリミティブ型）         │
│  - または TypeDecorator/カスタムField │
└─────────────────────────────────────┘
```

### テスト戦略

ドメイン型を使用したテストのベストプラクティスです。

**実装例**:

```python
import pytest
from pydantic import ValidationError

# ドメイン型のテスト
def test_create_user_id_valid():
    """有効なユーザーIDの生成テスト"""
    user_id = create_user_id(1)
    assert isinstance(user_id, int)
    assert user_id == 1

def test_create_user_id_invalid():
    """無効なユーザーIDのテスト"""
    with pytest.raises(ValidationError):
        create_user_id(0)  # 0は無効（gt=0）

    with pytest.raises(ValidationError):
        create_user_id(-1)  # 負の数は無効

def test_create_email_valid():
    """有効なメールアドレスの生成テスト"""
    email = create_email("test@example.com")
    assert isinstance(email, str)
    assert email == "test@example.com"

def test_create_email_invalid():
    """無効なメールアドレスのテスト"""
    with pytest.raises(ValidationError):
        create_email("invalid-email")  # 無効な形式

# APIエンドポイントのテスト（FastAPIの例）
def test_create_user_endpoint(client):
    """ユーザー作成エンドポイントのテスト"""
    response = client.post(
        "/users",
        json={
            "email": "test@example.com",
            "name": "田中太郎",
            "age": 30
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["email"] == "test@example.com"
    assert data["name"] == "田中太郎"

def test_create_user_invalid_email(client):
    """無効なメールアドレスでのユーザー作成テスト"""
    response = client.post(
        "/users",
        json={
            "email": "invalid-email",
            "name": "田中太郎"
        }
    )
    assert response.status_code == 422
    assert "errors" in response.json()
```

---

**関連ドキュメント**:
- [ORM統合ガイド](orm-integration.md)
- [typing-rule.md](../typing-rule.md)
- [CLAUDE.md](../../CLAUDE.md)

**更新履歴**:
- 2025-10-08: 初版作成（Issue #54対応）
