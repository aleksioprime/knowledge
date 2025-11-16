"""
Основной модуль FastAPI приложения.
Инициализирует приложение и подключает маршруты.
"""
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI

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

    yield  # Приложение работает

    # Код выполняется при завершении приложения
    # Здесь можно добавить очистку ресурсов


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

# Точка входа в приложение
if __name__ == "__main__":
    # Запуск Uvicorn-сервера
    uvicorn.run(
        "main:app",  # Указание приложения (main.py:app)
        host=settings.default_host,  # Хост из настроек
        port=settings.default_port,  # Порт из настроек
        reload=True,  # Автоматическая перезагрузка при изменении файлов
    )