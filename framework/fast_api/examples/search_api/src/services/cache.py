from urllib.parse import urlencode

from redis.asyncio import Redis


def make_key(prefix: str, **params) -> str:
    """Ключ из всех параметров запроса: tasks:search:page_number=1&page_size=50&query=отчёт."""
    filled = {name: value for name, value in params.items() if value is not None}
    return f'{prefix}:{urlencode(sorted(filled.items()))}'


class Cache:
    def __init__(self, redis: Redis, ttl_seconds: int):
        self.redis = redis
        self.ttl_seconds = ttl_seconds

    async def get(self, key: str) -> str | None:
        return await self.redis.get(key)

    async def set(self, key: str, value: str) -> None:
        await self.redis.set(key, value, ex=self.ttl_seconds)
