from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.repositories.posts import PostRepository
from app.services.posts import PostService
from app.core.rabbitmq import RabbitMQCategoryValidator, category_validator_instance


async def get_async_db():
    """Зависимость для получения асинхронной сессии базы данных"""
    async with AsyncSessionLocal() as db:
        yield db


def get_post_repository(db: AsyncSession = Depends(get_async_db)) -> PostRepository:
    """Зависимость для получения репозитория постов"""
    return PostRepository(db=db)


def get_category_validator() -> RabbitMQCategoryValidator:
    """
    Зависимость для получения валидатора категорий через RabbitMQ
    Возвращает созданный и инициализированный единственный экземпляр
    Она не создает новый экземпляр RabbitMQCategoryValidator при каждом вызове
    """
    return category_validator_instance


def get_post_service(
        post_repo: PostRepository = Depends(get_post_repository),
        category_validator: RabbitMQCategoryValidator = Depends(get_category_validator)
) -> PostService:
    """Зависимость для получения сервиса постов"""
    return PostService(post_repo=post_repo, category_validator=category_validator)