"""
Pydantic схемы для параметров сортировки
"""
from typing import Optional
from pydantic import BaseModel, Field


class BaseSortParams(BaseModel):
    """
    Параметры сортировки для SQL запросов.
    Определяет поле и порядок сортировки
    """
    sort_by: Optional[str] = Field(None, description="Поле для сортировки")
    order: Optional[str] = Field(None, pattern="^(asc|desc)$", description="Порядок сортировки (asc/desc)")
