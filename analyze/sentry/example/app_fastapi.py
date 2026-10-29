import logging
import re

import sentry_sdk
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

EMAIL = re.compile(r'[\w.+-]+@(?:[\w-]+\.)+[a-z]{2,}', re.IGNORECASE)
SECRET_KEYS = {'password', 'token', 'authorization', 'email', 'phone'}


def scrub(value):
    if isinstance(value, dict):
        return {
            key: '[Filtered]' if key.lower() in SECRET_KEYS else scrub(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [scrub(item) for item in value]
    if isinstance(value, str):
        return EMAIL.sub('[email]', value)
    return value


def before_send(event, hint):
    return scrub(event)  # вернуть None — событие не отправится


class TaskLocked(Exception):
    pass


sentry_sdk.init(
    dsn='http://public@127.0.0.1:47001/1',
    environment='local',
    release='tasker@1.4.2',
    traces_sample_rate=0.0,  # трассировка выключена, только ошибки
    before_send=before_send,
)

logger = logging.getLogger('tasker')
logging.basicConfig(level=logging.INFO)
app = FastAPI()
TASKS = {1: {'id': 1, 'title': 'Сдать отчёт', 'assignee': 'anna@example.com'}}


@app.exception_handler(TaskLocked)
async def task_locked(request: Request, exc: TaskLocked):
    return JSONResponse({'detail': 'Задачу редактирует другой пользователь'}, status_code=409)


@app.middleware('http')
async def sentry_context(request: Request, call_next):
    user_id = request.headers.get('X-User-Id')
    if user_id:
        sentry_sdk.set_user({'id': user_id})
    sentry_sdk.set_tag('client', request.headers.get('X-Client', 'web'))
    return await call_next(request)


@app.get('/tasks/{task_id}')
async def get_task(task_id: int):
    logger.info('Читаем задачу %s', task_id)
    if task_id == 13:
        task = TASKS[task_id]['title']  # ошибка в коде: KeyError
    if task_id == 7:
        raise TaskLocked(task_id)
    if task_id not in TASKS:
        raise HTTPException(404, 'Задача не найдена')
    return TASKS[task_id]


@app.post('/tasks/{task_id}/assign')
async def assign(task_id: int, request: Request):
    payload = await request.json()
    logger.info('Назначаем задачу %s на %s', task_id, payload['email'])
    raise RuntimeError(f'SMTP недоступен, письмо для {payload["email"]} не отправлено')
