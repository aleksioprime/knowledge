from uuid import UUID
from typing import Generic, TypeVar, List, Annotated

from fastapi import Query
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T] = Field(..., description="Список элементов на текущей странице")
    total: int = Field(..., description="Общее количество элементов")
    limit: int = Field(..., description="Максимальное количество элементов на странице")
    offset: int = Field(..., description="Смещение от начала коллекции")
    has_next: bool = Field(..., description="Есть ли следующая страница")
    has_previous: bool = Field(..., description="Есть ли предыдущая страница")


class BasePaginationParams(BaseModel):
    """ Базовый класс параметров пагинации """
    limit: Annotated[int, Query(alias='limit', gt=0)]
    offset: Annotated[int, Query(alias='offset', ge=0)]
    q: Annotated[str | None, Query(alias='q', description="Поисковый запрос")] = None