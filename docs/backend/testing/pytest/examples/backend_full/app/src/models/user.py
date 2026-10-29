"""
Модель пользователя для системы аутентификации.
Хранит данные пользователей и предоставляет метод проверки пароля.
"""
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from werkzeug.security import check_password_hash

from .base import Base, UUIDMixin, TimestampMixin


class User(UUIDMixin, TimestampMixin, Base):
    """
    Модель пользователя в системе.
    Содержит основную информацию о пользователе и хешированный пароль.
    """
    __tablename__ = 'users'

    # Обязательные поля
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    # Дополнительные поля профиля
    first_name: Mapped[str | None] = mapped_column(String(50))
    last_name: Mapped[str | None] = mapped_column(String(50))

    # Роль администратора
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def check_password(self, password: str) -> bool:
        """
        Проверяет соответствие введенного пароля хешу в БД.
        Использует werkzeug для безопасной проверки хешей.
        """
        return check_password_hash(self.hashed_password, password)

    def __repr__(self) -> str:
        """Строковое представление объекта пользователя"""
        return f"Пользователь: {self.username}"