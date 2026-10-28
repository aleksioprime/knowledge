import pytest
from sqlalchemy import delete

from src import service
from src.config import settings
from src.models import Link
from src.utils.shortener import ALPHABET, CODE_LENGTH, generate_code

pytestmark = pytest.mark.anyio

URL = 'https://example.com/very/long/path'


async def shorten(client, url: str = URL) -> str:
    response = await client.post('/api/links', json={'url': url})
    assert response.status_code == 201
    return response.json()['code']


def test_generate_code():
    code = generate_code()
    assert len(code) == CODE_LENGTH
    assert set(code) <= set(ALPHABET)


async def test_create_link(client):
    response = await client.post('/api/links', json={'url': URL})

    assert response.status_code == 201
    body = response.json()
    assert len(body['code']) == CODE_LENGTH
    assert body['short_url'] == f'{settings.base_url}/{body["code"]}'


async def test_invalid_url(client):
    response = await client.post('/api/links', json={'url': 'not a url'})
    assert response.status_code == 422


async def test_redirect(client):
    code = await shorten(client)

    response = await client.get(f'/{code}')

    assert response.status_code == 302
    assert response.headers['location'] == URL


async def test_unknown_code(client):
    response = await client.get('/AAAAAAA')

    assert response.status_code == 404
    assert response.json() == {'detail': 'Ссылка не найдена'}


async def test_redirect_uses_cache(client, cache, sessions):
    code = await shorten(client)
    await client.get(f'/{code}')

    assert await cache.get(f'link:{code}') == URL
    assert 0 < await cache.ttl(f'link:{code}') <= settings.cache_ttl_seconds

    # Ссылки в базе больше нет, но перенаправление отвечает из кэша
    async with sessions() as session:
        await session.execute(delete(Link))
        await session.commit()
    response = await client.get(f'/{code}')
    assert response.status_code == 302


async def test_retry_on_code_conflict(client, monkeypatch):
    codes = iter(['aaaaaaa', 'aaaaaaa', 'bbbbbbb'])
    monkeypatch.setattr(service, 'generate_code', lambda: next(codes))

    assert await shorten(client) == 'aaaaaaa'
    assert await shorten(client, 'https://example.com/other') == 'bbbbbbb'


async def test_all_codes_taken(client, monkeypatch):
    monkeypatch.setattr(service, 'generate_code', lambda: 'aaaaaaa')
    await shorten(client)

    response = await client.post('/api/links', json={'url': URL})
    assert response.status_code == 503


async def test_stats(client):
    code = await shorten(client)
    for _ in range(3):
        await client.get(f'/{code}')

    response = await client.get(f'/api/links/{code}/stats')

    assert response.status_code == 200
    body = response.json()
    assert body['url'] == URL
    assert body['clicks'] == 3


async def test_stats_unknown_code(client):
    response = await client.get('/api/links/AAAAAAA/stats')
    assert response.status_code == 404
