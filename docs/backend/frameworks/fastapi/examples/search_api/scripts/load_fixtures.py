"""Пересоздаёт индекс задач и загружает в него примеры из tasks.json."""
import asyncio
import json
from pathlib import Path

from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk

from src.core.config import settings

# Тот же маппинг, что у ETL из PostgreSQL
MAPPING = {
    'properties': {
        'title': {'type': 'text', 'analyzer': 'russian'},
        'description': {'type': 'text', 'analyzer': 'russian'},
        'done': {'type': 'boolean'},
        'owner': {'type': 'keyword'},
        'tags': {'type': 'keyword'},
        'modified': {'type': 'date'},
    },
}


async def main() -> None:
    tasks = json.loads((Path(__file__).parent / 'tasks.json').read_text())
    async with AsyncElasticsearch(settings.elastic_url) as elastic:
        await elastic.indices.delete(index=settings.tasks_index, ignore_unavailable=True)
        await elastic.indices.create(index=settings.tasks_index, mappings=MAPPING)
        actions = [{'_index': settings.tasks_index, '_id': task.pop('id'), '_source': task} for task in tasks]
        loaded, _ = await async_bulk(elastic, actions, refresh='wait_for')
    print(f'Загружено задач: {loaded}')


if __name__ == '__main__':
    asyncio.run(main())
