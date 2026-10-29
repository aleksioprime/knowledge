import os

import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base, get_session
from app.core.redis import get_redis
from app.main import app
from app.services.users import create_user, seed_roles

TEST_DATABASE_URL = os.environ.get('TEST_DATABASE_URL', 'postgresql+asyncpg://auth:auth@localhost:45432/auth_test')
TEST_REDIS_URL = os.environ.get('TEST_REDIS_URL', 'redis://localhost:46379/15')
PASSWORD = 'secret123'


@pytest.fixture
async def sessions():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        await seed_roles(session)
    yield factory
    await engine.dispose()


@pytest.fixture
async def redis():
    redis = Redis.from_url(TEST_REDIS_URL, decode_responses=True)
    await redis.flushdb()
    yield redis
    await redis.aclose()


@pytest.fixture
async def client(sessions, redis):
    async def override_session():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_redis] = lambda: redis
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(sessions):
    async def make(email: str, role: str = 'user') -> None:
        async with sessions() as session:
            await create_user(session, email, PASSWORD, role)

    return make


@pytest.fixture
def login(client):
    async def do_login(email: str, user_agent: str = 'pytest') -> dict:
        response = await client.post(
            '/auth/login', json={'email': email, 'password': PASSWORD}, headers={'User-Agent': user_agent},
        )
        assert response.status_code == 200, response.text
        return response.json()

    return do_login


def bearer(tokens: dict) -> dict:
    return {'Authorization': f'Bearer {tokens["access_token"]}'}
