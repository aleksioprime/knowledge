from redis.asyncio import Redis

from src.config import settings

redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


async def get_cache() -> Redis:
    return redis_client
