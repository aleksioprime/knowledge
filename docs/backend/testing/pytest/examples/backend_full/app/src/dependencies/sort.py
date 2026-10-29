"""
Dependencies для параметров запросов (query parameters).
Предоставляет параметры пагинации и сортировки для API эндпоинтов.
"""
from fastapi import Query

from src.schemas.sort import BaseSortParams


def get_sort_params(
        sort_by: str = Query("created_at", description='Поле для сортировки'),
        order: str = Query("desc", regex="^(asc|desc)$", description='Порядок сортировки (asc/desc)'),
) -> BaseSortParams:
    """
    Извлекает параметры сортировки из query параметров запроса.
    Определяет поле и порядок сортировки результато
    """
    return BaseSortParams(
        sort_by=sort_by,
        order=order,
    )