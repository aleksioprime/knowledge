from pydantic import BaseModel
from pydantic import ConfigDict


class PostBase(BaseModel):
    """Базовая схема поста"""
    title: str
    content: str
    category_id: int


class Post(PostBase):
    """Схема поста с ID"""
    id: int

    model_config = ConfigDict(from_attributes=True)