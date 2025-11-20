"""
Обработчики исключений для FastAPI приложения.
Перехватывают исключения и возвращают корректные HTTP ответы.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette import status

from src.exceptions.base import BaseException
from src.exceptions.auth import UnauthorizedException


def register_exception_handlers(app: FastAPI):
    """
    Регистрирует обработчики исключений в FastAPI приложении.
    Преобразует исключения в понятные JSON ответы для клиента.
    """

    @app.exception_handler(UnauthorizedException)
    async def unauthorized_exception_handler(request: Request, exc: UnauthorizedException):
        """
        Обработчик для исключений аутентификации.
        Возвращает 401 Unauthorized с сообщением об ошибке.
        """
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "detail": str(exc.message),
            },
        )

    @app.exception_handler(BaseException)
    async def request_exception_handler(request: Request, exc: BaseException):
        """
        Обработчик для пользовательских бизнес-исключений.
        Возвращает 400 Bad Request с сообщением об ошибке.
        """
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "detail": str(exc),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """
        Обработчик для всех непредвиденных исключений.
        Возвращает 500 Internal Server Error с информацией об ошибке.
        """
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "detail": str(exc),
                "path": str(request.url),
            },
        )