import asyncio
import pytest

from tests.functional.utils.waiters import wait_for_postgres, wait_for_redis, wait_for_app


pytest_plugins = [
    'tests.functional.fixtures.http',
]


@pytest.fixture(scope='session', autouse=True)
def wait_for_services():
    """
    Ожидает доступности всех необходимых сервисов перед запуском тестов
    """
    wait_for_postgres()
    wait_for_redis()
    wait_for_app()


@pytest.fixture(scope='session', autouse=True)
def event_loop():
    """
    Создает и предоставляет asyncio event loop для всех тестов в сессии
    """

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop

    loop.close()
