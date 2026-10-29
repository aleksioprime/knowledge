from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class Task(BaseModel):
    id: UUID
    title: str
    description: str | None = None
    done: bool
    owner: str
    tags: list[str] = []
    modified: datetime

    @classmethod
    def from_hit(cls, hit: dict) -> 'Task':
        return cls(id=hit['_id'], **hit['_source'])
