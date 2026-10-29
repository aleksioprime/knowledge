"""Старый «Задачник»: задачи и комментарии в одном приложении и в старом формате."""
from itertools import count

from fastapi import FastAPI, HTTPException, Request

app = FastAPI(title='Задачник: монолит')

# Исторические имена полей: ttl — заголовок, st — статус числом, usr_id — владелец
TASKS = {
    1: {'id': 1, 'ttl': 'Сдать отчёт', 'st': 1, 'usr_id': 10},
    2: {'id': 2, 'ttl': 'Купить хлеб', 'st': 2, 'usr_id': 11},
}
COMMENTS = [
    {'cid': 100, 'tsk': 1, 'usr_id': 11, 'txt': 'Когда дедлайн?', 'ts': 1761728400},
    {'cid': 101, 'tsk': 1, 'usr_id': 10, 'txt': 'В пятницу', 'ts': 1761732000},
]
next_comment_id = count(102)


@app.middleware('http')
async def served_by(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Served-By'] = 'monolith'
    return response


@app.get('/api/tasks')
def list_tasks():
    return list(TASKS.values())


@app.get('/api/tasks/{task_id}')
def get_task(task_id: int):
    if task_id not in TASKS:
        raise HTTPException(404, 'task not found')
    return TASKS[task_id]


@app.get('/api/tasks/{task_id}/comments')
def list_comments(task_id: int):
    return [comment for comment in COMMENTS if comment['tsk'] == task_id]


@app.post('/api/tasks/{task_id}/comments', status_code=201)
def add_comment(task_id: int, body: dict):
    comment = {'cid': next(next_comment_id), 'tsk': task_id, 'usr_id': body['usr_id'], 'txt': body['txt'], 'ts': 1761735600}
    COMMENTS.append(comment)
    return comment
