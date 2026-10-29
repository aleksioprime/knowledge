from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.api.deps import AccessPayload, CurrentUser, SessionDep, StoreDep, unauthorized
from app.core.security import create_access_token, create_refresh_token, decode_token, password_hash
from app.models import User
from app.schemas import (
    Credentials, LoginRecordOut, MeOut, PasswordChangeIn, RefreshIn, SessionOut, TokenPair, UserOut,
)
from app.services import users
from app.services.sessions import Rotation

router = APIRouter(prefix='/auth', tags=['auth'])


def client_info(request: Request) -> tuple[str, str]:
    user_agent = request.headers.get('user-agent', '')[:512]
    ip = request.client.host if request.client else ''
    return user_agent, ip


@router.post('/register', status_code=status.HTTP_201_CREATED)
async def register(session: SessionDep, data: Credentials) -> UserOut:
    if await users.get_by_email(session, data.email):
        raise HTTPException(status.HTTP_409_CONFLICT, detail='Email уже занят')
    user = await users.create_user(session, data.email, data.password)
    return UserOut(id=user.id, email=user.email, roles=user.role_names)


@router.post('/login')
async def login(request: Request, session: SessionDep, store: StoreDep, data: Credentials) -> TokenPair:
    user_agent, ip = client_info(request)
    user = await users.authenticate(session, data.email, data.password, user_agent, ip)
    if user is None:
        raise unauthorized('Неверный email или пароль')

    sid = uuid4().hex
    access = create_access_token(user.id, sid, user.role_names, await store.token_version(user.id))
    refresh = create_refresh_token(user.id, sid)
    await store.create(user.id, sid, refresh.jti, access.jti, access.exp, user_agent, ip)
    return TokenPair(access_token=access.token, refresh_token=refresh.token)


@router.post('/refresh')
async def refresh(session: SessionDep, store: StoreDep, data: RefreshIn) -> TokenPair:
    payload = decode_token(data.refresh_token, 'refresh')
    if payload is None:
        raise unauthorized()
    user = await session.get(User, int(payload['sub']))
    if user is None or not user.is_active:
        raise unauthorized()

    sid = payload['sid']
    access = create_access_token(user.id, sid, user.role_names, await store.token_version(user.id))
    new_refresh = create_refresh_token(user.id, sid)
    result = await store.rotate(sid, payload['jti'], new_refresh.jti, access.jti, access.exp)
    if result is Rotation.REUSED:
        # Этим refresh-токеном уже пользовались: его копия у кого-то ещё.
        # Не знаем, у кого настоящая, поэтому закрываем сессию целиком.
        await store.revoke(sid)
        raise unauthorized('Refresh-токен уже использован, сессия завершена')
    if result is Rotation.UNKNOWN:
        raise unauthorized('Сессия завершена')
    return TokenPair(access_token=access.token, refresh_token=new_refresh.token)


@router.post('/logout', status_code=status.HTTP_204_NO_CONTENT)
async def logout(store: StoreDep, payload: AccessPayload) -> None:
    await store.revoke(payload['sid'])
    # access этой сессии store.revoke уже положил в denylist, но после ротации
    # клиент мог прийти с более старым — запрещаем и его
    await store.deny_access(payload['jti'], payload['exp'])


@router.post('/logout/all', status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(store: StoreDep, payload: AccessPayload) -> None:
    await store.revoke_all(int(payload['sub']))


@router.post('/password', status_code=status.HTTP_204_NO_CONTENT)
async def change_password(session: SessionDep, store: StoreDep, user: CurrentUser, data: PasswordChangeIn) -> None:
    if not password_hash.verify(data.old_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='Неверный текущий пароль')
    user.password_hash = password_hash.hash(data.new_password)
    await session.commit()
    await store.revoke_all(user.id)


@router.get('/me')
async def me(user: CurrentUser) -> MeOut:
    return MeOut(id=user.id, email=user.email, roles=user.role_names, permissions=sorted(user.permission_codes))


@router.get('/history')
async def history(
    session: SessionDep,
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[LoginRecordOut]:
    return await users.login_history(session, user.id, limit, offset)


@router.get('/sessions')
async def sessions(store: StoreDep, payload: AccessPayload) -> list[SessionOut]:
    return [
        SessionOut(
            sid=s['sid'], user_agent=s['user_agent'], ip=s['ip'],
            created_at=int(s['created_at']), current=s['sid'] == payload['sid'],
        )
        for s in await store.list_sessions(int(payload['sub']))
    ]
