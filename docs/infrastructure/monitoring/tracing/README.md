# Распределённая трассировка

Метрика показывает: 99-й перцентиль (p99) ответа `GET /tasks/1` — полсекунды, хотя обычно он укладывается в 110 мс. Запрос прошёл через nginx, сервис задач, сервис пользователей и две базы. Лог каждого сервиса по отдельности говорит «запрос обработан», но не говорит, **где именно** ушли эти 400 мс. Трассировка собирает путь одного запроса через все сервисы в одно дерево с длительностями каждого шага — и медленный шаг видно сразу.

Метрики отвечают на вопрос «есть ли проблема» ([Prometheus](../prometheus/README.md)), логи — «что случилось» ([логирование](../logging/README.md)), трассы — «где именно в цепочке».

Пример в [`example/`](examples/) проверен на Python 3.12, OpenTelemetry SDK 1.45.1 (инструментирование 0.66b1), FastAPI 0.162, Jaeger 2.22.0 и nginx 1.31.8 в Docker на Apple M1.

## Минимальный пример

nginx → сервис `tasks` → по httpx сервис `users`, трассы уходят в Jaeger:

```bash
cd docs/infrastructure/monitoring/tracing/examples
docker compose -p kb-tracing up -d --build
curl -s localhost:58080/tasks/1
# {"id":1,"title":"Сдать отчёт","author_id":10,"author":{"id":10,"name":"Анна"}}
python show_trace.py tasks
```

```text
trace_id 2e10c83193d85ef8e04ee15e513bdcb5
tasks: GET /tasks/{task_id}              +  0.0 мс  104.0 мс
  tasks: SELECT task                     +  0.3 мс   20.4 мс
  tasks: GET                             + 21.0 мс   82.0 мс
    users: GET /users/{user_id}          + 21.7 мс   81.1 мс
      users: SELECT user                 + 21.9 мс   80.3 мс
```

Колонки: смещение от начала запроса и длительность шага. Из 104 мс 80 ушло на запрос в базу сервиса пользователей. То же дерево в виде диаграммы — в веб-интерфейсе Jaeger: http://localhost:56686.

Остановить и удалить: `docker compose -p kb-tracing down -v --rmi local`.

## Как это работает

**Трасса** (trace) — путь одного запроса. **Спан** (span) — один шаг этого пути: обработка HTTP-запроса, исходящий запрос к соседу, запрос в базу. У спана есть:

- имя (`SELECT task`), время начала и длительность;
- `trace_id` — общий для всех спанов трассы, и `span_id` — свой; плюс `parent_span_id`, из него и строится дерево;
- **атрибуты** — пары ключ-значение: `http.route`, `db.query.text`, `user.id`. Имена лучше брать из семантических соглашений OpenTelemetry (semantic conventions), тогда Jaeger и другие инструменты их понимают;
- **события** (events) — отметки времени внутри спана: «кэш пуст, идём в базу», исключение;
- **статус** — `UNSET`, `OK` или `ERROR`. Ошибочные спаны Jaeger подсвечивает красным, и по ним можно искать.

Аналогия — посылка с трек-номером. Трек-номер один (`trace_id`), а каждый сортировочный центр добавляет свою отметку с временем прибытия и отправки (спаны). По истории отметок видно, где посылка пролежала неделю.

### Передача контекста

Чтобы спан сервиса `users` оказался ребёнком спана из `tasks`, `tasks` должен передать `trace_id` и свой `span_id` вместе с запросом. Стандарт для HTTP — заголовок **W3C `traceparent`**:

```text
traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01
             │  └ trace_id (32 hex)              └ id родительского спана └ флаги: 01 — трасса записывается
             └ версия формата
```

Инструментированный httpx добавляет его сам, а инструментированный FastAPI сам читает. Проверка вручную — отправим в `users` запрос с придуманным заголовком:

```bash
docker compose -p kb-tracing exec tasks python -c "
import httpx
httpx.get('http://users:8000/users/10',
          headers={'traceparent': '00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01'})"
curl -s localhost:56686/api/traces/0af7651916cd43dd8448eb211c80319c
```

```text
GET /users/{user_id}  span e86af111363af89c  родитель b7ad6b7169203331
SELECT user           span eeb4e02ed4cfb5ff  родитель e86af111363af89c
```

Сервис продолжил чужую трассу. Если где-то в цепочке заголовок теряется (самописный HTTP-клиент, очередь без передачи заголовков), трасса рвётся на две несвязанные.

Через брокер сообщений контекст передают так же — в заголовках сообщения. Для Kafka, RabbitMQ и Celery есть готовые инструментирования.

## OpenTelemetry в FastAPI

**OpenTelemetry** (OTel) — общий стандарт и набор библиотек для трасс, метрик и логов. Код пишется против API OpenTelemetry, а куда уходят данные — Jaeger, Grafana Tempo, Zipkin, облачный сервис — решает настройка экспортёра.

```text
fastapi==0.162.0
httpx==0.28.1
opentelemetry-sdk==1.45.1
opentelemetry-exporter-otlp-proto-http==1.45.1
opentelemetry-instrumentation-fastapi==0.66b1
opentelemetry-instrumentation-httpx==0.66b1
```

Пакеты инструментирования пока в статусе beta, поэтому нумерация у них своя. Выходят они парами с SDK: SDK 1.45.1 и инструментирование 0.66b1 — из одного релиза. Фиксируйте пару целиком, иначе pip может поставить несовместимые версии.

Настройка — один раз при старте приложения ([`app/telemetry.py`](examples/app/telemetry.py)):

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_tracing(app: FastAPI) -> None:
    # Имя сервиса и семплер SDK берёт из OTEL_SERVICE_NAME и OTEL_TRACES_SAMPLER*,
    # адрес Jaeger — из OTEL_EXPORTER_OTLP_ENDPOINT
    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app, exclude_spans=['send', 'receive'])
    HTTPXClientInstrumentor().instrument()
```

- `TracerProvider` — фабрика трассировщиков, `BatchSpanProcessor` копит готовые спаны и отправляет пачками в фоновом потоке, не задерживая ответ;
- **автоинструментирование**: `FastAPIInstrumentor` создаёт спан на каждый входящий запрос (`GET /tasks/{task_id}`) и читает `traceparent`, `HTTPXClientInstrumentor` — спан на каждый исходящий запрос (`GET`) и добавляет `traceparent`. Ни одной строчки в обработчиках;
- `exclude_spans=['send', 'receive']` убирает служебные спаны ASGI (`http send`) — без него на каждый запрос их по три лишних;
- в [`docker-compose.yaml`](examples/docker-compose.yaml) задано `OTEL_SEMCONV_STABILITY_OPT_IN=http`: инструментирование пишет атрибуты под новыми стабильными именами (`http.request.method`, `url.path`) вместо старых (`http.method`, `http.target`).

Готовые инструментирования есть для SQLAlchemy, asyncpg, psycopg, Redis, Celery, Kafka и многих других (`opentelemetry-instrumentation-*`). Можно вообще не трогать код: `opentelemetry-instrument uvicorn app.tasks:app` включит всё найденное при запуске, но явная настройка в коде понятнее.

### Ручные спаны

Автоинструментирование видит только границы сервиса. Что происходит внутри — запрос в базу, вызов тяжёлой функции — размечают вручную:

```python
tracer = trace.get_tracer('tasks')


async def select_task(task_id: int) -> dict | None:
    with tracer.start_as_current_span('SELECT task') as span:
        span.set_attribute('db.system.name', 'postgresql')
        span.set_attribute('db.query.text', 'SELECT id, title, author_id FROM task WHERE id = $1')
        await asyncio.sleep(0.02)  # имитация запроса в базу
        task = TASKS.get(task_id)
        span.set_attribute('db.response.returned_rows', int(task is not None))
        return task
```

`start_as_current_span` делает спан текущим: всё, что создаётся внутри (в том числе спаны httpx), становится его детьми. Исключение, вылетевшее из `with`, само записывается в спан как событие, и статус становится `ERROR`.

В примере базы нет — запрос имитирует `sleep`, чтобы не усложнять compose. В реальном сервисе для SQLAlchemy или asyncpg ручные спаны не нужны: их создаст инструментирование драйвера.

Событие внутри текущего спана:

```python
trace.get_current_span().add_event('кэш пуст, идём в базу', {'user.id': user_id})
```

### Ошибки

Задача 2 ссылается на несуществующего автора: `users` отвечает 404, `tasks` — 502.

```text
trace_id 09de100615b1e943fc23faee0caf86f4
tasks: GET /tasks/{task_id}              +  0.0 мс  107.8 мс ERROR
  tasks: SELECT task                     +  1.7 мс   20.9 мс
  tasks: GET                             + 23.0 мс   83.5 мс ERROR
    users: GET /users/{user_id}          + 24.4 мс   82.0 мс
      users: SELECT user                 + 24.7 мс   80.9 мс
```

Серверный спан `users` с ответом 404 — не ошибка: по соглашениям OpenTelemetry 4xx на сервере означает ошибку клиента, а не сервиса. А для вызывающей стороны тот же 404 — ошибка, поэтому клиентский спан `GET` красный.

## Экспорт в Jaeger по OTLP

**OTLP** (OpenTelemetry Protocol) — родной протокол OpenTelemetry: gRPC на порту 4317 или HTTP на 4318. Jaeger принимает его сам, промежуточный коллектор не обязателен.

Раньше в Python был отдельный `opentelemetry-exporter-jaeger` со старым протоколом Jaeger (thrift). Он объявлен устаревшим и больше не выпускается: Jaeger давно принимает OTLP, а сам Jaeger 1.x с его агентом (`jaeger-agent`, UDP 6831) снят с поддержки. Во второй версии Jaeger собран на основе OpenTelemetry Collector. Если в старых статьях встречается `JaegerExporter(agent_host_name=..., agent_port=6831)` и образ `jaegertracing/all-in-one` — это та самая устаревшая схема.

Jaeger 2 одним образом `jaegertracing/jaeger` запускает всё сразу — приём, хранение в памяти и веб-интерфейс, как раньше `all-in-one`. Для учебного стенда хватает, в продакшене трассы хранят в Elasticsearch, OpenSearch или Cassandra.

```yaml
jaeger:
  image: jaegertracing/jaeger:2.22.0
  ports:
    - "56686:16686"  # веб-интерфейс и HTTP API; OTLP 4318 нужен только внутри сети compose
```

Сервисам достаточно переменной `OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4318` — HTTP-экспортёр сам допишет `/v1/traces`.

### Трассы через HTTP API

В Jaeger 2.22 работает API `/api/v3/...` (ответ в формате OTLP JSON) и получение трассы по id `/api/traces/<trace_id>`. Старый поиск `/api/traces?service=tasks` и `/api/services`, которые часто встречаются в статьях, здесь отвечают 404:

```bash
curl -s localhost:56686/api/v3/services
# {"services":["users","tasks","jaeger"]}

curl -s 'localhost:56686/api/v3/traces?query.service_name=tasks&query.start_time_min=2026-10-28T00:00:00Z&query.start_time_max=2026-10-30T00:00:00Z&query.duration_min=300ms'
```

На этом построен [`show_trace.py`](examples/show_trace.py) из примера: он ищет трассы сервиса и печатает дерево.

## Поиск медленных запросов

В сервисе `users` каждый двадцатый запрос в базу идёт полсекунды вместо 80 мс. 200 запросов через nginx:

```text
p50=113 мс  p95=127 мс  p99=537 мс
```

Метрики говорят только, что хвост есть. Ищем трассы длиннее 300 мс:

```bash
python show_trace.py tasks --min-ms 300
```

```text
трасс за последний час: 8
trace_id bb720fb41175e968d88b9a73056534bc
tasks: GET /tasks/{task_id}              +  0.0 мс  532.5 мс
  tasks: SELECT task                     +  0.4 мс   20.9 мс
  tasks: GET                             + 22.0 мс  509.4 мс
    users: GET /users/{user_id}          + 23.8 мс  507.4 мс
      users: SELECT user                 + 24.7 мс  505.9 мс
```

Медленный — запрос в базу в `users`, а не сеть и не `tasks`. В интерфейсе Jaeger то же самое делается полем Min Duration на странице поиска. Grafana умеет связывать график p99 с трассами (exemplars): точка на графике ведёт прямо в трассу.

## X-Request-Id и связь с логами

Трассы показывают структуру, логи — подробности. Связывают их общим идентификатором в каждой строке лога.

**`X-Request-Id`** генерирует первый узел на входе — здесь nginx. Переменная `$request_id` — случайные 32 hex-символа на каждый запрос:

```nginx
# Пришёл свой X-Request-Id — берём его, нет — генерирует nginx
map $http_x_request_id $req_id {
    default $http_x_request_id;
    ""      $request_id;
}

log_format traced '$remote_addr "$request" $status request_id=$req_id $request_time';

server {
    listen 80;
    access_log /dev/stdout traced;

    location / {
        proxy_set_header X-Request-Id $req_id;       # передать сервису
        add_header X-Request-Id $req_id always;      # вернуть клиенту
        proxy_pass http://tasks:8000;
    }
}
```

`map` нужен, чтобы не затереть идентификатор, если запрос пришёл от другого сервиса или балансировщика уже с ним. Если nginx смотрит прямо в интернет, наоборот, лучше всегда ставить свой `$request_id`: клиент может прислать что угодно. Клиент получает идентификатор в ответе — его можно попросить прислать в поддержку.

В сервисе middleware кладёт заголовок в `ContextVar` и в атрибут серверного спана, исходящий httpx-клиент передаёт его дальше, а фильтр логирования дописывает в каждую запись `request_id`, `trace_id` и `span_id`:

```python
request_id_var: ContextVar[str] = ContextVar('request_id', default='-')


class TraceContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        ctx = trace.get_current_span().get_span_context()
        record.trace_id = format(ctx.trace_id, '032x') if ctx.is_valid else '-'
        record.span_id = format(ctx.span_id, '016x') if ctx.is_valid else '-'
        record.request_id = request_id_var.get()
        return True


async def pass_request_id(request: httpx.Request) -> None:
    request.headers['X-Request-Id'] = request_id_var.get()


users = httpx.AsyncClient(base_url=USERS_URL, timeout=2.0, event_hooks={'request': [pass_request_id]})
```

Как устроены фильтры и форматтеры — в заметке [Логирование в Python](../../../languages/python/stdlib/logging.md). Готовый вариант без своего фильтра — `opentelemetry-instrumentation-logging`: он добавляет в записи поля `otelTraceID` и `otelSpanID`.

Логи трёх сервисов для запроса из минимального примера (ответ пришёл с `X-Request-Id: b70005883053b582c405e3db44a30b83`):

```text
# nginx
192.168.65.1 "GET /tasks/1 HTTP/1.1" 200 request_id=b70005883053b582c405e3db44a30b83 0.104
# tasks
INFO httpx request_id=b70005883053b582c405e3db44a30b83 trace_id=2e10c83193d85ef8e04ee15e513bdcb5 span_id=f0edf51b432af86c HTTP Request: GET http://users:8000/users/10 "HTTP/1.1 200 OK"
INFO tasks request_id=b70005883053b582c405e3db44a30b83 trace_id=2e10c83193d85ef8e04ee15e513bdcb5 span_id=f0edf51b432af86c задача 1 отдана
# users
INFO users request_id=b70005883053b582c405e3db44a30b83 trace_id=2e10c83193d85ef8e04ee15e513bdcb5 span_id=6d297402466082e7 пользователь 10 найден
```

`trace_id` в логах совпадает с трассой `2e10c831…` из минимального примера. `span_id` в строках `tasks` — серверный спан запроса: строки записаны вне ручного спана `SELECT task`.

По `request_id` из жалобы пользователя находим строки во всех сервисах (в [Loki](../logging/README.md) — `{service=~".+"} |= "73e1f62..."`), из строки лога берём `trace_id` и открываем трассу в Jaeger. И наоборот: из медленной трассы — в логи по `trace_id`.

Зачем два идентификатора, если есть `trace_id`? `X-Request-Id` появляется раньше — на входе, до любого сервиса с OpenTelemetry, — попадает в лог nginx и существует, даже если трасса не записана из-за семплирования. Сам nginx в этом примере трассы не пишет, трасса начинается в `tasks`. Для nginx есть модуль `ngx_otel_module` (пакет `nginx-module-otel`), но в официальных образах `nginx:1.31.8` и `nginx:1.31.8-alpine` его нет.

## Семплирование

Записывать каждый запрос в продакшене дорого: тысячи запросов в секунду дают десятки тысяч спанов в секунду, которые нужно отправить по сети, принять и хранить. Поэтому записывают долю.

**Head-based** (решение в начале) — первый сервис при создании трассы бросает монетку и записывает решение во флаг `traceparent` (`-01` — записывать, `-00` — нет). Остальные сервисы следуют решению родителя, и трасса либо записывается целиком, либо не записывается вовсе. Настройка — переменными окружения:

```yaml
OTEL_TRACES_SAMPLER: parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG: "0.1"   # 10%
```

`parentbased_` — слушаться решения родителя, если оно есть; `traceidratio` — для новой трассы решать по `trace_id`, поэтому решение одинаково на всех узлах. 200 запросов при доле 0,1:

```text
трасс tasks: 17
трасс users: 17
```

17 из 200 — около ожидаемых 20, и у обоих сервисов ровно одни и те же трассы, без обрывков.

Минус head-based: решение принимается до того, как известно, будет ли запрос медленным или ошибочным. При 10% девять из десяти редких медленных запросов просто не попадут в Jaeger. **Tail-based** (решение в конце) это исправляет: все спаны отправляются в OpenTelemetry Collector, он ждёт окончания трассы и сохраняет все ошибочные и медленные плюс долю обычных. Цена — коллектор должен держать в памяти все незавершённые трассы.

## Стоимость

- **CPU в приложении.** Создание спана с атрибутом и `BatchSpanProcessor` на Apple M1: 11–17 мкс на записываемый спан и около 4 мкс на незаписываемый. На запрос с десятью спанами это доли миллисекунды — обычно незаметно, но в горячем цикле спан на каждую итерацию уже лишний;
- **сеть и хранилище** — главная статья расходов. Растут линейно с долей семплирования и числом спанов на запрос;
- **очередь экспортёра.** `BatchSpanProcessor` держит до 2048 спанов (`OTEL_BSP_MAX_QUEUE_SIZE`); если Jaeger недоступен и очередь заполнилась, новые спаны выбрасываются, а приложение продолжает работать. Это правильно: трассировка не должна ронять сервис;
- **данные в атрибутах.** Тексты запросов с параметрами, токены, персональные данные в атрибутах попадают в хранилище трасс, к которому доступ обычно шире, чем к базе.

## Частые ошибки

- **Трасса рвётся на куски.** Где-то не передаётся `traceparent`: HTTP-клиент не инструментирован, инструментирование включено не в том процессе (в веб-приложении, а запросы шлёт воркер), сообщение в очередь ушло без заголовков. Проверка — посмотреть заголовки запроса на принимающей стороне.
- **Спанов нет вообще.** `TracerProvider` не установлен через `trace.set_tracer_provider` — тогда API OpenTelemetry молча работает вхолостую. Либо неверный `OTEL_EXPORTER_OTLP_ENDPOINT`: для HTTP-экспортёра это `http://jaeger:4318` без `/v1/traces`, для gRPC — `http://jaeger:4317`.
- **Спаны теряются при остановке.** `BatchSpanProcessor` отправляет пачку раз в 5 секунд; короткий скрипт или задача Celery завершаются раньше. Нужен `provider.shutdown()` при выходе.
- **Старый Jaeger-экспортёр.** `opentelemetry-exporter-jaeger` и `jaeger-agent` устарели — используйте OTLP.
- **100% трасс в продакшене.** Хранилище трасс растёт быстрее, чем хранилище логов. Начинают с 1–10% и tail-based для ошибок.
- **Высокая кардинальность в имени спана.** `GET /tasks/1`, `GET /tasks/2`… вместо `GET /tasks/{task_id}` — поиск и группировка по операциям перестают работать. Конкретные значения — в атрибуты, не в имя.
- **`X-Request-Id` от клиента без проверки** в публичном API — клиент может подсунуть чужой идентификатор или мусор в логи.

## Когда не использовать

Монолит с одной базой: путь запроса и так виден в профилировщике и логах, а SQL — в `EXPLAIN` и `pg_stat_statements`. Трассировка окупается, когда запрос пересекает хотя бы два сервиса или ходит в несколько внешних систем. Для ответа на вопрос «сколько» (RPS, доля ошибок, p99) нужны [метрики](../prometheus/README.md), а не трассы.

## Связанные темы

- [Prometheus](../prometheus/README.md) — метрики и p99, с которых начинается поиск
- [Централизованное логирование](../logging/README.md) — где искать строки по `request_id` и `trace_id`
- [Логирование в Python](../../../languages/python/stdlib/logging.md) — фильтры и форматтеры
- [Устойчивость](../../../backend/design/resilience.md) — таймауты и повторы, которые хорошо видны в трассах
- [API Gateway](../../../backend/microservices/api_gateway/README.md) — ещё одно место, где появляется `X-Request-Id`
