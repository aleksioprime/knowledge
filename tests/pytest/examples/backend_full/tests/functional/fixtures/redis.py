import pytest
from redis.asyncio import Redis

from core.settings import test_settings


@pytest.fixture(scope='session')
async def redis_client():
    """
    Асинхронная фикстура для создания клиента Redis
    """
    client = Redis(host=test_settings.redis.host, port=test_settings.redis.port)
    yield client
    await client.aclose()