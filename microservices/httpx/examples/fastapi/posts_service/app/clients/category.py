# app/clients/category_client.py

import httpx
from fastapi import HTTPException, status
import os


CATEGORIES_SERVICE_URL = os.getenv("CATEGORIES_SERVICE_URL", "http://127.0.0.1:8002")


class CategoryServiceClient:
    """
    Клиент для взаимодействия с Categories Service.
    Оборачивает все httpx-вызовы и обработку ошибок.
    """

    def __init__(self, base_url: str = CATEGORIES_SERVICE_URL):
        self.base_url = base_url
        self._client = httpx.AsyncClient()

    async def validate(self, category_id: int) -> None:
        """
        Проверяет существование категории
        Выбрасывает HTTPException если категория не найдена или сервис недоступен
        """
        try:
            resp = await self._client.get(f"{self.base_url}/categories/{category_id}")
            resp.raise_for_status()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(
                    status_code=400,
                    detail="Категория не найдена",
                )
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Ошибка сервиса категорий: {e.response.text}",
            )

        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Сервис категорий недоступен",
            )

    async def aclose(self):
        """Закрытие http-клиента"""
        await self._client.aclose()
