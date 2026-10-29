import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal

from aiokafka import AIOKafkaProducer
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

TOPIC = 'task-events'


class EventIn(BaseModel):
    event_type: Literal['task.created', 'task.done', 'task.viewed', 'task.rated']
    user_id: int = Field(gt=0)
    task_id: int = Field(gt=0)
    rating: int | None = Field(default=None, ge=1, le=5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    producer = AIOKafkaProducer(
        bootstrap_servers=os.environ.get('KAFKA_BOOTSTRAP_SERVERS', '127.0.0.1:39192'),
        acks='all',
        enable_idempotence=True,
        # Батчинг: ждём до 20 мс, чтобы собрать в один запрос события от разных HTTP-запросов
        linger_ms=20,
        max_batch_size=256 * 1024,
        compression_type='gzip',
        key_serializer=lambda key: str(key).encode(),
        value_serializer=lambda value: json.dumps(value).encode(),
    )
    await producer.start()
    app.state.producer = producer
    yield
    await producer.stop()


app = FastAPI(lifespan=lifespan)


@app.post('/events', status_code=202)
async def create_event(event: EventIn, request: Request) -> dict:
    payload = event.model_dump() | {
        'event_id': str(uuid.uuid4()),
        'event_time': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
    }
    # Ключ — пользователь: его события попадут в одну партицию и сохранят порядок
    await request.app.state.producer.send_and_wait(TOPIC, key=event.user_id, value=payload)
    return {'event_id': payload['event_id']}
