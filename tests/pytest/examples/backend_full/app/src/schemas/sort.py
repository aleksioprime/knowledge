"""
Pydantic схемы для параметров сортировки
"""
from pydantic import BaseModel, Field


class BaseSortParams(BaseModel):
    """
    Параметры сортировки для SQL запросов.
    Определяет поле и порядок сортировки
    """
    sort_by: str = Field(..., description="Поле для сортировки")
    order: str = Field(..., pattern="^(asc|desc)$", description="Порядок сортировки (asc/desc)")
