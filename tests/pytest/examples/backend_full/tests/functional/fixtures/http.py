import pytest
from httpx import AsyncClient, Response
from tests.functional.core.settings import test_settings


@pytest.fixture()
def make_get_request():
    """
    Фикстура для выполнения HTTP GET-запросов с помощью AsyncClient.
    Принимает путь (endpoint) и параметры запроса, возвращает HTTP-ответ.
    """

    async def inner(endpoint: str, params: dict = None) -> Response:
        base_url = test_settings.service.url
        async with AsyncClient(base_url=base_url) as client:
            return await client.get(endpoint, params=params)

    return inner

@pytest.fixture()
def make_post_request():
    """
    Фикстура для выполнения HTTP POST-запросов с помощью AsyncClient.
    Принимает путь (endpoint) и данные запроса, возвращает HTTP-ответ
    """

    async def inner(endpoint: str, json: dict = None, headers: dict = None) -> Response:
        base_url = test_settings.service.url
        async with AsyncClient(base_url=base_url) as client:
            return await client.post(endpoint, json=json, headers=headers)

    return inner