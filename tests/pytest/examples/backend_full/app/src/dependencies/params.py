from fastapi import Query

from src.models.base import BasePaginationParams, BaseSortParams


def get_pagination_params(
        page_size: int = Query(12, description='Количество записей на страницу'),
        page_number: int = Query(1, description='Номер текущей страницы'),
) -> BasePaginationParams:
    """
    Получает параметры пагинации
    """

    limit = page_size if page_size > 0 else 12
    offset = (page_number - 1) * limit if page_number > 1 else 0

    return BasePaginationParams(
        limit=limit,
        offset=offset,
    )


def get_sort_params(
        sort_by: str = Query("timestamp", description='Поле для сортировки'),
        order: str = Query("desc", description='Порядок сортировки'),
) -> BaseSortParams:
    """
    Получает параметры пагинации
    """

    return BaseSortParams(
        sort_by=sort_by,
        order=order,
    )