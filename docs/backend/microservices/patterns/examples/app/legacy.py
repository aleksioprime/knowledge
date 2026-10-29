"""Предохранительный слой: единственное место, которое знает старый формат монолита."""
from datetime import datetime, timezone

import httpx
from pydantic import BaseModel

LEGACY_STATUS = {0: 'new', 1: 'in_progress', 2: 'done'}


class TaskRef(BaseModel):
    id: int
    title: str
    status: str


class Comment(BaseModel):
    id: str
    task_id: int
    author_id: int
    text: str
    created_at: datetime


def task_from_legacy(raw: dict) -> TaskRef:
    return TaskRef(id=raw['id'], title=raw['ttl'], status=LEGACY_STATUS.get(raw['st'], 'unknown'))


def comment_from_legacy(raw: dict) -> Comment:
    return Comment(
        id=f'legacy-{raw["cid"]}',  # префикс, чтобы старые id не пересеклись с новыми
        task_id=raw['tsk'],
        author_id=raw['usr_id'],
        text=raw['txt'],
        created_at=datetime.fromtimestamp(raw['ts'], tz=timezone.utc),
    )


class LegacyTasker:
    def __init__(self, base_url: str):
        self.client = httpx.AsyncClient(base_url=base_url, timeout=2.0)

    async def get_task(self, task_id: int) -> TaskRef | None:
        response = await self.client.get(f'/api/tasks/{task_id}')
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return task_from_legacy(response.json())

    async def get_comments(self, task_id: int) -> list[Comment]:
        response = await self.client.get(f'/api/tasks/{task_id}/comments')
        response.raise_for_status()
        return [comment_from_legacy(raw) for raw in response.json()]
