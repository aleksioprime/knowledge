import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_cache
from app.core.database import get_session
from app.core.security import decode_access_token
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/token')

SessionDep = Annotated[AsyncSession, Depends(get_session)]
CacheDep = Annotated[Redis, Depends(get_cache)]

LOGIN_ATTEMPTS_PER_MINUTE = 5


async def get_current_user(session: SessionDep, token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    user_id = decode_access_token(token)
    user = await session.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Неверный или просроченный токен',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def limit_login_attempts(request: Request, cache: CacheDep) -> None:
    # Фиксированное окно: счётчик попыток с одного IP за текущую минуту
    window = 60
    key = f'rate:login:{request.client.host}:{int(time.time() // window)}'
    async with cache.pipeline() as pipe:
        pipe.incr(key)
        pipe.expire(key, window, nx=True)
        attempts, _ = await pipe.execute()
    if attempts > LOGIN_ATTEMPTS_PER_MINUTE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail='Слишком много попыток входа, попробуйте через минуту',
            headers={'Retry-After': str(window)},
        )
