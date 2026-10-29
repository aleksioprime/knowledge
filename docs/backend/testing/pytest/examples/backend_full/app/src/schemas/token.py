"""
Pydantic схемы для JWT токенов.
Определяют формат токенов для запросов и ответов API.
"""
from pydantic import BaseModel, Field


class TokenSchema(BaseModel):
    """
    Схема для передачи пары токенов клиенту
    """
    access_token: str = Field(..., description="Access токен для доступа к защищенным ресурсам")
    refresh_token: str = Field(..., description="Refresh токен для обновления access токена")


class RefreshTokenSchema(BaseModel):
    """
    Схема для запроса обновления access токена
    """
    refresh_token: str = Field(..., description="Refresh токен для обновления")


class AccessTokenSchema(BaseModel):
    """
    Схема для ответа с новым access токеном
    """
    access_token: str = Field(..., description="Новый access токен")
