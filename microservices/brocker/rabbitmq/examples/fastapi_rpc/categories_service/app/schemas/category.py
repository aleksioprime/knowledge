from pydantic import BaseModel
from pydantic import ConfigDict


class CategoryBase(BaseModel):
    """Базовая схема категории"""
    name: str


class CategorySchema(CategoryBase):
    """Схема категории с ID"""
    id: int

    # Конфигурация модели для работы с ORM
    model_config = ConfigDict(from_attributes=True)