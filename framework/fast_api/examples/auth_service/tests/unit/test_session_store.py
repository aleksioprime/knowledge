import time

import pytest
from fakeredis import FakeAsyncRedis

from app.services.sessions import Rotation, SessionStore

pytestmark = pytest.mark.anyio


@pytest.fixture
async def store():
    redis = FakeAsyncRedis(decode_responses=True)
    yield SessionStore(redis, refresh_ttl=3600)
    await redis.aclose()


async def create_session(store: SessionStore, sid: str = 's1') -> None:
    await store.create(1, sid, 'r1', 'a1', int(time.time()) + 900, 'pytest', '127.0.0.1')


async def test_refresh_rotates_only_once(store):
    await create_session(store)

    assert await store.rotate('s1', 'r1', 'r2', 'a2', int(time.time()) + 900) is Rotation.OK
    assert await store.rotate('s1', 'r1', 'r3', 'a3', int(time.time()) + 900) is Rotation.REUSED
    assert await store.rotate('nope', 'r1', 'r3', 'a3', int(time.time()) + 900) is Rotation.UNKNOWN


async def test_revoke_puts_access_into_denylist_until_exp(store):
    await create_session(store)

    await store.revoke('s1')

    assert await store.is_denied('a1')
    assert 0 < await store.redis.ttl('denylist:a1') <= 900
    assert await store.list_sessions(1) == []


async def test_revoke_all_bumps_token_version(store):
    await create_session(store, 's1')
    await create_session(store, 's2')

    await store.revoke_all(1)

    assert await store.token_version(1) == 1
    assert await store.list_sessions(1) == []
