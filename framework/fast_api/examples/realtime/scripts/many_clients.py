"""Держит N соединений WebSocket к одному экземпляру и рассылает каждому по уведомлению.

python -m scripts.many_clients 2000
"""

import asyncio
import json
import resource
import sys
import time

import httpx2 as httpx
import websockets

from app.auth import create_token
from app.config import Settings

APP1, APP2 = 'ws://localhost:41801', 'http://localhost:41802'


async def client(n: int, ready: asyncio.Event, received: list) -> None:
    token = create_token(f'user{n}', Settings.jwt_secret)
    async with websockets.connect(f'{APP1}/ws?token={token}', ping_interval=None) as ws:
        await ws.recv()
        ready.set()
        received.append(json.loads(await ws.recv()))


async def main(count: int) -> None:
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    resource.setrlimit(resource.RLIMIT_NOFILE, (min(hard, count * 2 + 100), hard))
    received: list = []
    events = [asyncio.Event() for _ in range(count)]
    tasks = [asyncio.create_task(client(n, events[n], received)) for n in range(count)]
    await asyncio.gather(*(event.wait() for event in events))
    async with httpx.AsyncClient(base_url=APP2) as http:
        print('подключено:', sum((await http.get('http://localhost:41801/debug/connections')).json()['websocket'].values()))
        input_wait = float(sys.argv[2]) if len(sys.argv) > 2 else 0
        await asyncio.sleep(input_wait)
        started = time.perf_counter()
        for n in range(count):
            await http.post('/notify', json={'user_id': f'user{n}', 'event': 'task_assigned', 'data': {'task_id': n}})
        await asyncio.gather(*tasks)
    print(f'доставлено: {len(received)} за {time.perf_counter() - started:.1f} с')


if __name__ == '__main__':
    asyncio.run(main(int(sys.argv[1])))
