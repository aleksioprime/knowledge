import asyncio
import logging
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from opentelemetry import trace

from app.telemetry import request_id_var, setup_logging, setup_tracing

TASKS = {
    1: {'id': 1, 'title': 'Сдать отчёт', 'author_id': 10},
    2: {'id': 2, 'title': 'Позвонить в банк', 'author_id': 99},  # такого автора нет
}

logger = logging.getLogger('tasks')
tracer = trace.get_tracer('tasks')


async def pass_request_id(request: httpx.Request) -> None:
    request.headers['X-Request-Id'] = request_id_var.get()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.users = httpx.AsyncClient(
        base_url=os.environ['USERS_URL'], timeout=2.0, event_hooks={'request': [pass_request_id]}
    )
    yield
    await app.state.users.aclose()


app = FastAPI(lifespan=lifespan)
setup_logging()
setup_tracing(app)


async def select_task(task_id: int) -> dict | None:
    with tracer.start_as_current_span('SELECT task') as span:
        span.set_attribute('db.system.name', 'postgresql')
        span.set_attribute('db.query.text', 'SELECT id, title, author_id FROM task WHERE id = $1')
        await asyncio.sleep(0.02)  # имитация запроса в базу
        task = TASKS.get(task_id)
        span.set_attribute('db.response.returned_rows', int(task is not None))
        return task


@app.get('/tasks/{task_id}')
async def get_task(task_id: int):
    task = await select_task(task_id)
    if task is None:
        raise HTTPException(404, 'задача не найдена')

    response = await app.state.users.get(f'/users/{task["author_id"]}')
    if response.status_code != 200:
        logger.error('не удалось получить автора %s: %s', task['author_id'], response.status_code)
        raise HTTPException(502, 'сервис пользователей не отдал автора')

    logger.info('задача %s отдана', task_id)
    return {**task, 'author': response.json()}
