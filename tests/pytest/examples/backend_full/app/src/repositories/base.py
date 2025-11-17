"""
Базовый репозиторий для работы с базой данных.
Предоставляет общую функциональность для всех репозиториев.
"""
from sqlalchemy.ext.asyncio import AsyncSession


class BaseSQLRepository:
    """
    Базовый класс для всех SQL репозиториев.
    Хранит ссылку на сессию БД и предоставляет базовые методы.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует репозиторий с асинхронной сессией БД SQLAlchemy
        """
        self.session = session