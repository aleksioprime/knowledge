import asyncio
import json
import logging

from redis.asyncio import Redis

from app.manager import ConnectionManager

CHANNEL = 'notifications'
logger = logging.getLogger(__name__)


def stream_key(user_id: str) -> str:
    return f'notifications:{user_id}'


def is_newer(event_id: str, than: str | None) -> bool:
    """Сравнивает идентификаторы Redis Stream вида '1761730000000-0'."""
    if than is None:
        return True
    return tuple(map(int, event_id.split('-'))) > tuple(map(int, than.split('-')))


class NotificationBus:
    """Хранит уведомления в Redis Stream и раздаёт их всем экземплярам через pub/sub."""

    def __init__(self, redis: Redis, manager: ConnectionManager, instance: str, maxlen: int = 1000):
        self.redis = redis
        self.manager = manager
        self.instance = instance
        self.maxlen = maxlen
        self.ready = asyncio.Event()

    async def publish(self, user_id: str, event: str, data: dict) -> str:
        event_id = await self.redis.xadd(
            stream_key(user_id),
            {'event': event, 'data': json.dumps(data, ensure_ascii=False)},
            maxlen=self.maxlen,
            approximate=True,
        )
        message = {'user_id': user_id, 'id': event_id, 'event': event, 'data': data, 'from': self.instance}
        await self.redis.publish(CHANNEL, json.dumps(message, ensure_ascii=False))
        return event_id

    async def missed(self, user_id: str, after_id: str, limit: int = 100) -> list[dict]:
        rows = await self.redis.xrange(stream_key(user_id), min=f'({after_id}', count=limit)
        return [
            {'id': row_id, 'event': fields['event'], 'data': json.loads(fields['data'])}
            for row_id, fields in rows
        ]

    async def listen(self) -> None:
        while True:
            try:
                async with self.redis.pubsub() as pubsub:
                    await pubsub.subscribe(CHANNEL)
                    self.ready.set()
                    async for raw in pubsub.listen():
                        if raw['type'] != 'message':
                            continue
                        message = json.loads(raw['data'])
                        user_id = message.pop('user_id')
                        await self.manager.deliver(user_id, message)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception('Подписка на Redis оборвалась, переподключаемся')
                await asyncio.sleep(1)
