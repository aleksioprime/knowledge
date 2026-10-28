from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routers import auth, tasks
from app.core.metrics import MetricsMiddleware, metrics_endpoint
from app.services.tasks import TaskNotFoundError

app = FastAPI(title='Задачник')
app.include_router(auth.router)
app.include_router(tasks.router)
app.add_middleware(MetricsMiddleware)
app.add_api_route('/metrics', metrics_endpoint, include_in_schema=False)


@app.exception_handler(TaskNotFoundError)
async def task_not_found(request: Request, exc: TaskNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={'detail': 'Задача не найдена'})


@app.get('/health')
async def health() -> dict[str, str]:
    return {'status': 'ok'}
