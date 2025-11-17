"""
Репозиторий для работы с элементами (Items).
Содержит методы CRUD операций для элементов в БД.
"""
from abc import ABC, abstractmethod
from uuid import UUID
import logging
from typing import List, Tuple

from sqlalchemy import select, func, update, delete
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import joinedload

from src.models.item import Item
from src.repositories.base import BaseSQLRepository
from src.schemas.item import ItemQueryParams, ItemCreateSchema, ItemUpdateSchema

logger = logging.getLogger(__name__)


class BaseItemRepository(ABC):
    """
    Абстрактный базовый класс для репозитория элементов.
    Определяет интерфейс для реализации.
    """

    @abstractmethod
    async def get_detail_by_id(self, item_id: UUID) -> Item | None:
        """Получает элемент по его уникальному идентификатору"""
        ...

    @abstractmethod
    async def get_all(self, params: ItemQueryParams) -> Tuple[List[Item], int]:
        """Получает все элементы с учетом параметров запроса"""
        ...

    @abstractmethod
    async def create(self, item: ItemCreateSchema) -> Item:
        """Создает новый элемент в БД"""
        ...

    @abstractmethod
    async def update(self, item_id: UUID, body: ItemUpdateSchema) -> Item:
        """Обновляет существующий элемент по ID"""
        ...

    @abstractmethod
    async def delete(self, item_id: UUID) -> None:
        """Удаляет элемент по ID"""
        ...


class ItemRepository(BaseItemRepository, BaseSQLRepository):
    """
    Репозиторий для работы с элементами в БД
    """

    async def get_detail_by_id(self, item_id: UUID) -> Item | None:
        """
        Получает детальный элемент по его уникальному идентификатору
        """
        stmt = (
            select(Item)
            .where(Item.id == item_id)
            .options(joinedload(Item.group))
        )
        result = await self.session.execute(stmt)
        return result.scalars().one_or_none()

    async def get_all(self, params: ItemQueryParams) -> Tuple[List[Item], int]:
        """
        Получает список всех элементов с пагинацией
        """
        query = (
            select(Item)
            .options(joinedload(Item.group))
        )

        # Фильтры поиска
        query = self._apply_filters(query, params)

        # Сортировка по названию по возрастанию
        query = query.order_by(Item.name.asc())

        # Пагинация
        stmt = (query.offset(params.offset).limit(params.limit))

        # Выполняем запрос и получаем результаты
        result = await self.session.execute(stmt)
        items = result.scalars().all()

        # Получаем общее количество элементов для пагинации
        total = await self._count_all(params)
        return items, total

    async def create(self, item: ItemCreateSchema) -> Item:
        """
        Добавляет новый элемент в текущую сессию БД
        """
        # Создаем объект модели из схемы
        item = Item(**item.model_dump(exclude_unset=True))

        # Добавляем в сессию и синхронизируем изменения с БД
        self.session.add(item)
        await self.session.flush()

        return item

    async def update(self, item_id: UUID, body: ItemUpdateSchema) -> Item:
        """
        Обновляет существующий элемент по ID
        """
        # Получаем данные для обновления из схемы
        update_data = body.model_dump(exclude_unset=True)
        if not update_data:
            raise NoResultFound("Нет данных для обновления")

        stmt = (
            update(Item)
            .where(Item.id == item_id)
            .values(**update_data)
            .returning(Item)
        )

        result = await self.session.execute(stmt)

        item = result.scalar_one_or_none()

        if not item:
            raise NoResultFound(f"Элемент с ID {item_id} не найден")

        return item

    async def delete(self, item_id: UUID) -> None:
        """
        Удаляет элемент по ID
        """
        stmt = (
            delete(Item)
            .where(Item.id == item_id)
            .returning(Item.id)
        )

        result = await self.session.execute(stmt)
        deleted = result.scalar_one_or_none()

        if not deleted:
            raise NoResultFound(f"Элемент с ID {item_id} не найден")

    async def _count_all(self, params: ItemQueryParams) -> int:
        """
        Подсчитывает общее количество элементов с учетом фильтров
        """
        query = select(func.count(Item.id))

        # Применяем фильтры
        stmt = self._apply_filters(query, params)

        # Выполняем запрос и получаем количество
        result = await self.session.execute(stmt)
        return result.scalar_one()

    def _apply_filters(self, query, params: ItemQueryParams):
        """Применяет фильтры поиска"""
        if params.q:
            pattern = f"%{params.q}%"
            query = query.filter(Item.name.ilike(pattern))
        return query