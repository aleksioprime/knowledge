"""
Модуль API маршрутов.
Содержит все эндпоинты для аутентификации, работы с профилем и элементами.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from src.app import crud, schemas, security
from src.app.db import get_db
from src.app.dependencies import get_current_user

router = APIRouter()


@router.post("/auth/login", response_model=schemas.Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Авторизация пользователя.
    Проверяет учетные данные и возвращает JWT токен
    """
    user = await crud.get_user_by_username(db, form_data.username)

    # Простая проверка пароля (в реальном приложении нужно хешировать!)
    if not user or user.hashed_password != form_data.password:
        raise HTTPException(status_code=401, detail="Incorrect credentials")

    token = security.create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/profile", response_model=schemas.User)
async def profile(current_user=Depends(get_current_user)):
    """
    Получить профиль текущего авторизованного пользователя
    """
    return current_user


@router.get("/items")
async def items(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Получить список всех элементов.
    Требуется авторизация
    """
    return await crud.get_items(db)


@router.post("/items", response_model=schemas.Item)
async def create_item(
    item: schemas.ItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Создать новый элемент.
    Требуется авторизация
    """
    return await crud.create_item(db, item, current_user.id)


@router.delete("/items/{item_id}")
async def delete_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Удалить элемент по ID.
    Требуется авторизация
    """
    deleted = await crud.delete_item(db, item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted successfully"}


@router.put("/items/{item_id}", response_model=schemas.Item)
async def update_item(
    item_id: int,
    item_update: schemas.ItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Обновить элемент по ID.
    Требуется авторизация
    """
    updated_item = await crud.update_item(db, item_id, item_update)
    if not updated_item:
        raise HTTPException(status_code=404, detail="Item not found")
    return updated_item


@router.post("/items/delete-batch")
async def delete_items_batch(
    delete_request: schemas.ItemDeleteBatch,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Массовое удаление элементов по списку ID.
    Требуется авторизация
    """
    result = await crud.delete_items_by_ids(db, delete_request.item_ids)
    return {
        "message": f"Deleted {result['deleted']} items",
        "deleted": result["deleted"],
        "not_found": result["not_found"]
    }
