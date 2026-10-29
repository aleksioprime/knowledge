"""Асинхронный доступ к оценкам: PyMongo AsyncMongoClient и ODM Beanie.

Запускать после ugc.py (коллекции уже шардированы и проиндексированы).
uv run --with-requirements requirements.txt python ugc_async.py
"""

import asyncio
from datetime import UTC, datetime

from beanie import Document, init_beanie
from pydantic import Field
from pymongo import AsyncMongoClient, ReturnDocument

URL = 'mongodb://localhost:37017'


async def with_pymongo() -> None:
    client = AsyncMongoClient(URL)
    ratings = client.ugc.task_ratings

    doc = await ratings.find_one_and_update(
        {'task_id': 3, 'user_id': 201},
        {'$set': {'score': 4}, '$setOnInsert': {'created_at': datetime.now(UTC)}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    print('pymongo:', doc['task_id'], doc['user_id'], doc['score'])

    pipeline = [{'$match': {'task_id': 3}}, {'$group': {'_id': None, 'avg': {'$avg': '$score'}}}]
    async for row in await ratings.aggregate(pipeline):
        print('pymongo: среднее по задаче 3 =', row['avg'])
    await client.close()


class TaskRating(Document):
    task_id: int
    user_id: int
    score: int = Field(ge=1, le=5)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = 'task_ratings'
        # Индексы и шардирование уже созданы в ugc.py; Beanie их только использует


async def with_beanie() -> None:
    client = AsyncMongoClient(URL)
    await init_beanie(database=client.ugc, document_models=[TaskRating])

    await TaskRating.find_one(TaskRating.task_id == 3, TaskRating.user_id == 202).upsert(
        {'$set': {TaskRating.score: 5}},
        on_insert=TaskRating(task_id=3, user_id=202, score=5),
    )
    top = await TaskRating.find(TaskRating.task_id == 3).sort(-TaskRating.score).to_list()
    print('beanie:', [(r.user_id, r.score) for r in top])

    try:
        TaskRating(task_id=3, user_id=203, score=10)
    except ValueError as error:
        print('beanie: валидация pydantic —', error.errors()[0]['msg'])
    await client.close()


async def main() -> None:
    await with_pymongo()
    await with_beanie()


asyncio.run(main())
