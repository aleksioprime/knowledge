from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas import TaskCreate, TaskRead, TaskUpdate
from app.services import tasks

router = APIRouter(prefix='/tasks', tags=['tasks'])


@router.get('')
async def list_tasks(
    session: SessionDep,
    user: CurrentUser,
    done: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TaskRead]:
    return [TaskRead.model_validate(t) for t in await tasks.list_tasks(session, user, done, limit, offset)]


@router.post('', status_code=status.HTTP_201_CREATED)
async def create_task(session: SessionDep, user: CurrentUser, data: TaskCreate) -> TaskRead:
    return TaskRead.model_validate(await tasks.create_task(session, user, data))


@router.get('/{task_id}')
async def get_task(session: SessionDep, user: CurrentUser, task_id: int) -> TaskRead:
    return TaskRead.model_validate(await tasks.get_task(session, user, task_id))


@router.patch('/{task_id}')
async def update_task(session: SessionDep, user: CurrentUser, task_id: int, data: TaskUpdate) -> TaskRead:
    return TaskRead.model_validate(await tasks.update_task(session, user, task_id, data))


@router.delete('/{task_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(session: SessionDep, user: CurrentUser, task_id: int) -> None:
    await tasks.delete_task(session, user, task_id)
