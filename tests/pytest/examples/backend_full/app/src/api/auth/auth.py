"""
API эндпоинты для аутентификации пользователей.
Содержит методы для входа, выхода и обновления токенов.
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from starlette import status

from src.dependencies.auth import get_auth_service
from src.schemas.auth import AuthSchema
from src.schemas.token import TokenSchema, RefreshTokenSchema, AccessTokenSchema
from src.services.auth import AuthService


router = APIRouter()


@router.post(
    path='/login/',
    summary='Вход в аккаунт',
    description='Авторизует пользователя и выдает пару JWT токенов (access и refresh)',
    response_model=TokenSchema,
    status_code=status.HTTP_200_OK,
)
async def login(
        body: AuthSchema,
        service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenSchema:
    """
    Аутентифицирует пользователя по логину и паролю.
    Возвращает пару токенов для авторизованного доступа к API.
    """
    token_pair: TokenSchema = await service.login(body)
    return token_pair


@router.post(
    path='/logout/',
    summary='Выход из аккаунта',
    description='Отзывает токены пользователя, делая их недействительными',
    status_code=status.HTTP_200_OK,
)
async def logout(
        token: RefreshTokenSchema,
        service: Annotated[AuthService, Depends(get_auth_service)],
):
    """
    Выполняет выход пользователя из системы.
    Помечает refresh токен как отозванный в Redis.
    """
    await service.logout(token.refresh_token)


@router.post(
    path='/refresh/',
    summary='Обновление access токена',
    description='Выдает новый access токен на основе валидного refresh токена',
    response_model=AccessTokenSchema,
    status_code=status.HTTP_200_OK,
)
async def refresh_tokens(
        token: RefreshTokenSchema,
        service: Annotated[AuthService, Depends(get_auth_service)],
) -> AccessTokenSchema:
    """
    Обновляет access токен используя refresh токен.
    Используется когда access токен истек, а refresh еще валиден.
    """
    token_pair = await service.refresh(token.refresh_token)
    return token_pair