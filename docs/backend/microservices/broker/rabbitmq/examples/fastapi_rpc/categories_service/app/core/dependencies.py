from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.repositories.categories import CategoryRepository
from app.services.categories import CategoryService


async def get_async_db():
    """Зависимость для получения асинхронной сессии базы данных"""
    async with AsyncSessionLocal() as db:
        yield db


def get_category_repository(db: AsyncSession = Depends(get_async_db)) -> CategoryRepository:
    """Зависимость для получения репозитория категорий"""
    return CategoryRepository(db=db)


def get_category_service(
        category_repo: CategoryRepository = Depends(get_category_repository)
) -> CategoryService:
    """Зависимость для получения сервиса категорий"""
    return CategoryService(category_repo=category_repo)