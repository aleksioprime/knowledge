"""Учебный сервис, который отвечает быстро, медленно или с ошибками."""
import asyncio

from fastapi import FastAPI, HTTPException

app = FastAPI()
calls = {'flaky': 0}


@app.get('/tasks/{task_id}')
async def get_task(task_id: int):
    await asyncio.sleep(0.5)
    if task_id > 100:
        raise HTTPException(status_code=404, detail='Задача не найдена')
    return {'id': task_id, 'title': f'Задача {task_id}'}


@app.post('/tasks', status_code=201)
async def create_task(task: dict):
    return {'id': 1, **task}


@app.get('/slow')
async def slow():
    await asyncio.sleep(5)
    return {'status': 'наконец-то'}


@app.get('/flaky')
async def flaky():
    calls['flaky'] += 1
    if calls['flaky'] % 3 != 0:
        raise HTTPException(status_code=503, detail='Сервис перегружен')
    return {'status': 'ok', 'attempt': calls['flaky']}
