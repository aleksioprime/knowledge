"""
Модуль API маршрутов.
Содержит все эндпоинты для аутентификации, работы с профилем и элементами
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from . import crud, schemas, security
from .db import get_db
from .dependencies import get_current_user

router = APIRouter()


@router.post("/auth/login", response_model=schemas.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Авторизация пользователя.
    Проверяет учетные данные и возвращает JWT токен
    """
    user = crud.get_user_by_username(db, form_data.username)

    # Простая проверка пароля (в реальном приложении нужно хешировать!)
    if not user or user.hashed_password != form_data.password:
        raise HTTPException(status_code=401, detail="Incorrect credentials")

    token = security.create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/profile", response_model=schemas.User)
def profile(current_user=Depends(get_current_user)):
    """
    Получить профиль текущего авторизованного пользователя
    """
    return current_user


@router.get("/items")
def items(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """
    Получить список всех элементов.
    Требуется авторизация
    """
    return crud.get_items(db)


@router.post("/items", response_model=schemas.Item)
def create_item(
    item: schemas.ItemCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Создать новый элемент.
    Требуется авторизация
    """
    return crud.create_item(db, item, current_user.id)
