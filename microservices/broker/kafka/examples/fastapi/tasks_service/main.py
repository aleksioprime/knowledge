import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from aiokafka import AIOKafkaProducer
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

TOPIC = 'task-events'


@asynccontextmanager
async def lifespan(app: FastAPI):
    producer = AIOKafkaProducer(
        bootstrap_servers=os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9096'),
        key_serializer=lambda key: str(key).encode(),
        value_serializer=lambda value: json.dumps(value, ensure_ascii=False).encode(),
        acks='all',
    )
    await producer.start()
    app.state.producer = producer
    yield
    await producer.stop()


app = FastAPI(title='Сервис задач', lifespan=lifespan)
tasks: dict[int, dict] = {}


class TaskCreate(BaseModel):
    title: str
    owner_id: int


async def publish(request: Request, event_type: str, task: dict) -> None:
    event = {'type': event_type, 'task': task, 'at': datetime.now(timezone.utc).isoformat()}
    # Ключ — владелец: все события одного пользователя попадут в одну партицию и сохранят порядок
    await request.app.state.producer.send_and_wait(TOPIC, key=task['owner_id'], value=event)


@app.post('/tasks', status_code=201)
async def create_task(request: Request, data: TaskCreate) -> dict:
    task = {'id': len(tasks) + 1, 'done': False, **data.model_dump()}
    tasks[task['id']] = task
    await publish(request, 'task.created', task)
    return task


@app.post('/tasks/{task_id}/done')
async def complete_task(request: Request, task_id: int) -> dict:
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail='Задача не найдена')
    tasks[task_id]['done'] = True
    await publish(request, 'task.done', tasks[task_id])
    return tasks[task_id]
