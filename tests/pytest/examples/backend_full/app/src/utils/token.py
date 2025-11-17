"""
Утилиты для работы с JWT токенами.
Предоставляет функции для декодирования и валидации токенов.
"""
import time
from datetime import timedelta
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError, decode

from src.schemas.auth import UserJWT
from src.utils.time import utc_now
from src.core.config import settings


class JWTHelper:
    """
    Вспомогательный класс для работы с JWT токенами
    """
    @staticmethod
    def create_token(user_id: str, expiration: timedelta, is_admin: bool = False) -> str:
        """
        Создает JWT токен с указанным сроком действия
        """
        now = utc_now()  # Получаем текущее UTC время
        payload = {
            'sub': user_id,                 # Идентификатор пользователя (subject)
            'iat': now,                     # Время создания токена (issued at)
            'exp': now + expiration,        # Время истечения токена (expiration)
            'is_admin': is_admin,           # Флаг администратора
        }
        # Кодируем payload с помощью секретного ключа
        encoded_jwt = jwt.encode(payload, key=settings.jwt.secret_key, algorithm=settings.jwt.algorithm)
        return encoded_jwt

    def generate_token_pair(self, user: UserJWT) -> tuple[str, str]:
        """
        Генерирует пару access и refresh токенов для пользователя
        """
        user_id = str(user.id)  # Преобразуем UUID в строку
        is_admin = getattr(user, "is_admin", False)  # Безопасно получаем флаг администратора

        # Создаем краткосрочный access токен (обычно 15-30 минут)
        access_token = self.create_token(
            user_id=user_id,
            is_admin=is_admin,
            expiration=settings.jwt.access_token_expire_time,
        )
        # Создаем долгосрочный refresh токен (обычно 7-30 дней)
        refresh_token = self.create_token(
            user_id=user_id,
            is_admin=is_admin,
            expiration=settings.jwt.refresh_token_expire_time,
        )
        return access_token, refresh_token

    def verify(self, token: str) -> dict:
        """
        Проверяет подлинность и валидность JWT токена
        """
        try:
            # Декодируем и валидируем токен
            payload = jwt.decode(
                jwt=token,
                key=settings.jwt.secret_key,
                algorithms=[settings.jwt.algorithm],
            )
        except jwt.ExpiredSignatureError:
            # Токен истек (exp < текущее время)
            raise BaseException('Token has expired')
        except jwt.InvalidTokenError:
            # Невалидная подпись или формат токена
            raise BaseException('Invalid token')

        return payload

    def refresh_access_token(self, refresh_token: str) -> str:
        """
        Обновляет access токен с использованием действующего refresh токена
        """
        # Проверяем валидность refresh токена
        payload = self.verify(refresh_token)

        # Извлекаем данные пользователя из payload
        user_id = payload['sub']
        is_admin = payload.get('is_admin', False)

        # Генерируем новый access токен с теми же правами
        new_access_token = self.create_token(
            user_id=user_id,
            is_admin=is_admin,
            expiration=settings.jwt.access_token_expire_time,
        )

        return new_access_token

    @staticmethod
    def decode(token: str) -> dict | None:
        """
        Декодирует JWT токен и проверяет его срок действия
        """
        try:
            # Декодируем токен (jwt.decode автоматически проверяет exp)
            decoded_token = decode(
                token,
                settings.jwt.secret_key,
                algorithms=[settings.jwt.algorithm],
            )
            # Дополнительная проверка срока действия (избыточна, т.к. decode уже проверяет)
            return decoded_token if decoded_token['exp'] >= time.time() else None
        except (ExpiredSignatureError, InvalidTokenError):
            # Возвращаем None при любых ошибках валидации
            return None