from collections.abc import AsyncIterator, Awaitable, Callable

import httpx
import pytest
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk
from redis.asyncio import Redis

from settings import settings
from testdata.tasks import TASKS_MAPPING

WriteTasks = Callable[[list[dict]], Awaitable[None]]


@pytest.fixture(scope='session')
async def es_client() -> AsyncIterator[AsyncElasticsearch]:
    client = AsyncElasticsearch(settings.elastic_url)
    yield client
    await client.close()


@pytest.fixture(scope='session')
async def redis_client() -> AsyncIterator[Redis]:
    client = Redis.from_url(settings.redis_url)
    yield client
    await client.aclose()


@pytest.fixture(scope='session')
async def http_client() -> AsyncIterator[httpx.AsyncClient]:
    # Сервис запущен отдельно, тесты ходят к нему по сети, как любой клиент
    async with httpx.AsyncClient(base_url=settings.service_url, timeout=10) as client:
        yield client


@pytest.fixture(scope='session', autouse=True)
async def tasks_index(es_client: AsyncElasticsearch) -> None:
    await es_client.indices.delete(index=settings.tasks_index, ignore_unavailable=True)
    await es_client.indices.create(index=settings.tasks_index, mappings=TASKS_MAPPING)


@pytest.fixture(autouse=True)
async def clean_state(tasks_index, es_client: AsyncElasticsearch, redis_client: Redis) -> None:
    """Перед каждым тестом: пустой индекс и пустой кэш, чтобы тесты не влияли друг на друга."""
    await es_client.delete_by_query(
        index=settings.tasks_index, query={'match_all': {}}, refresh=True, conflicts='proceed',
    )
    await redis_client.flushdb()


@pytest.fixture
def es_write_data(es_client: AsyncElasticsearch) -> WriteTasks:
    async def write(tasks: list[dict]) -> None:
        actions = [
            {'_index': settings.tasks_index, '_id': task['id'], '_source': {k: v for k, v in task.items() if k != 'id'}}
            for task in tasks
        ]
        # refresh: без него документ появится в поиске примерно через секунду, и тест станет нестабильным
        _, errors = await async_bulk(es_client, actions, refresh='wait_for', raise_on_error=False)
        assert not errors, errors

    return write
