import os

import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.cache import get_cache
from app.core.database import Base, get_session
from app.main import app

TEST_DATABASE_URL = os.environ.get(
    'TEST_DATABASE_URL', 'postgresql+asyncpg://tasker:tasker@localhost:5432/tasker_test'
)
TEST_REDIS_URL = os.environ.get('TEST_REDIS_URL', 'redis://localhost:6379/15')


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
async def cache():
    cache = Redis.from_url(TEST_REDIS_URL, decode_responses=True)
    await cache.flushdb()
    yield cache
    await cache.aclose()


@pytest.fixture
async def sessions():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def client(cache, sessions):
    async def get_test_session():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_cache] = lambda: cache
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        yield client
    app.dependency_overrides.clear()


async def login(client: AsyncClient, email: str) -> dict[str, str]:
    await client.post('/auth/register', json={'email': email, 'password': 'secret123'})
    response = await client.post('/auth/token', data={'username': email, 'password': 'secret123'})
    return {'Authorization': f'Bearer {response.json()["access_token"]}'}


@pytest.fixture
async def anna(client):
    return await login(client, 'anna@example.com')


@pytest.fixture
async def boris(client):
    return await login(client, 'boris@example.com')
