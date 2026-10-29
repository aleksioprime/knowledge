"""
Модуль моделей базы данных SQLAlchemy.
Содержит определения таблиц для пользователей и элементов.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime
from src.app.db import Base


class User(Base):
    """
    Модель пользователя в базе данных
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True)
    full_name = Column(String)
    hashed_password = Column(String)
    disabled = Column(Boolean, default=False)


class Item(Base):
    """
    Модель элемента в базе данных
    """
    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    price = Column(Float)
    owner_id = Column(Integer)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )