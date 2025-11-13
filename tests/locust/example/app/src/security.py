"""
Модуль безопасности для работы с JWT токенами.
Содержит функции для создания и проверки токенов аутентификации
"""

from datetime import datetime, timedelta
from jose import jwt
from .config import settings


def create_access_token(data: dict) -> str:
    """
    Создать JWT токен доступа с указанными данными
    """
    to_encode = data.copy()

    # Устанавливаем время истечения токена
    expire = datetime.utcnow() + settings.jwt.access_token_expire_time
    to_encode.update({"exp": expire})

    # Кодируем токен с использованием секретного ключа
    return jwt.encode(
        to_encode,
        settings.jwt.secret_key,
        algorithm=settings.jwt.algorithm,
    )
