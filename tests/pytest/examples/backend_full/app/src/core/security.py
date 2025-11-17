"""
Модуль безопасности для работы с JWT токенами.
Содержит класс для проверки Bearer токенов.
"""
import http
from typing import Optional

from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.utils.token import JWTHelper


class JWTBearer(HTTPBearer):
    """
    Класс для проверки JWT токенов в заголовках запросов.
    Наследуется от HTTPBearer и выполняет валидацию токенов.
    """

    def __init__(self, auto_error: bool = True):
        """
        Инициализирует JWTBearer
        """
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> dict:
        """
        Проверяет JWT токен из заголовка Authorization.
        Валидирует токен и возвращает декодированный payload
        """
        # Извлекаем credentials из заголовка Authorization
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)

        if not credentials:
            raise HTTPException(
                status_code=http.HTTPStatus.FORBIDDEN,
                detail="Invalid authorization code",
            )

        # Проверяем, что используется Bearer схема
        if not credentials.scheme == "Bearer":
            raise HTTPException(
                status_code=http.HTTPStatus.UNAUTHORIZED,
                detail="Only Bearer token might be accepted",
            )

        # Декодируем и проверяем токен
        decoded_token = self.parse_token(credentials.credentials)
        if not decoded_token:
            raise HTTPException(
                status_code=http.HTTPStatus.FORBIDDEN,
                detail="Invalid or expired token",
            )

        return decoded_token

    @staticmethod
    def parse_token(jwt_token: str) -> Optional[dict]:
        """
        Декодирует JWT токен и возвращает payload
        """
        payload = JWTHelper().decode(jwt_token)
        return payload
