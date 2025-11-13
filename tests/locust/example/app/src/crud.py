"""
Модуль для работы с базой данных (CRUD операции).
Содержит функции для создания, чтения, обновления и удаления данных
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from . import models, schemas


async def get_user_by_username(db: AsyncSession, username: str) -> models.User | None:
    """
    Получить пользователя по имени пользователя
    """
    result = await db.execute(
        select(models.User).where(models.User.username == username)
    )
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user: schemas.UserCreate) -> models.User:
    """
    Создать нового пользователя в базе данных
    """
    db_user = models.User(
        username=user.username,
        full_name=user.full_name,
        hashed_password=user.password,  # В реальном приложении нужно хешировать!
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def get_items(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[models.Item]:
    """
    Получить список элементов из базы данных
    """
    result = await db.execute(
        select(models.Item).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def create_item(db: AsyncSession, item: schemas.ItemCreate, owner_id: int) -> models.Item:
    """
    Создать новый элемент в базе данных
    """
    db_item = models.Item(**item.model_dump(), owner_id=owner_id)
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    return db_item


async def delete_item(db: AsyncSession, item_id: int) -> bool:
    """
    Удалить элемент из базы данных по ID
    """
    result = await db.execute(
        select(models.Item).where(models.Item.id == item_id)
    )
    db_item = result.scalar_one_or_none()

    if db_item is None:
        return False

    await db.delete(db_item)
    await db.commit()
    return True


async def delete_items_by_ids(db: AsyncSession, item_ids: list[int]) -> dict[str, int]:
    """
    Удалить несколько элементов из базы данных по списку ID
    """
    if not item_ids:
        return {"deleted": 0, "not_found": 0}

    # Получаем все items с указанными ID
    result = await db.execute(
        select(models.Item).where(models.Item.id.in_(item_ids))
    )
    items_to_delete = result.scalars().all()

    # Удаляем найденные items
    deleted_count = 0
    for item in items_to_delete:
        await db.delete(item)
        deleted_count += 1

    await db.commit()

    not_found_count = len(item_ids) - deleted_count

    return {
        "deleted": deleted_count,
        "not_found": not_found_count
    }
