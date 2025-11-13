"""
Модуль для работы с базой данных (CRUD операции).
Содержит функции для создания, чтения, обновления и удаления данных.
"""

from sqlalchemy.orm import Session
from . import models, schemas


def get_user_by_username(db: Session, username: str) -> models.User | None:
    """
    Получить пользователя по имени пользователя
    """
    return db.query(models.User).filter(models.User.username == username).first()


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    """
    Создать нового пользователя в базе данных
    """
    db_user = models.User(
        username=user.username,
        full_name=user.full_name,
        hashed_password=user.password,  # В реальном приложении нужно хешировать!
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_items(db: Session, skip: int = 0, limit: int = 100) -> list[models.Item]:
    """
    Получить список элементов из базы данных
    """
    return db.query(models.Item).offset(skip).limit(limit).all()


def create_item(db: Session, item: schemas.ItemCreate, owner_id: int) -> models.Item:
    """
    Создать новый элемент в базе данных
    """
    db_item = models.Item(**item.dict(), owner_id=owner_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item
