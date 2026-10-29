"""
Основной модуль FastAPI приложения.
Инициализирует приложение и подключает маршруты.
"""
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from redis.asyncio import Redis

from src.db import redis
from src.core.config import settings
from src.exceptions.handlers import register_exception_handlers
from src.api import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения.
    Выполняется при старте и завершении работы приложения.
    """
    # Код выполняется при старте приложения
    redis.redis = Redis(host=settings.redis.host, port=settings.redis.port)
    yield  # Приложение работает

    # Код выполняется при завершении приложения
    # Здесь можно добавить очистку ресурсов
    await redis.redis.close()

# Инициализируем FastAPI приложение с lifespan
app = FastAPI(
    lifespan=lifespan, # Указание жизненного цикла приложения
    title=settings.project_name, # Название приложения
    docs_url="/api/openapi", # URL для документации Swagger
)

# Регистрация обработчиков исключений
register_exception_handlers(app)

# Подключаем роутер с API эндпоинтами
app.include_router(router, prefix="/api")