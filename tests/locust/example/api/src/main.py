"""
Основной модуль FastAPI приложения.
Инициализирует приложение, создает таблицы БД и подключает маршруты.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.app.api import router
from src.app.db import init_db
from src.app.init_db import init_test_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения.
    Выполняется при старте и завершении работы приложения.
    """
    # Код выполняется при старте приложения
    await init_db()  # Создаем таблицы
    await init_test_data()  # Инициализируем тестовые данные

    yield  # Приложение работает

    # Код выполняется при завершении приложения
    # Здесь можно добавить очистку ресурсов


# Инициализируем FastAPI приложение с lifespan
app = FastAPI(
    title="Example FastAPI Application",
    lifespan=lifespan,
)

# Подключаем роутер с API эндпоинтами
app.include_router(router, prefix="/api")