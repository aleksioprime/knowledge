"""
Модуль для работы с PostgreSQL базой данных.
Настраивает асинхронный движок, сессии и базовую модель для SQLAlchemy.
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

from src.core.config import settings

# Создаем асинхронный движок для подключения к БД
# echo=True выводит SQL запросы в консоль (для отладки)
engine = create_async_engine(settings.db.dsn, echo=settings.db.show_query, future=True)

# Фабрика для создания асинхронных сессий
# expire_on_commit=False - объекты остаются доступны после коммита
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

# Базовый класс для всех моделей SQLAlchemy
Base = declarative_base()


async def get_db_session() -> AsyncSession:
    """
    Dependency для получения асинхронной сессии базы данных.
    Используется в FastAPI эндпоинтах через Depends.
    Автоматически закрывает сессию после использования.
    """
    async with async_session_maker() as session:
        yield session
