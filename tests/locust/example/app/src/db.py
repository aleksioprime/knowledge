"""
Модуль для работы с базой данных.
Настройка асинхронного подключения к PostgreSQL и создание сессий.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from .config import settings

# Используем асинхронный DSN из конфигурации
DATABASE_URL = settings.db.dsn

# Создаем асинхронный движок SQLAlchemy
engine = create_async_engine(DATABASE_URL, echo=False)

# Создаем фабрику асинхронных сессий
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Базовый класс для моделей
Base = declarative_base()


async def get_db():
    """
    Асинхронный генератор сессий базы данных для использования с FastAPI Depends.
    Автоматически закрывает сессию после использования
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """
    Инициализация базы данных.
    Создает все таблицы, определенные в моделях.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
