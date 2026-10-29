import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from app import sse, ws
from app.bus import NotificationBus
from app.config import Settings, get_settings
from app.manager import ConnectionManager


class Notification(BaseModel):
    user_id: str
    event: str = Field(examples=['task_assigned'])
    data: dict = Field(default_factory=dict, examples=[{'task_id': 42, 'title': 'Подготовить отчёт'}])


def create_app(settings: Settings | None = None, redis: Redis | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        client = redis or Redis.from_url(settings.redis_url, decode_responses=True)
        manager = ConnectionManager(settings.send_timeout, settings.sse_queue_size)
        bus = NotificationBus(client, manager, settings.instance, settings.stream_maxlen)
        app.state.settings = settings
        app.state.manager = manager
        app.state.bus = bus
        listener = asyncio.create_task(bus.listen())
        await asyncio.wait_for(bus.ready.wait(), timeout=10)
        yield
        listener.cancel()
        await asyncio.gather(listener, return_exceptions=True)
        await client.aclose()

    app = FastAPI(title='Уведомления Задачника', lifespan=lifespan)
    app.include_router(ws.router)
    app.include_router(sse.router)

    @app.post('/notify', status_code=status.HTTP_202_ACCEPTED)
    async def notify(notification: Notification, request: Request) -> dict:
        event_id = await request.app.state.bus.publish(
            notification.user_id, notification.event, notification.data
        )
        return {'id': event_id, 'instance': settings.instance}

    @app.get('/debug/connections')
    async def connections(request: Request) -> dict:
        return {'instance': settings.instance, **request.app.state.manager.stats()}

    @app.get('/health')
    async def health() -> dict:
        return {'status': 'ok'}

    return app


app = create_app()
