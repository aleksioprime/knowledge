"""Новый сервис комментариев. Новые комментарии хранит у себя, старые читает из монолита."""
import os
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from app.legacy import Comment, LegacyTasker, TaskRef

app = FastAPI(title='Задачник: комментарии')
# Адрес монолита внутри сети, а не шлюза: через шлюз запрос вернулся бы в этот же сервис
legacy = LegacyTasker(os.environ['LEGACY_URL'])
COMMENTS: list[Comment] = []


class NewComment(BaseModel):
    author_id: int
    text: str


class TaskComments(BaseModel):
    task: TaskRef
    comments: list[Comment]


@app.middleware('http')
async def served_by(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Served-By'] = 'comments'
    return response


async def existing_task(task_id: int) -> TaskRef:
    task = await legacy.get_task(task_id)
    if task is None:
        raise HTTPException(404, 'task not found')
    return task


@app.get('/api/tasks/{task_id}/comments')
async def list_comments(task_id: int) -> TaskComments:
    task = await existing_task(task_id)
    old = await legacy.get_comments(task_id)
    new = [comment for comment in COMMENTS if comment.task_id == task_id]
    return TaskComments(task=task, comments=old + new)


@app.post('/api/tasks/{task_id}/comments', status_code=201)
async def add_comment(task_id: int, body: NewComment) -> Comment:
    await existing_task(task_id)
    comment = Comment(
        id=str(uuid4()), task_id=task_id, author_id=body.author_id,
        text=body.text, created_at=datetime.now(timezone.utc),
    )
    COMMENTS.append(comment)
    return comment
