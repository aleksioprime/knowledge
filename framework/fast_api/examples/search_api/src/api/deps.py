from typing import Annotated

from elasticsearch import AsyncElasticsearch
from fastapi import Depends
from redis.asyncio import Redis

from src.core.config import settings
from src.db.elastic import get_elastic
from src.db.redis import get_redis
from src.services.cache import Cache
from src.services.task import TaskService


def get_task_service(
    elastic: Annotated[AsyncElasticsearch, Depends(get_elastic)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> TaskService:
    cache = Cache(redis, ttl_seconds=settings.cache_ttl_seconds)
    return TaskService(elastic=elastic, cache=cache, index=settings.tasks_index)


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
