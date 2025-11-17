"""
Сервис аутентификации и авторизации пользователей.
Обрабатывает логику входа, выхода и обновления токенов.
"""
from redis.asyncio import Redis

from src.core.config import settings
from src.exceptions.base import BaseException
from src.models.user import User
from src.repositories.uow import UnitOfWork
from src.schemas.auth import AuthSchema
from src.schemas.token import TokenSchema, AccessTokenSchema
from src.utils.token import JWTHelper


class AuthService:
    """
    Сервис для управления аутентификацией пользователей
    """

    def __init__(self, uow: UnitOfWork, redis: Redis, jwt_helper: JWTHelper):
        """
        Инициализирует сервис с необходимыми зависимостями
        """
        self.uow = uow
        self.redis = redis
        self.jwt_helper = jwt_helper

    async def login(self, body: AuthSchema) -> TokenSchema:
        """
        Выполняет аутентификацию пользователя и генерирует токены
        """
        async with self.uow:
            # Проверяем учетные данные
            user = await self._login(body)
            # Генерируем access и refresh токены
            tokens = await self._generate_jwt_tokens(user)

        return tokens

    async def refresh(self, refresh_token: str):
        """
        Обновляет access токен, используя валидный refresh токен.
        Проверяет, что refresh токен не отозван и генерирует новый access.
        """
        # Проверяем, что токен не в черном списке
        await self._is_token_valid(refresh_token)
        # Генерируем новый access токен на основе refresh
        new_tokens = self.jwt_helper.refresh_access_token(refresh_token)

        return AccessTokenSchema(
            access_token=new_tokens,
        )

    async def logout(self, refresh_token: str):
        """
        Выполняет выход пользователя из системы.
        Добавляет refresh токен в черный список в Redis.
        """
        # Проверяем валидность токена перед отзывом
        await self._is_token_valid(refresh_token)
        # Добавляем токен в Redis с TTL равным времени его жизни
        await self._revoke_token(
            refresh_token,
            settings.jwt.refresh_token_expire_time
        )

    async def _login(self, body: AuthSchema) -> User:
        """
        Проверяет учетные данные пользователя
        """
        user: User = await self.uow.auth.get_user_by_username(body.username)

        # Проверяем существование пользователя и корректность пароля
        if not user or not user.check_password(body.password):
            raise BaseException('Ошибка имени пользователя или пароля')

        return user

    async def _generate_jwt_tokens(self, user: User) -> TokenSchema:
        """
        Генерирует пару JWT токенов (access и refresh)
        """
        access_token, refresh_token = self.jwt_helper.generate_token_pair(user)
        return TokenSchema(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def _is_token_valid(self, token: str) -> None:
        """
        Проверяет, не был ли токен отозван ранее
        """
        is_revoked = await self.redis.get(name=token)

        # Если токен найден в Redis со значением "revoked" - он отозван
        if is_revoked and is_revoked.decode() == "revoked":
            raise BaseException("Token has been revoked")

    async def _revoke_token(self, token: str, expire_time: int):
        """
        Отзывает токен, добавляя его в Redis черный список.
        Токен автоматически удалится из Redis после истечения TTL.
        """
        await self.redis.set(
            name=token,
            value="revoked",
            ex=expire_time,  # TTL в секундах
        )
