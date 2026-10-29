"""
Модуль Pydantic схем для валидации данных.
Содержит схемы для сериализации и десериализации данных API.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class Token(BaseModel):
    """
    Схема ответа с JWT токеном
    """
    access_token: str
    token_type: str


class UserBase(BaseModel):
    """
    Базовая схема пользователя с общими полями
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

    model_config = ConfigDict(from_attributes=True)


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


class ItemUpdate(BaseModel):
    """
    Схема для обновления элемента.
    Все поля опциональны - обновляются только переданные поля
    """
    name: str | None = None
    price: float | None = None


class Item(ItemBase):
    """
    Схема элемента для возврата из API.
    Включает ID, ID владельца и временные метки
    """
    id: int
    owner_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ItemDeleteBatch(BaseModel):
    """
    Схема для массового удаления элементов по списку ID
    """
    item_ids: list[int]
