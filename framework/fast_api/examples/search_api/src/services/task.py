from typing import Literal
from uuid import UUID

from elasticsearch import AsyncElasticsearch, NotFoundError
from pydantic import TypeAdapter

from src.models.task import Task
from src.services.cache import Cache, make_key

TaskList = TypeAdapter(list[Task])
SortOrder = Literal['modified', '-modified']


class TaskService:
    """Чтение задач из Elasticsearch с кэшем в Redis. Про HTTP ничего не знает."""

    def __init__(self, elastic: AsyncElasticsearch, cache: Cache, index: str):
        self.elastic = elastic
        self.cache = cache
        self.index = index

    async def get_by_id(self, task_id: UUID) -> Task | None:
        key = f'tasks:id:{task_id}'
        if (cached := await self.cache.get(key)) is not None:
            return Task.model_validate_json(cached)
        try:
            hit = await self.elastic.get(index=self.index, id=str(task_id))
        except NotFoundError:
            return None
        task = Task.from_hit(hit)
        await self.cache.set(key, task.model_dump_json())
        return task

    async def search(self, query: str, page_number: int, page_size: int) -> list[Task]:
        body = {'multi_match': {'query': query, 'fields': ['title^2', 'description']}}
        key = make_key('tasks:search', query=query, page_number=page_number, page_size=page_size)
        return await self._search_cached(key, body, page_number, page_size)

    async def list_tasks(self, tag: str | None, sort: SortOrder, page_number: int, page_size: int) -> list[Task]:
        body = {'bool': {'filter': [{'term': {'tags': tag}}]}} if tag else {'match_all': {}}
        order = 'desc' if sort.startswith('-') else 'asc'
        key = make_key('tasks:list', tag=tag, sort=sort, page_number=page_number, page_size=page_size)
        return await self._search_cached(key, body, page_number, page_size, sort=[{'modified': order}])

    async def _search_cached(self, key: str, query: dict, page_number: int, page_size: int, sort=None) -> list[Task]:
        if (cached := await self.cache.get(key)) is not None:
            return TaskList.validate_json(cached)
        response = await self.elastic.search(
            index=self.index,
            query=query,
            sort=sort,
            from_=(page_number - 1) * page_size,
            size=page_size,
        )
        tasks = [Task.from_hit(hit) for hit in response['hits']['hits']]
        await self.cache.set(key, TaskList.dump_json(tasks).decode())
        return tasks
