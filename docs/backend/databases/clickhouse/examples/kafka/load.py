"""Отправляет события в API и ждёт, пока они появятся в ClickHouse (считает уникальные event_id).

uv run --with httpx==0.28.1 --with clickhouse-connect==1.11.0 load.py --count 100000
"""

import argparse
import asyncio
import random
import time

import clickhouse_connect
import httpx

API_URL = 'http://127.0.0.1:38000/events'
EVENT_TYPES = ['task.viewed'] * 6 + ['task.created', 'task.done', 'task.rated']


def make_event() -> dict:
    event = {
        'event_type': random.choice(EVENT_TYPES),
        'user_id': random.randint(1, 5_000),
        # Немного «популярных» задач, чтобы в отчёте было что показать
        'task_id': int(random.paretovariate(1.2)) if random.random() < 0.5 else random.randint(1, 20_000),
    }
    if event['event_type'] == 'task.rated':
        event['rating'] = random.randint(1, 5)
    return event


async def send_all(count: int, concurrency: int) -> int:
    queue: asyncio.Queue[dict] = asyncio.Queue()
    for _ in range(count):
        queue.put_nowait(make_event())
    errors = 0

    async def worker(client: httpx.AsyncClient) -> None:
        nonlocal errors
        while not queue.empty():
            event = queue.get_nowait()
            for _ in range(3):
                try:
                    response = await client.post(API_URL, json=event)
                except httpx.TransportError:
                    continue  # повтор может дать дубль, если API успел отправить событие
                if response.status_code == 202:
                    break
            else:
                errors += 1

    limits = httpx.Limits(max_connections=concurrency)
    async with httpx.AsyncClient(limits=limits, timeout=30) as client:
        await asyncio.gather(*(worker(client) for _ in range(concurrency)))
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=100_000)
    parser.add_argument('--concurrency', type=int, default=50)
    parser.add_argument('--table', default='ugc.events')
    args = parser.parse_args()

    ch = clickhouse_connect.get_client(host='127.0.0.1', port=38123, username='ugc', password='ugc')
    before = ch.command(f'SELECT uniqExact(event_id) FROM {args.table}')

    started = time.perf_counter()
    errors = asyncio.run(send_all(args.count, args.concurrency))
    sent = time.perf_counter() - started
    print(f'API принял {args.count - errors} событий за {sent:.1f} с ({args.count / sent:.0f} в секунду), ошибок: {errors}')

    while (rows := ch.command(f'SELECT uniqExact(event_id) FROM {args.table}') - before) < args.count - errors:
        time.sleep(0.5)
    total = time.perf_counter() - started
    print(f'В {args.table} {rows} новых уникальных событий через {total:.1f} с после старта')


if __name__ == '__main__':
    main()
