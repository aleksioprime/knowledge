import pytest
from httpx import AsyncClient, Response
from core.settings import test_settings


@pytest.fixture(scope='session')
def make_get_request():
    """
    Фикстура для выполнения HTTP GET-запросов с помощью AsyncClient.
    Принимает путь (endpoint), параметры запроса и заголовки, возвращает HTTP-ответ.
    """

    async def inner(endpoint: str, params: dict = None, headers: dict = None) -> Response:
        base_url = test_settings.service.url
        async with AsyncClient(base_url=base_url) as client:
            return await client.get(endpoint, params=params, headers=headers)

    return inner

@pytest.fixture(scope='session')
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


@pytest.fixture(scope='session')
def make_patch_request():
    """
    Фикстура для выполнения HTTP PATCH-запросов с помощью AsyncClient.
    Принимает путь (endpoint) и данные запроса, возвращает HTTP-ответ
    """

    async def inner(endpoint: str, json: dict = None, headers: dict = None) -> Response:
        base_url = test_settings.service.url
        async with AsyncClient(base_url=base_url) as client:
            return await client.patch(endpoint, json=json, headers=headers)

    return inner


@pytest.fixture(scope='session')
def make_delete_request():
    """
    Фикстура для выполнения HTTP DELETE-запросов с помощью AsyncClient.
    Принимает путь (endpoint) и заголовки, возвращает HTTP-ответ
    """

    async def inner(endpoint: str, headers: dict = None) -> Response:
        base_url = test_settings.service.url
        async with AsyncClient(base_url=base_url) as client:
            return await client.delete(endpoint, headers=headers)

    return inner