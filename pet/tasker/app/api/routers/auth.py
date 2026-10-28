from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, SessionDep, limit_login_attempts
from app.core.security import create_access_token
from app.schemas import Token, UserCreate, UserRead
from app.services import users

router = APIRouter(prefix='/auth', tags=['auth'])


@router.post('/register', status_code=status.HTTP_201_CREATED)
async def register(session: SessionDep, data: UserCreate) -> UserRead:
    try:
        user = await users.create_user(session, data)
    except users.EmailTakenError:
        raise HTTPException(status.HTTP_409_CONFLICT, detail='Пользователь с таким email уже есть')
    return UserRead.model_validate(user)


@router.post('/token', dependencies=[Depends(limit_login_attempts)])
async def login(session: SessionDep, form: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    # В форме OAuth2 поле называется username, но мы передаём в него email
    user = await users.authenticate(session, form.username, form.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail='Неверный email или пароль')
    return Token(access_token=create_access_token(user.id))


@router.get('/me')
async def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)
