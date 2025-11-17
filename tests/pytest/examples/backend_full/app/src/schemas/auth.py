"""
Pydantic схемы для аутентификации.
Используются для валидации данных входящих запросов и JWT токенов.
"""
from uuid import UUID
from pydantic import BaseModel, Field


class AuthSchema(BaseModel):
    """
    Схема для аутентификации пользователя.
    Принимает логин и пароль при входе в систему.
    """
    username: str = Field(..., description="Логин пользователя")
    password: str = Field(..., description="Пароль пользователя")


class UserJWT(BaseModel):
    """
    Схема для представления данных пользователя внутри JWT токена.
    Содержит минимально необходимую информацию для авторизации.
    """
    id: UUID = Field(..., description="Уникальный идентификатор пользователя")
    is_admin: bool = Field(False, description="Флаг суперпользователя")