import asyncio
import pytest


pytest_plugins = [
    'fixtures.http',
    'fixtures.postgres',
    'fixtures.setup',
]

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
