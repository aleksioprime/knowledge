"""
Healthcheck эндпоинты для проверки работоспособности сервисов.
Позволяет проверить состояние web-сервера, PostgreSQL и Redis.
"""
from fastapi import APIRouter, Depends, HTTPException
from starlette import status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text

from src.db.postgres import get_db_session
from src.db.redis import get_redis

router = APIRouter()


@router.get("/ping/", status_code=status.HTTP_200_OK)
async def ping():
    """
    Простая проверка работоспособности web-сервера.
    Возвращает статус "ok" если сервер работает.
    """
    return {"status": "ok", "message": "Server is up and running"}


@router.get("/ping/postgres/", status_code=status.HTTP_200_OK)
async def postgres_health_check(db_session: AsyncSession = Depends(get_db_session)):
    """
    Проверяет подключение к PostgreSQL базе данных.
    Выполняет простой запрос SELECT 1 для проверки связи.
    """
    try:
        # Выполняем простой запрос для проверки соединения
        result = await db_session.execute(text("SELECT 1"))
        if result.scalar() == 1:
            return {"status": "ok", "message": "Postgres is operational"}
    except SQLAlchemyError as e:
        # Возвращаем ошибку 500 при проблемах с БД
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "error", "message": f"Postgres check failed: {str(e)}"},
        )


@router.get("/ping/redis/", status_code=status.HTTP_200_OK)
async def redis_health_check(redis: Redis = Depends(get_redis)):
    """
    Проверяет подключение к Redis.
    Использует команду PING для проверки доступности.
    """
    try:
        # Выполняем ping команду Redis
        if await redis.ping():
            return {"status": "ok", "message": "Redis is operational"}
    except Exception as e:
        # Возвращаем ошибку 500 при проблемах с Redis
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "error", "message": f"Redis check failed: {str(e)}"},
        )