"""
Pydantic схемы для аутентификации.
Используются для валидации данных входящих запросов и JWT токенов.
"""
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class AuthSchema(BaseModel):
    """
    Схема для аутентификации пользователя.
    Принимает логин и пароль при входе в систему.
    """
    username: str = Field(..., min_length=1, description="Логин пользователя")
    password: str = Field(..., min_length=1, description="Пароль пользователя")


class UserJWT(BaseModel):
    """
    Схема для представления данных пользователя внутри JWT токена.
    Содержит минимально необходимую информацию для авторизации.
    """
    id: UUID = Field(..., alias="sub", description="Уникальный идентификатор пользователя")
    is_admin: bool = Field(False, description="Флаг суперпользователя")

    class Config:
        populate_by_name = True  # Позволяет использовать как 'id', так и 'sub'