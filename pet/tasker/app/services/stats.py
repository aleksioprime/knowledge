from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Task, User
from app.schemas import TaskStats

STATS_TTL_SECONDS = 60


def stats_key(user_id: int) -> str:
    return f'stats:user:{user_id}'


async def get_stats(session: AsyncSession, cache: Redis, owner: User) -> TaskStats:
    cached = await cache.get(stats_key(owner.id))
    if cached is not None:
        return TaskStats.model_validate_json(cached)

    query = select(func.count(), func.count().filter(Task.done)).where(Task.owner_id == owner.id)
    total, done = (await session.execute(query)).one()
    stats = TaskStats(total=total, done=done)

    await cache.set(stats_key(owner.id), stats.model_dump_json(), ex=STATS_TTL_SECONDS)
    return stats


async def invalidate_stats(cache: Redis, owner: User) -> None:
    await cache.delete(stats_key(owner.id))
