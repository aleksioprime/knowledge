"""
Репозиторий для работы с пользователями и аутентификацией.
Содержит методы для получения данных пользователей из БД.
"""
from abc import ABC, abstractmethod
from typing import List
from uuid import UUID

from sqlalchemy import select

from src.models.user import User
from src.repositories.base import BaseSQLRepository


class BaseAuthRepository(ABC):
    """
    Абстрактный базовый класс для репозитория аутентификации.
    Определяет интерфейс для реализации.
    """
    ...


class AuthRepository(BaseAuthRepository, BaseSQLRepository):
    """
    Репозиторий для работы с пользователями в базе данных SQLAlchemy
    """

    async def get_user_by_username(self, username: str) -> User | None:
        """
        Получает пользователя по имени пользователя (логину).
        Возвращает None, если пользователь не найден.
        """
        query = select(User).filter_by(username=username)
        result = await self.session.scalars(query)
        return result.one_or_none()