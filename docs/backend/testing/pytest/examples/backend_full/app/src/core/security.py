"""
Модуль безопасности для работы с JWT токенами.
Содержит класс для проверки Bearer токенов.
"""
import http
from typing import Optional

from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.schemas.auth import UserJWT
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

    async def __call__(self, request: Request) -> UserJWT:
        """
        Проверяет JWT токен из заголовка Authorization.
        Валидирует токен и возвращает объект UserJWT с данными пользователя.
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
    def parse_token(jwt_token: str) -> Optional[UserJWT]:
        """
        Декодирует JWT токен и возвращает объект UserJWT.
        Преобразует поле 'sub' из JWT в 'id' через alias в схеме.
        """
        payload = JWTHelper().decode(jwt_token)
        if not payload:
            return None
        return UserJWT(**payload)
