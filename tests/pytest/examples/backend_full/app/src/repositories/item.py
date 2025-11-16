from abc import ABC, abstractmethod
from uuid import UUID
import logging

from sqlalchemy import select, func
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import joinedload

from src.models.item import Item
from src.repositories.base import BaseSQLRepository
from src.schemas.item import ItemQueryParams, ItemUpdateSchema

logger = logging.getLogger(__name__)


class BaseItemRepository(ABC):

    @abstractmethod
    async def get_all(self, params: ItemQueryParams):
        ...


class ItemRepository(BaseItemRepository, BaseSQLRepository):

    async def get_by_id(self, Item_id: UUID) -> Item | None:
        """
        Получает элемент по ID
        """
        query = select(Item).filter(Item.id == Item_id).options(joinedload(Item.group))
        result = await self.session.execute(query)
        return result.scalars().one_or_none()

    async def create(self, item: Item) -> None:
        """
        Добавляет новый элемент в текущую сессию
        """
        self.session.add(item)

    async def update(self, item_id: UUID, body: ItemUpdateSchema) -> Item:
        """
        Обновляет элемент по ID
        """
        update_data = {key: value for key, value in body.dict(exclude_unset=True).items()}
        if not update_data:
            raise NoResultFound("Нет данных для обновления")

        item = await self.get_by_id(item_id)
        if not item:
            raise NoResultFound(f"Элемент с ID {item_id} не найдено")
        # Обновление полей
        for key, value in update_data.items():
            setattr(item, key, value)

        await self.session.flush()
        return item

    async def delete(self, item_id: UUID) -> None:
        """
        Удаляет элемент по ID
        """
        item = await self.get_by_id(item_id)
        if not item:
            raise NoResultFound(f"Элемент с ID {item_id} не найдено")

        await self.session.delete(item)