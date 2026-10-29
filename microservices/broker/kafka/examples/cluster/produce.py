"""Отправляет несколько событий с выбранным acks и печатает, что записалось.

uv run --with aiokafka==0.15.0 produce.py --acks all --count 3
"""

import argparse
import asyncio
import json
import logging

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

BOOTSTRAP = '127.0.0.1:39092'

# Без этого клиент печатает предупреждение на каждый повтор
logging.getLogger('aiokafka').setLevel(logging.ERROR)


async def main(acks: str, count: int, topic: str) -> None:
    producer = AIOKafkaProducer(
        bootstrap_servers=BOOTSTRAP,
        acks=int(acks) if acks in ('0', '1') else 'all',
        request_timeout_ms=5000,
        retry_backoff_ms=500,
    )
    await producer.start()
    try:
        for task_id in range(1, count + 1):
            event = {'type': 'task.created', 'task_id': task_id}
            try:
                meta = await producer.send_and_wait(
                    topic, key=b'user-1', value=json.dumps(event).encode()
                )
                if meta is None:  # acks=0: брокер ничего не отвечает
                    print(f'task {task_id}: отправлено, подтверждения нет')
                else:
                    print(f'task {task_id}: записано, партиция {meta.partition}, смещение {meta.offset}')
            except KafkaError as error:
                print(f'task {task_id}: ошибка {type(error).__name__}')
    finally:
        await producer.stop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--acks', choices=['0', '1', 'all'], default='all')
    parser.add_argument('--count', type=int, default=3)
    parser.add_argument('--topic', default='task-events')
    args = parser.parse_args()
    asyncio.run(main(args.acks, args.count, args.topic))
