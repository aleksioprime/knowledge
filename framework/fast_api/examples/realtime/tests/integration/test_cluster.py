"""Проверки на двух экземплярах из docker-compose.yaml.

Запуск: docker compose -p kb-ws up -d --build --wait && pytest tests/integration
"""

import asyncio
import json
import os

import httpx2 as httpx
import pytest
import websockets

from app.auth import create_token
from app.config import Settings

APP1 = os.getenv('APP1_URL', 'http://localhost:41801')
APP2 = os.getenv('APP2_URL', 'http://localhost:41802')
PROXY = os.getenv('PROXY_URL', 'http://localhost:41800')
SECRET = os.getenv('JWT_SECRET', Settings.jwt_secret)

try:
    httpx.get(f'{APP1}/health', timeout=1).raise_for_status()
except httpx.HTTPError:
    pytest.skip('стенд не запущен: docker compose -p kb-ws up -d --build --wait', allow_module_level=True)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return 'asyncio'


def ws_url(base: str, token: str, **params) -> str:
    query = '&'.join(f'{k}={v}' for k, v in {'token': token, **params}.items())
    return base.replace('http', 'ws', 1) + f'/ws?{query}'


async def notify(base: str, user_id: str, event: str, **data) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(f'{base}/notify', json={'user_id': user_id, 'event': event, 'data': data})
        response.raise_for_status()
        return response.json()['id']


async def sse_events(response, count: int) -> list[dict]:
    """Читает из потока text/event-stream `count` событий (комментарии пропускает)."""
    events, current = [], {}
    async for line in response.aiter_lines():
        if line.startswith(':'):
            continue
        if not line:
            if 'data' in current:
                current['data'] = json.loads(current['data'])
                events.append(current)
                if len(events) == count:
                    return events
            current = {}
            continue
        field, _, value = line.partition(':')
        current[field] = value.removeprefix(' ')
    return events


async def test_notification_crosses_instances():
    token = create_token('anna', SECRET)
    async with websockets.connect(ws_url(APP1, token)) as ws:
        hello = json.loads(await ws.recv())
        event_id = await notify(APP2, 'anna', 'task_assigned', task_id=42, title='Подготовить отчёт')
        message = json.loads(await asyncio.wait_for(ws.recv(), 5))
    print(f'\nподключение к {hello["instance"]}, уведомление отправлено через {message["from"]}: {message}')
    assert hello['instance'] == 'app1'
    assert message['from'] == 'app2'
    assert message['id'] == event_id


async def test_invalid_token_closes_with_1008():
    async with websockets.connect(ws_url(APP1, 'broken')) as ws:
        with pytest.raises(websockets.ConnectionClosedError) as error:
            await ws.recv()
    print(f'\nкод закрытия: {error.value.rcvd.code}, причина: {error.value.rcvd.reason}')
    assert error.value.rcvd.code == 1008


async def test_disconnect_removes_from_manager():
    token = create_token('boris', SECRET)
    async with httpx.AsyncClient(base_url=APP1) as client:
        async with websockets.connect(ws_url(APP1, token)) as ws:
            await ws.recv()
            during = (await client.get('/debug/connections')).json()['websocket']
        for _ in range(20):
            after = (await client.get('/debug/connections')).json()['websocket']
            if 'boris' not in after:
                break
            await asyncio.sleep(0.1)
    print(f'\nпока подключён: {during}, после отключения: {after}')
    assert during.get('boris') == 1
    assert 'boris' not in after


async def test_sse_catches_up_with_last_event_id():
    token = create_token('vera', SECRET)
    async with httpx.AsyncClient(timeout=10) as client:
        async with client.stream('GET', f'{APP1}/events', params={'token': token}) as response:
            assert response.headers['content-type'].startswith('text/event-stream')
            await asyncio.sleep(0.2)
            await notify(APP2, 'vera', 'comment_added', task_id=7, text='Первый комментарий')
            [first] = await asyncio.wait_for(sse_events(response, 1), 5)

        missed = [await notify(APP2, 'vera', 'comment_added', task_id=7, text=f'Пока не было: {n}') for n in (1, 2)]

        async with client.stream('GET', f'{APP2}/events', params={'token': token},
                                 headers={'Last-Event-ID': first['id']}) as response:
            caught_up = await asyncio.wait_for(sse_events(response, 2), 5)
        await asyncio.sleep(0.3)
        listeners = (await client.get(f'{APP2}/debug/connections')).json()['sse']
    print(f'\nпервое событие: {first}\nпосле переподключения: {caught_up}')
    assert first['event'] == 'comment_added'
    assert [event['id'] for event in caught_up] == missed
    assert 'vera' not in listeners


async def test_flood_client_is_disconnected():
    token = create_token('gleb', SECRET)
    async with websockets.connect(ws_url(APP1, token)) as ws:
        await ws.recv()
        sent = 0
        with pytest.raises(websockets.ConnectionClosed) as error:
            while True:
                await ws.send(json.dumps({'type': 'ping'}))
                sent += 1
                await ws.recv()
    print(f'\nотправлено {sent} сообщений, код закрытия: {error.value.rcvd.code}, причина: {error.value.rcvd.reason}')
    assert error.value.rcvd.code == 1008
    assert error.value.rcvd.reason == 'too many messages'


async def test_long_poll_crosses_instances():
    token = create_token('dina', SECRET)
    async with httpx.AsyncClient(timeout=10) as client:
        waiting = asyncio.create_task(client.get(f'{APP2}/poll', params={'token': token, 'timeout': 5}))
        await asyncio.sleep(0.3)
        event_id = await notify(APP1, 'dina', 'task_assigned', task_id=5)
        items = (await waiting).json()['items']
    assert [item['id'] for item in items] == [event_id]


async def test_through_nginx():
    token = create_token('egor', SECRET)
    async with websockets.connect(ws_url(PROXY, token)) as ws, httpx.AsyncClient(timeout=10) as client:
        hello = json.loads(await ws.recv())
        async with client.stream('GET', f'{PROXY}/events', params={'token': token}) as response:
            await asyncio.sleep(0.2)
            await notify(PROXY, 'egor', 'task_assigned', task_id=9)
            [event] = await asyncio.wait_for(sse_events(response, 1), 5)
        message = json.loads(await asyncio.wait_for(ws.recv(), 5))
    print(f'\nчерез nginx: WebSocket на {hello["instance"]}, SSE получил {event}')
    assert message['id'] == event['id']
