"""
Фикстуры для работы с PostgreSQL в тестах.
Создание подключения к БД и фабрики сессий.
"""
import pytest
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from core.settings import test_settings



@pytest.fixture(scope='session')
async def db_engine():
    """Создает асинхронный движок для подключения к тестовой БД"""
    engine = create_async_engine(
        test_settings.postgres.dsn,
        echo=False,
        future=True
    )
    yield engine
    await engine.dispose()


@pytest.fixture(scope='session')
async def db_session_maker(db_engine):
    """Создает фабрику для создания асинхронных сессий БД"""
    session_maker = async_sessionmaker(
        db_engine,
        expire_on_commit=False,
        class_=AsyncSession
    )
    return session_maker