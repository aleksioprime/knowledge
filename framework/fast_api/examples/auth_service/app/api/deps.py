from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.redis import get_redis
from app.core.security import decode_token
from app.models import User
from app.services.sessions import SessionStore

SessionDep = Annotated[AsyncSession, Depends(get_session)]
bearer = HTTPBearer(auto_error=False)


def get_store(redis: Annotated[Redis, Depends(get_redis)]) -> SessionStore:
    return SessionStore(redis, refresh_ttl=settings.refresh_ttl_days * 24 * 3600)


StoreDep = Annotated[SessionStore, Depends(get_store)]


def unauthorized(detail: str = 'Неверный или просроченный токен') -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail=detail, headers={'WWW-Authenticate': 'Bearer'})


async def get_access_payload(
    store: StoreDep, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> dict:
    if credentials is None:
        raise unauthorized('Нет токена')
    payload = decode_token(credentials.credentials, 'access')
    if payload is None:
        raise unauthorized()
    if await store.is_denied(payload['jti']):
        raise unauthorized('Токен отозван')
    if payload['ver'] != await store.token_version(int(payload['sub'])):
        raise unauthorized('Токен отозван')
    return payload


AccessPayload = Annotated[dict, Depends(get_access_payload)]


async def get_current_user(session: SessionDep, payload: AccessPayload) -> User:
    user = await session.get(User, int(payload['sub']))
    if user is None or not user.is_active:
        raise unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_permission(code: str):
    """Зависимость: пропускает, только если у пользователя есть право `code`.

    Права читаются из базы на каждом запросе, поэтому снятая роль действует сразу.
    """

    async def checker(user: CurrentUser) -> User:
        if code not in user.permission_codes:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=f'Нужно право {code}')
        return user

    return checker
