# Prometheus

Пользователи жалуются, что «Задачник» тормозит. Насколько? С какого времени? На каких эндпоинтах? Без цифр это гадание. Prometheus раз в несколько секунд опрашивает приложения, сохраняет их числовые показатели — **метрики** — и позволяет строить по ним графики и правила тревоги: «если больше 5% запросов падают с ошибкой, сообщи».

В [«Задачнике»](../../pet/tasker/README.md) метрики уже подключены. Запуск вместе с мониторингом:

```bash
docker compose -f docker-compose.yaml -f docker-compose.monitoring.yaml up -d --build
```

Prometheus откроется на http://localhost:9090, [Grafana](../grafana/README.md) — на http://localhost:3000.

## Минимальный пример

Приложение отдаёт метрики текстом по адресу `/metrics`:

```bash
curl localhost:8000/metrics
```

```text
# HELP http_requests_total Количество HTTP-запросов
# TYPE http_requests_total counter
http_requests_total{method="GET",path="/tasks",status="200"} 30.0
http_requests_total{method="GET",path="/tasks/{task_id}",status="200"} 30.0
http_requests_total{method="GET",path="/tasks/{task_id}",status="404"} 30.0
http_requests_total{method="POST",path="/tasks",status="201"} 5.0
```

Prometheus забирает этот текст каждые 5 секунд:

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 5s

scrape_configs:
  - job_name: tasker
    static_configs:
      - targets: ['app:8000']
```

## Как это работает

**Pull-модель.** Не приложение отправляет данные, а Prometheus сам приходит за ними. Если приложение упало, Prometheus это заметит: у цели будет статус `down`. Список целей — на странице Status → Targets.

**Метрика** — имя, набор **меток** (labels) и число. Каждое уникальное сочетание меток — отдельный **временной ряд**. Prometheus хранит, как значение каждого ряда менялось во времени.

**Типы метрик:**

- **Counter** — только растёт: количество запросов, ошибок, созданных задач. Само значение мало что говорит, важна скорость роста;
- **Gauge** — может расти и падать: число задач в очереди, занятая память;
- **Histogram** — раскладывает значения по «корзинам»: сколько запросов уложилось в 10 мс, в 25 мс, в 50 мс… По ним считают перцентили времени ответа.

## Метрики в FastAPI

```python
# app/core/metrics.py
from prometheus_client import Counter, Histogram

REQUESTS = Counter('http_requests_total', 'Количество HTTP-запросов', ['method', 'path', 'status'])
LATENCY = Histogram(
    'http_request_duration_seconds',
    'Время обработки HTTP-запроса',
    ['method', 'path'],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5),
)
TASKS_CREATED = Counter('tasks_created_total', 'Сколько задач создали пользователи')


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
```

Две детали, на которых легко ошибиться:

- **`try/finally`.** Если эндпоинт выбросил исключение, `call_next` тоже его выбрасывает, и без `finally` запрос просто не попадёт в метрики. Получится, что все ошибки 500 невидимы. В первой версии этого примера так и было: база лежала, все запросы падали, а алерт молчал;
- **шаблон пути в метке.** Если писать в метку настоящий путь (`/tasks/1`, `/tasks/2`…), на каждый id появится свой временной ряд, и Prometheus быстро разбухнет.

Метрика бизнес-события ставится прямо в сервисе:

```python
# app/services/tasks.py
TASKS_CREATED.inc()
```

Готовые библиотеки (`prometheus-fastapi-instrumentator`) делают то же самое одной строкой. Ручной вариант здесь — чтобы было видно, что внутри.

## PromQL: вопросы к метрикам

Запросы пишут на странице Graph в Prometheus или в Grafana.

**Сколько запросов в секунду на каждый эндпоинт:**

```promql
sum by (path) (rate(http_requests_total[1m]))
```

```text
{path="/tasks"}            5.75
{path="/tasks/{task_id}"}  4.31
```

`rate(...[1m])` — средняя скорость роста счётчика за последнюю минуту. `sum by (path)` складывает ряды с разными `method` и `status`, оставляя разбивку по пути.

**Сколько ответов каждого кода за 5 минут:**

```promql
sum by (status) (increase(http_requests_total[5m]))
```

**95-й перцентиль времени ответа** — 95% запросов быстрее этого значения:

```promql
histogram_quantile(0.95, sum by (le, path) (rate(http_request_duration_seconds_bucket[1m])))
```

```text
{path="/tasks"}            0.0193   — 19 мс
{path="/tasks/{task_id}"}  0.0095
```

Среднее время ответа обманчиво: один запрос на 10 секунд теряется среди тысячи быстрых. Перцентили показывают, каково самым невезучим пользователям.

**Доля ошибок 5xx:**

```promql
sum(rate(http_requests_total{status=~"5.."}[1m])) / sum(rate(http_requests_total[1m]))
```

Если ошибок не было, ряда с `status=~"5.."` нет вовсе, и запрос вернёт пустой результат, а не 0. Для графика можно дописать `or vector(0)`.

## Алерты

Правило проверяется постоянно, и если условие выполняется дольше `for`, алерт срабатывает:

```yaml
# monitoring/alerts.yml
groups:
  - name: tasker
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[1m]))
            / sum(rate(http_requests_total[1m])) > 0.05
        for: 30s
        labels:
          severity: critical
        annotations:
          summary: 'Больше 5% запросов к «Задачнику» завершаются ошибкой 5xx'
```

Проверим: остановим базу, и все запросы к `/tasks` начнут падать.

```bash
docker compose stop db
```

На странице Alerts алерт сначала **pending** (условие выполняется, но меньше 30 секунд), затем **firing**:

```text
HighErrorRate  firing  Больше 5% запросов к «Задачнику» завершаются ошибкой 5xx  1.0
```

Сам Prometheus никому не пишет. Уведомления в почту, Telegram или Slack рассылает отдельный компонент — **Alertmanager**: он группирует алерты и не даёт засыпать канал сотней одинаковых сообщений.

## Частые ошибки

- **Высокая кардинальность меток.** id пользователя, email или полный URL в метках создают миллионы рядов. В метках — только значения из небольшого известного набора.
- **`rate` сразу после старта.** Для `rate` нужно хотя бы два замера. Сразу после появления ряда запрос может ничего не вернуть, хотя счётчик уже не нулевой.
- **Gauge вместо Counter.** Количество запросов, сохранённое как Gauge, обнуляется при перезапуске, и Prometheus не поймёт, что это сброс. `rate` по Counter корректно учитывает перезапуски.
- **Несколько процессов uvicorn или gunicorn.** У каждого рабочего процесса свои счётчики, а `/metrics` отдаёт данные того процесса, которому достался запрос. Для этого у `prometheus_client` есть режим multiprocess.
- **`/metrics` открыт в интернет.** Метрики выдают внутреннее устройство системы. Закрывайте их от внешнего доступа.

## Связанные темы

- [Grafana](../grafana/README.md) — графики и дашборд по этим метрикам
- [Централизованное логирование](../logging/README.md)
- [Учебный проект «Задачник»](../../pet/tasker/README.md)
