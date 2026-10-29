import time

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUESTS = Counter('http_requests_total', 'Количество HTTP-запросов', ['method', 'path', 'status'])
LATENCY = Histogram(
    'http_request_duration_seconds',
    'Время обработки HTTP-запроса',
    ['method', 'path'],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5),
)
TASKS_CREATED = Counter('tasks_created_total', 'Сколько задач создали пользователи')


def metrics_endpoint() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        status = 500  # если эндпоинт упал с исключением, ответа не будет, но запрос нужно посчитать
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            # Шаблон пути, а не сам путь: /tasks/{task_id} вместо /tasks/1, /tasks/2, ...
            route = request.scope.get('route')
            path = route.path if route else 'unknown'
            if path != '/metrics':
                LATENCY.labels(request.method, path).observe(time.perf_counter() - start)
                REQUESTS.labels(request.method, path, str(status)).inc()
