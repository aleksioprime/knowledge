"""
API эндпоинты для работы с элементами.
Содержит CRUD операции для управления элементами.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.dependencies.item import get_item_service
from src.dependencies.item import get_item_params
from src.dependencies.permissions import permission_required
from src.schemas.auth import UserJWT
from src.schemas.pagination import PaginatedResponse
from src.schemas.item import (
    ItemCreateSchema,
    ItemUpdateSchema,
    ItemResponseSchema,
    ItemQueryParams
)
from src.services.item import ItemService

router = APIRouter()


@router.get(
    path="/",
    summary="Получить список элементов",
    description="Возвращает список элементов с поддержкой сортировки, фильтрации, пагинации",
    response_model=PaginatedResponse[ItemResponseSchema],
    status_code=status.HTTP_200_OK,
)
async def get_items(
    params: Annotated[ItemQueryParams, Depends(get_item_params)],
    service: Annotated[ItemService, Depends(get_item_service)]
) -> PaginatedResponse[ItemResponseSchema]:
    """
    Получает список элементов с возможностью фильтрации.
    Поддерживает поиск по названию, фильтрацию по цене, группе и тэгу.
    Поддерживает сортировку по указанным полям.
    """
    items = await service.get_all(params)
    return items


@router.get(
    path="/{item_id}/",
    summary="Получить элемент по ID",
    description="Возвращает информацию об элементе по его уникальному идентификатору",
    response_model=ItemResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def get_item(
        item_id: UUID,
        service: Annotated[ItemService, Depends(get_item_service)],
) -> ItemResponseSchema:
    """
    Получает детальную информацию об элементе.
    Включает связанные данные: группу и теги.
    """
    item = await service.get_detail_by_id(item_id)
    return item


@router.post(
    path="/",
    summary="Создать новый элемент",
    description="Создает новый элемент с указанными данными",
    response_model=ItemResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_item(
        body: ItemCreateSchema,
        service: Annotated[ItemService, Depends(get_item_service)],
        user: Annotated[UserJWT, Depends(permission_required())],
) -> ItemResponseSchema:
    """
    Создает новый элемент в системе.
    Требует название, цену и опционально ID группы.
    """
    created_item = await service.create(body)
    return created_item


@router.patch(
    path="/{item_id}/",
    summary="Обновить элемент",
    description="Обновляет данные элемента по его ID",
    response_model=ItemResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def update_item(
        item_id: UUID,
        body: ItemUpdateSchema,
        service: Annotated[ItemService, Depends(get_item_service)],
        user: Annotated[UserJWT, Depends(permission_required())],
) -> ItemResponseSchema:
    """
    Обновляет существующий элемент.
    Можно обновить название, цену или группу.
    """
    updated_item = await service.update(item_id, body)
    return updated_item


@router.delete(
    path="/{item_id}/",
    summary="Удалить элемент",
    description="Удаляет элемент по его ID",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_item(
        item_id: UUID,
        service: Annotated[ItemService, Depends(get_item_service)],
        user: Annotated[UserJWT, Depends(permission_required())],
) -> None:
    """
    Удаляет элемент из системы.
    После удаления элемент невозможно восстановить.
    """
    await service.delete(item_id)
