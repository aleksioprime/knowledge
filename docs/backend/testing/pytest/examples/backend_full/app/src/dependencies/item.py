"""
Dependencies для работы с элементами (Items).
Предоставляет сервисы для использования в API эндпоинтах.
"""
from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, Query

from src.schemas.pagination import BasePaginationParams
from src.schemas.sort import BaseSortParams
from src.schemas.item import ItemQueryParams
from src.dependencies.pagination import get_pagination_params
from src.dependencies.sort import get_sort_params
from src.dependencies.uow import get_unit_of_work
from src.repositories.uow import UnitOfWork
from src.services.item import ItemService



def get_item_params(
        pagination: Annotated[BasePaginationParams, Depends(get_pagination_params)],
        sort: Annotated[BaseSortParams, Depends(get_sort_params)],
        name: Optional[str] = Query(None, description="Фильтр по названию"),
        min_price: Optional[float] = Query(None, ge=0, description="Минимальная цена"),
        max_price: Optional[float] = Query(None, ge=0, description="Максимальная цена"),
        group_id: Optional[UUID] = Query(None, description="Фильтр по ID группы"),
        tag_ids: Optional[list[UUID]] = Query(None, description="Фильтр по ID тегов"),
) -> ItemQueryParams:
    """
    Получает query-параметры фильтрации для элементов
    """
    return ItemQueryParams(
        limit=pagination.limit,
        offset=pagination.offset,
        q=pagination.q,
        sort_by=sort.sort_by,
        order=sort.order,
        name=name,
        min_price=min_price,
        max_price=max_price,
        group_id=group_id,
        tag_ids=tag_ids,
    )


async def get_item_service(
        uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> ItemService:
    """
    Создает и возвращает сервис для работы с элементами
    """
    return ItemService(uow)
