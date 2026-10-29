"""
Сервис для работы с элементами (Items).
Содержит бизнес-логику для CRUD операций над элементами.
"""
from uuid import UUID
from typing import List

from sqlalchemy.exc import IntegrityError, NoResultFound

from src.exceptions.base import BaseException
from src.exceptions.item import ItemNotFoundException
from src.repositories.uow import UnitOfWork
from src.schemas.pagination import PaginatedResponse
from src.schemas.item import ItemResponseSchema, ItemCreateSchema, ItemUpdateSchema, ItemQueryParams


class ItemService:
    """
    Сервис для управления элементами
    """

    def __init__(self, uow: UnitOfWork):
        """
        Инициализирует сервис с необходимыми зависимостями
        """
        self.uow = uow

    async def get_detail_by_id(self, item_id: UUID) -> ItemResponseSchema:
        """
        Получает элемент по ID
        """
        async with self.uow:
            item = await self.uow.item.get_detail_by_id(item_id)

            if not item:
                raise ItemNotFoundException()

        return ItemResponseSchema.model_validate(item)

    async def get_all(self, params: ItemQueryParams) -> PaginatedResponse[ItemResponseSchema]:
        """
        Получает список элементов с поддержкой фильтрации, сортировки и пагинации
        """
        async with self.uow:
            items, total = await self.uow.item.get_all(params)

        items = [ItemResponseSchema.model_validate(item) for item in items]

        return PaginatedResponse[ItemResponseSchema](
            items=items,
            total=total,
            limit=params.limit,
            offset=params.offset,
            has_next=params.offset + params.limit < total,
            has_previous=params.offset > 0
        )

    async def create(self, body: ItemCreateSchema) -> ItemResponseSchema:
        """
        Создает новый элемент
        """
        async with self.uow:
            try:
                created_item = await self.uow.item.create(body)
                result = ItemResponseSchema.model_validate(created_item)
            except IntegrityError as exc:
                raise BaseException("Ошибка ограничения целостности данных в базе данных") from exc

        return result

    async def update(self, item_id: UUID, body: ItemUpdateSchema) -> ItemResponseSchema:
        """
        Обновляет существующий элемент по ID
        """
        async with self.uow:
            try:
                updated_item = await self.uow.item.update(item_id, body)
                result = ItemResponseSchema.model_validate(updated_item)
            except NoResultFound as exc:
                raise ItemNotFoundException() from exc

        return result

    async def delete(self, item_id: UUID) -> None:
        """
        Удаляет элемент по ID
        """
        async with self.uow:
            try:
                await self.uow.item.delete(item_id)
            except NoResultFound as exc:
                raise ItemNotFoundException() from exc