"""
Unit of Work паттерн для управления транзакциями БД.
Обеспечивает атомарность операций и автоматический commit/rollback.
"""
from src.db.postgres import async_session_maker
from src.repositories.auth import AuthRepository
from src.repositories.item import ItemRepository


class UnitOfWork:
    """
    Реализация паттерна Unit of Work для управления транзакциями.
    Автоматически создает репозитории и управляет жизненным циклом сессии
    """

    def __init__(self):
        """Инициализирует UnitOfWork с фабрикой сессий"""
        self.session_factory = async_session_maker

    async def __aenter__(self):
        """
        Создает новую сессию БД и инициализирует репозитории.
        Вызывается при входе в контекстный менеджер
        """
        self.session = self.session_factory()
        # Инициализируем все репозитории с одной сессией
        self.auth = AuthRepository(self.session)
        self.item = ItemRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """
        Завершает работу с сессией: commit или rollback.
        Автоматически откатывает изменения при возникновении исключений
        """
        if exc_type is not None:
            # Если произошла ошибка - откатываем изменения
            await self.rollback()
        else:
            # Если все прошло успешно - сохраняем изменения
            await self.commit()
        # Закрываем сессию в любом случае
        await self.session.close()

    async def commit(self):
        """Фиксирует все изменения в БД"""
        await self.session.commit()

    async def rollback(self):
        """Откатывает все изменения в БД"""
        await self.session.rollback()