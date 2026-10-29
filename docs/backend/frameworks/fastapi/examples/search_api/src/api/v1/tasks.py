from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from src.api.deps import TaskServiceDep
from src.core.config import MAX_RESULT_WINDOW
from src.models.task import Task
from src.services.task import SortOrder

router = APIRouter(prefix='/api/v1/tasks', tags=['tasks'])

PageNumber = Annotated[int, Query(ge=1, description='Номер страницы, с единицы')]
PageSize = Annotated[int, Query(ge=1, le=100, description='Размер страницы')]


def check_result_window(page_number: int, page_size: int) -> None:
    if page_number * page_size > MAX_RESULT_WINDOW:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f'Можно получить только первые {MAX_RESULT_WINDOW} результатов, уточните запрос',
        )


# /search и / объявлены раньше /{task_id}, иначе "search" разбирался бы как task_id
@router.get('/search')
async def search_tasks(
    service: TaskServiceDep,
    query: Annotated[str, Query(min_length=1, max_length=200)],
    page_number: PageNumber = 1,
    page_size: PageSize = 50,
) -> list[Task]:
    check_result_window(page_number, page_size)
    return await service.search(query, page_number, page_size)


@router.get('/')
async def list_tasks(
    service: TaskServiceDep,
    tag: str | None = None,
    sort: SortOrder = '-modified',
    page_number: PageNumber = 1,
    page_size: PageSize = 50,
) -> list[Task]:
    check_result_window(page_number, page_size)
    return await service.list_tasks(tag, sort, page_number, page_size)


@router.get('/{task_id}')
async def get_task(task_id: UUID, service: TaskServiceDep) -> Task:
    task = await service.get_by_id(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Задача не найдена')
    return task
