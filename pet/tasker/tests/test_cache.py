import pytest

from app.api.deps import LOGIN_ATTEMPTS_PER_MINUTE

pytestmark = pytest.mark.anyio


async def test_stats_are_cached_and_invalidated(client, cache, anna):
    await client.post('/tasks', json={'title': 'Купить хлеб'}, headers=anna)

    response = await client.get('/tasks/stats', headers=anna)
    assert response.json() == {'total': 1, 'done': 0}
    assert await cache.get('stats:user:1') == '{"total":1,"done":0}'

    await client.patch('/tasks/1', json={'done': True}, headers=anna)
    assert await cache.get('stats:user:1') is None

    response = await client.get('/tasks/stats', headers=anna)
    assert response.json() == {'total': 1, 'done': 1}


async def test_login_rate_limit(client, anna):
    # Фикстура anna уже выполнила один вход
    for _ in range(LOGIN_ATTEMPTS_PER_MINUTE - 1):
        response = await client.post('/auth/token', data={'username': 'anna@example.com', 'password': 'wrong'})
        assert response.status_code == 401

    response = await client.post('/auth/token', data={'username': 'anna@example.com', 'password': 'secret123'})
    assert response.status_code == 429
    assert response.headers['Retry-After'] == '60'
