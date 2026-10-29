"""API приёма событий: проверяет контракт и публикует событие в topic exchange."""

import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated, Literal

import aio_pika
from aio_pika.exceptions import AMQPError, ChannelInvalidStateError, DeliveryError
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from common import RABBIT_URL, declare_topology, routing_key


class TaskAssigned(BaseModel):
    task_id: int
    assignee_id: int
    actor_id: int


class CommentCreated(BaseModel):
    task_id: int
    comment_id: int
    author_id: int


class TaskAssignedEvent(BaseModel):
    event_id: uuid.UUID
    type: Literal['task.assigned']
    occurred_at: datetime
    data: TaskAssigned


class CommentCreatedEvent(BaseModel):
    event_id: uuid.UUID
    type: Literal['comment.created']
    occurred_at: datetime
    data: CommentCreated


Event = Annotated[TaskAssignedEvent | CommentCreatedEvent, Field(discriminator='type')]


@asynccontextmanager
async def lifespan(app: FastAPI):
    connection = await aio_pika.connect_robust(RABBIT_URL)
    # publisher_confirms: publish ждёт подтверждения от брокера
    # on_return_raises: сообщение, которое некуда положить, превращается в исключение
    channel = await connection.channel(publisher_confirms=True, on_return_raises=True)
    app.state.exchange = await declare_topology(channel)
    yield
    await connection.close()


app = FastAPI(title='Notifications API', lifespan=lifespan)


@app.post('/events', status_code=202)
async def accept_event(event: Event, x_request_id: Annotated[str | None, Header()] = None):
    message = aio_pika.Message(
        body=event.model_dump_json().encode(),
        content_type='application/json',
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        message_id=str(event.event_id),
        headers={'x-request-id': x_request_id or str(uuid.uuid4())},
    )
    try:
        await app.state.exchange.publish(
            message, routing_key=routing_key(event.type), mandatory=True, timeout=5
        )
    except (DeliveryError, AMQPError, ChannelInvalidStateError, ConnectionError, asyncio.TimeoutError) as exc:
        # Источник получит 503 и повторит отправку из своего outbox
        raise HTTPException(503, f'Брокер не принял событие: {exc!r}') from exc
    return {'status': 'accepted', 'event_id': event.event_id}
