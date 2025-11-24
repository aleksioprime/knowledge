from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.repositories.posts import PostRepository
from app.services.posts import PostService
from app.clients.category import CategoryServiceClient


async def get_async_db():
    """Зависимость для получения асинхронной сессии базы данных"""
    async with AsyncSessionLocal() as db:
        yield db


def get_post_repository(db: AsyncSession = Depends(get_async_db)) -> PostRepository:
    """Зависимость для получения репозитория постов"""
    return PostRepository(db=db)

async def get_category_client():
    """Зависимость для получения клиента сервиса категорий"""
    client = CategoryServiceClient()
    try:
        yield client
    finally:
        await client.aclose()


def get_post_service(
        post_repo: PostRepository = Depends(get_post_repository),
        category_client: CategoryServiceClient = Depends(get_category_client)
) -> PostService:
    """Зависимость для получения сервиса постов"""
    return PostService(post_repo=post_repo, category_client=category_client)