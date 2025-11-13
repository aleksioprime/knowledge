"""
Модуль Pydantic схем для валидации данных.
Содержит схемы для сериализации и десериализации данных API.
"""

from pydantic import BaseModel


class Token(BaseModel):
    """
    Схема ответа с JWT токеном.

    Attributes:
        access_token: JWT токен доступа
        token_type: Тип токена (обычно "bearer")
    """
    access_token: str
    token_type: str


class UserBase(BaseModel):
    """
    Базовая схема пользователя с общими полями.

    Attributes:
        username: Имя пользователя
        full_name: Полное имя пользователя (опционально)
    """
    username: str
    full_name: str | None = None


class UserCreate(UserBase):
    """
    Схема для создания нового пользователя.
    Наследует поля из UserBase и добавляет пароль
    """
    password: str


class User(UserBase):
    """
    Схема пользователя для возврата из API.
    Включает ID пользователя
    """
    id: int

    class Config:
        orm_mode = True


class ItemBase(BaseModel):
    """
    Базовая схема элемента с общими полями
    """
    name: str
    price: float


class ItemCreate(ItemBase):
    """
    Схема для создания нового элемента.
    Наследует все поля из ItemBase без изменений.
    """
    pass


class Item(ItemBase):
    """
    Схема элемента для возврата из API.
    Включает ID и ID владельца
    """
    id: int
    owner_id: int | None = None

    class Config:
        orm_mode = True
