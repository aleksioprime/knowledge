"""
Dependencies для аутентификации и авторизации.
Предоставляет сервис аутентификации и проверку токенов.
"""
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPBearer
from redis.asyncio import Redis

from src.db.redis import get_redis
from src.dependencies.uow import get_unit_of_work
from src.repositories.uow import UnitOfWork
from src.services.auth import AuthService
from src.utils.token import JWTHelper

# Экземпляр HTTPBearer для извлечения токена из заголовка Authorization
http_bearer = HTTPBearer()


async def get_auth_service(
        uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
        redis: Annotated[Redis, Depends(get_redis)],
):
    """
    Создает и возвращает сервис аутентификации.
    Инжектирует зависимости: UnitOfWork, Redis и JWTHelper.
    Используется в эндпоинтах через Depends.
    """
    jwt_helper = JWTHelper()
    return AuthService(uow, redis, jwt_helper)