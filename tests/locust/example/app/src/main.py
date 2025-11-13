"""
Основной модуль FastAPI приложения.
Инициализирует приложение, создает таблицы БД и подключает маршруты.
"""

from fastapi import FastAPI
from .api import router
from .db import Base, engine
from .init_db import init_test_data

# Создаем таблицы в базе данных при запуске приложения
Base.metadata.create_all(bind=engine)

# Инициализируем тестовые данные
init_test_data()

# Инициализируем FastAPI приложение
app = FastAPI(title="Example FastAPI Application")

# Подключаем роутер с API эндпоинтами
app.include_router(router, prefix="/api")