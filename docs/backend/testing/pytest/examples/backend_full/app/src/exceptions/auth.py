"""
Исключения для аутентификации и авторизации.
"""
from src.exceptions.base import BaseException


class UnauthorizedException(BaseException):
    """
    Исключение для ошибок аутентификации.
    Возвращает статус 401 Unauthorized.
    Используется когда пользователь не авторизован или учетные данные неверны.
    """
    pass


class InvalidCredentialsException(UnauthorizedException):
    """
    Исключение для неверных учетных данных (логин/пароль).
    """
    def __init__(self):
        super().__init__("Invalid username or password")


class TokenRevokedException(UnauthorizedException):
    """
    Исключение для отозванного токена.
    """
    def __init__(self):
        super().__init__("Token has been revoked")
