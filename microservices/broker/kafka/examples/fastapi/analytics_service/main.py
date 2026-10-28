import asyncio
import json
import logging
import os
from collections import defaultdict
from contextlib import asynccontextmanager

from aiokafka import AIOKafkaConsumer
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s: %(message)s')
logger = logging.getLogger('analytics')

stats: dict[int, dict[str, int]] = defaultdict(lambda: {'created': 0, 'done': 0})


def handle(event: dict) -> None:
    owner_id = event['task']['owner_id']
    if event['type'] == 'task.created':
        stats[owner_id]['created'] += 1
    elif event['type'] == 'task.done':
        stats[owner_id]['done'] += 1


async def consume(consumer: AIOKafkaConsumer) -> None:
    async for message in consumer:
        event = json.loads(message.value)
        handle(event)
        # Смещение фиксируем только после обработки: при падении событие придёт снова
        await consumer.commit()
        logger.info('%s, партиция %s, смещение %s', event['type'], message.partition, message.offset)


@asynccontextmanager
async def lifespan(app: FastAPI):
    consumer = AIOKafkaConsumer(
        'task-events',
        bootstrap_servers=os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9096'),
        group_id='analytics',
        auto_offset_reset='earliest',
        enable_auto_commit=False,
    )
    await consumer.start()
    worker = asyncio.create_task(consume(consumer))
    yield
    worker.cancel()
    await consumer.stop()


app = FastAPI(title='Сервис аналитики', lifespan=lifespan)


@app.get('/stats')
async def get_stats() -> dict[int, dict[str, int]]:
    return stats
