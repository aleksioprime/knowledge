from datetime import date

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title='Задачник')


class TaskCreate(BaseModel):
    title: str
    due_date: date | None = None


class Task(TaskCreate):
    id: int
    done: bool = False


# Пока задачи хранятся в памяти и пропадают при перезапуске.
# На этапе про SQLAlchemy их место займёт PostgreSQL.
tasks: dict[int, Task] = {}


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.get('/tasks')
def list_tasks() -> list[Task]:
    return list(tasks.values())


@app.post('/tasks', status_code=201)
def create_task(data: TaskCreate) -> Task:
    task = Task(id=len(tasks) + 1, **data.model_dump())
    tasks[task.id] = task
    return task


@app.get('/tasks/{task_id}')
def get_task(task_id: int) -> Task:
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail='Задача не найдена')
    return tasks[task_id]
