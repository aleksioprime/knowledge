"""
Pydantic схемы для работы с элементами (Items).
Содержит схемы для создания, обновления и получения элементов
и параметры запроса для фильтрации и сортировки.
"""
from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from src.schemas.pagination import BasePaginationParams
from src.schemas.sort import BaseSortParams


class ItemQueryParams(BasePaginationParams, BaseSortParams):
    """
    Параметры запроса для фильтрации и поиска элементов
    """
    name: Optional[str] = Field(None, description="Поиск по названию")
    min_price: Optional[float] = Field(None, ge=0, description="Минимальная цена")
    max_price: Optional[float] = Field(None, ge=0, description="Максимальная цена")
    group_id: Optional[UUID] = Field(None, description="Фильтр по группе")
    tag_ids: Optional[list[UUID]] = Field(None, description="Фильтр по тегам")


class GroupSchema(BaseModel):
    """
    Схема группы для вложенного представления в Item.
    """
    id: UUID
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class TagSchema(BaseModel):
    """
    Схема тега для вложенного представления в Item.
    """
    id: UUID
    name: str

    class Config:
        from_attributes = True


class ItemCreateSchema(BaseModel):
    """
    Схема для создания нового элемента.
    Принимает только необходимые поля.
    """
    name: str = Field(..., min_length=1, max_length=100, description="Название элемента")
    price: float = Field(..., gt=0, description="Цена элемента")
    group_id: Optional[UUID] = Field(None, description="ID группы, к которой относится элемент")


class ItemUpdateSchema(BaseModel):
    """
    Схема для обновления элемента.
    Все поля опциональны - обновляются только переданные.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Название элемента")
    price: Optional[float] = Field(None, gt=0, description="Цена элемента")
    group_id: Optional[UUID] = Field(None, description="ID группы")


class ItemResponseSchema(BaseModel):
    """
    Схема для возврата данных элемента.
    Включает все поля, включая связанные объекты.
    """
    id: UUID
    name: str
    price: float
    group: Optional[GroupSchema] = None
    tags: list[TagSchema] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
