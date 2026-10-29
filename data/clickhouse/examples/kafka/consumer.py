"""Свой консьюмер: читает task-events и пишет в ClickHouse пачками.

uv run --with aiokafka==0.15.0 --with clickhouse-connect==1.11.0 consumer.py
"""

import asyncio
import json
import time
import uuid
from datetime import datetime

import clickhouse_connect
from aiokafka import AIOKafkaConsumer

BATCH_SIZE = 50_000
BATCH_SECONDS = 2.0
COLUMNS = ['event_id', 'event_type', 'user_id', 'task_id', 'rating', 'event_time', 'kafka_partition', 'kafka_offset']


def to_row(message) -> list:
    event = json.loads(message.value)
    return [
        uuid.UUID(event['event_id']),
        event['event_type'],
        event['user_id'],
        event['task_id'],
        event.get('rating'),
        datetime.fromisoformat(event['event_time']),
        message.partition,
        message.offset,
    ]


async def main() -> None:
    ch = clickhouse_connect.get_client(host='127.0.0.1', port=38123, username='ugc', password='ugc')
    consumer = AIOKafkaConsumer(
        'task-events',
        bootstrap_servers='127.0.0.1:39192',
        group_id='batch-writer',
        auto_offset_reset='earliest',
        enable_auto_commit=False,
    )
    await consumer.start()
    rows: list[list] = []
    flushed_at = time.monotonic()
    try:
        while True:
            batches = await consumer.getmany(timeout_ms=500, max_records=10_000)
            for messages in batches.values():
                rows.extend(to_row(message) for message in messages)

            if rows and (len(rows) >= BATCH_SIZE or time.monotonic() - flushed_at >= BATCH_SECONDS):
                # Сначала вставка, потом коммит смещений: при падении между ними пачка придёт ещё раз
                await asyncio.to_thread(ch.insert, 'ugc.events_batch', rows, column_names=COLUMNS)
                await consumer.commit()
                print(f'вставлено {len(rows)} строк')
                rows = []
                flushed_at = time.monotonic()
    finally:
        await consumer.stop()


if __name__ == '__main__':
    asyncio.run(main())
