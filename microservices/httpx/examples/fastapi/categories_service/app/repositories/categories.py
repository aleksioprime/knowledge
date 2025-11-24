from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.category import Category


class CategoryRepository:
    """Репозиторий для работы с категориями в базе данных"""

    def __init__(self, db: AsyncSession):
        """Инициализация репозитория с сессией базы данных"""
        self.db = db

    async def get_by_id(self, category_id: int) -> Category | None:
        """Получить категорию по ID"""
        result = await self.db.scalar(select(Category).filter(Category.id == category_id))
        return result

    async def get_by_name(self, name: str) -> Category | None:
        """Получить категорию по имени"""
        result = await self.db.scalar(select(Category).filter(Category.name == name))
        return result

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[Category]:
        """Получить все категории с поддержкой пагинации"""
        result = await self.db.scalars(select(Category).offset(skip).limit(limit))
        return result.all()

    async def create(self, name: str) -> Category:
        """Создать новую категорию"""
        db_category = Category(
            name=name,
        )
        self.db.add(db_category)
        await self.db.commit()
        await self.db.refresh(db_category)
        return db_category