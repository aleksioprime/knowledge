"""
Dependency для предоставления Unit of Work в эндпоинтах.
Используется через FastAPI Depends для инъекции зависимостей.
"""
from src.repositories.uow import UnitOfWork


async def get_unit_of_work():
    """
    Создает и возвращает новый экземпляр UnitOfWork.
    Используется как зависимость в FastAPI эндпоинтах.
    """
    return UnitOfWork()