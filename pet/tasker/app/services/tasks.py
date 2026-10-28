from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Task, User
from app.schemas import TaskCreate, TaskUpdate
from app.services.stats import invalidate_stats


class TaskNotFoundError(Exception):
    pass


async def list_tasks(
    session: AsyncSession, owner: User, done: bool | None, limit: int, offset: int
) -> list[Task]:
    query = select(Task).where(Task.owner_id == owner.id)
    if done is not None:
        query = query.where(Task.done == done)
    query = query.order_by(Task.id).limit(limit).offset(offset)
    return list(await session.scalars(query))


async def get_task(session: AsyncSession, owner: User, task_id: int) -> Task:
    task = await session.get(Task, task_id)
    # Чужая задача выглядит так же, как несуществующая: не выдаём, что она есть
    if task is None or task.owner_id != owner.id:
        raise TaskNotFoundError(task_id)
    return task


async def create_task(session: AsyncSession, cache: Redis, owner: User, data: TaskCreate) -> Task:
    task = Task(**data.model_dump(), owner_id=owner.id)
    session.add(task)
    await session.commit()
    await session.refresh(task)
    await invalidate_stats(cache, owner)
    return task


async def update_task(
    session: AsyncSession, cache: Redis, owner: User, task_id: int, data: TaskUpdate
) -> Task:
    task = await get_task(session, owner, task_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    await session.commit()
    await invalidate_stats(cache, owner)
    return task


async def delete_task(session: AsyncSession, cache: Redis, owner: User, task_id: int) -> None:
    task = await get_task(session, owner, task_id)
    await session.delete(task)
    await session.commit()
    await invalidate_stats(cache, owner)
