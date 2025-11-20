"""
Исключения для работы с элементами (Items).
"""
from .base import BaseException


class ItemNotFoundException(BaseException):
    """
    Исключение, выбрасываемое когда элемент не найден.
    Возвращает HTTP 404 Not Found.
    """
    def __init__(self, message: str = "Элемент с указанным ID не найден"):
        super().__init__(message)
