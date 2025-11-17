"""
Главный роутер API.
Объединяет все эндпоинты приложения: ping, auth и items.
"""
from fastapi import APIRouter
from .auth import auth, ping
from .items import item

# Создаем главный роутер для всех API эндпоинтов
router = APIRouter()

# Подключаем роутеры модулей с соответствующими префиксами и тегами
router.include_router(ping.router, prefix="", tags=["ping"])  # Healthcheck эндпоинты
router.include_router(auth.router, prefix="", tags=["auth"])  # Аутентификация
router.include_router(item.router, prefix="/items", tags=["items"])  # Работа с элементами