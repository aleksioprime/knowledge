"""
Модуль для работы с базой данных.
Настройка подключения к PostgreSQL и создание сессий.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

# Формируем URL для подключения к PostgreSQL
DATABASE_URL = (
    f"postgresql://{settings.db.user}:"
    f"{settings.db.password}@{settings.db.host}:"
    f"{settings.db.port}/{settings.db.name}"
)

# Создаем движок SQLAlchemy
engine = create_engine(DATABASE_URL, echo=False)

# Создаем фабрику сессий
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Базовый класс для моделей
Base = declarative_base()


def get_db():
    """
    Генератор сессий базы данных для использования с FastAPI Depends.
    Автоматически закрывает сессию после использования.

    Yields:
        Session: Сессия базы данных SQLAlchemy
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
