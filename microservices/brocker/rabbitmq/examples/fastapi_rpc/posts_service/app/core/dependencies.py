from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.repositories.posts import PostRepository
from app.services.posts import PostService


async def get_async_db():
    """Зависимость для получения асинхронной сессии базы данных"""
    async with AsyncSessionLocal() as db:
        yield db


def get_post_repository(db: AsyncSession = Depends(get_async_db)) -> PostRepository:
    """Зависимость для получения репозитория постов"""
    return PostRepository(db=db)


def get_post_service(
        post_repo: PostRepository = Depends(get_post_repository)
) -> PostService:
    """Зависимость для получения сервиса постов"""
    return PostService(post_repo=post_repo)
