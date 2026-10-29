# HTTPX: основы

Сервису задач нужно узнать у сервиса пользователей имя владельца, а потом отправить событие в сервис уведомлений. Межсервисные HTTP-запросы выглядят просто, но именно на них всё и ломается: соседний сервис отвечает 30 секунд и подвешивает ваш, временно отвечает 503, а сто запросов подряд по одному занимают в сто раз больше времени, чем нужно. HTTPX — HTTP-клиент для Python с тем же удобным API, что у `requests`, но с асинхронным режимом и продуманными таймаутами.

```bash
pip install httpx
```

Все примеры лежат в [examples/simple](../examples/simple/README.md) вместе с учебным сервером.

## Минимальный пример

```python
import httpx

response = httpx.get('http://localhost:8001/tasks/42', params={'fields': 'title'})
response.status_code  # 200
response.json()       # {'id': 42, 'title': 'Задача 42'}
response.request.url  # http://localhost:8001/tasks/42?fields=title

response = httpx.post('http://localhost:8001/tasks', json={'title': 'Купить хлеб'})
response.status_code  # 201
```

`params` собирает строку запроса, `json` сериализует тело и ставит `Content-Type: application/json`.

## Ошибки: ответ 4xx и 5xx — не исключение

HTTPX не выбрасывает исключение, если сервер ответил ошибкой: ответ 404 — тоже ответ. Проверять код нужно самому:

```python
response = httpx.get('http://localhost:8001/tasks/404')
response.status_code  # 404
response.is_success   # False

response.raise_for_status()
# HTTPStatusError: Client error '404 Not Found' for url '...'
```

А вот проблемы с сетью — исключения. Их иерархия помогает понять, что случилось:

```text
httpx.HTTPError
├── httpx.HTTPStatusError      — сервер ответил 4xx/5xx (только после raise_for_status)
└── httpx.TransportError       — до ответа дело не дошло
    ├── httpx.TimeoutException — ConnectTimeout, ReadTimeout, WriteTimeout, PoolTimeout
    └── httpx.ConnectError     — сервис не запущен, неверный адрес
```

## Таймауты

По умолчанию HTTPX ждёт 5 секунд на каждую фазу запроса. Это лучше, чем у `requests`, который по умолчанию ждёт бесконечно. Но для межсервисных вызовов значение стоит выбирать осознанно:

```python
httpx.get('http://localhost:8001/slow', timeout=1.0)
# ReadTimeout: timed out

httpx.Timeout(10.0, connect=2.0)
# Timeout(connect=2.0, read=10.0, write=10.0, pool=10.0)
```

- `connect` — установить соединение. Если сервис жив, это миллисекунды, поэтому значение можно держать маленьким;
- `read` — ждать ответа. Зависит от того, что делает сервис;
- `pool` — ждать свободное соединение из пула, если все заняты.

## Клиент вместо отдельных вызовов

`httpx.get(...)` каждый раз открывает новое соединение и закрывает его. Для сервиса, который постоянно ходит к соседу, это дорого: каждый раз заново TCP- и TLS-рукопожатие. `Client` держит пул соединений и переиспользует их, а заодно хранит общие настройки:

```python
with httpx.Client(base_url='http://localhost:8001', timeout=5.0, headers={'X-Service': 'tasks'}) as client:
    client.get('/tasks/1')
    client.get('/tasks/2')  # по тому же соединению
```

В веб-приложении клиент создают **один раз** при старте и закрывают при остановке. В FastAPI это удобно сделать в `lifespan`:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(base_url='http://users-service:8000', timeout=5.0)
    yield
    await app.state.http.aclose()


app = FastAPI(lifespan=lifespan)
```

## Асинхронный режим: запросы параллельно

`AsyncClient` — тот же API с `await`. Главное преимущество: независимые запросы можно отправить одновременно.

```python
import asyncio


async def main():
    async with httpx.AsyncClient(base_url='http://localhost:8001', timeout=5.0) as client:
        for task_id in range(1, 6):
            await client.get(f'/tasks/{task_id}')
        # по очереди: 2.6 с

        responses = await asyncio.gather(*(client.get(f'/tasks/{task_id}') for task_id in range(1, 6)))
        # параллельно: 0.5 с


asyncio.run(main())
```

Каждый ответ сервера занимает полсекунды. По очереди пять запросов идут 2,6 секунды, параллельно — столько же, сколько один.

В `async def` эндпоинтах FastAPI используйте только `AsyncClient`. Синхронный `httpx.get` внутри `async def` остановит весь сервер на время запроса.

## Повторы

Встроенные повторы есть только на уровне транспорта и только для ошибок **соединения**:

```python
transport = httpx.HTTPTransport(retries=3)
client = httpx.Client(transport=transport)
```

Ответ `503` они не повторят — это уже ответ. Для временных ошибок сервера пишут свой цикл или берут библиотеку `tenacity`:

```python
RETRY_STATUSES = {502, 503, 504}


def get_with_retries(client: httpx.Client, url: str, attempts: int = 4) -> httpx.Response:
    for attempt in range(1, attempts + 1):
        try:
            response = client.get(url)
            if response.status_code not in RETRY_STATUSES:
                return response
        except httpx.TransportError:
            pass
        if attempt < attempts:
            time.sleep(0.2 * 2 ** (attempt - 1))  # 0.2, 0.4, 0.8 с
    response.raise_for_status()
    return response


get_with_retries(client, '/flaky').json()
# попытка 1: 503
# попытка 2: 503
# {'status': 'ok', 'attempt': 3}
```

Повторять можно только безопасные запросы: `GET`, а также `PUT` и `DELETE`, которые [идемпотентны](../../../web/http/request_response.md). Повтор `POST /orders` может создать два заказа.

## Частые ошибки

- **Нет проверки статуса.** `response.json()` от ответа 500 вернёт текст ошибки, а код спокойно пойдёт дальше. Вызывайте `raise_for_status()` или проверяйте `status_code`.
- **Новый клиент на каждый запрос.** Пул соединений не работает, а при высокой нагрузке заканчиваются свободные порты — см. [TCP-соединения и порты](../../../web/http/tcp_connections.md).
- **Таймаут на полминуты.** Если сосед завис, ваш сервис держит запрос и соединение 30 секунд, и вскоре зависает сам. Таймаут должен быть меньше, чем время, которое готов ждать *ваш* клиент.
- **Повтор неидемпотентного запроса.** Для `POST` повтор возможен, только если сервер поддерживает ключ идемпотентности.
- **Ошибка соседа, отданная своему клиенту как есть.** Сервис пользователей ответил 404, а вы возвращаете клиенту 404 на `/tasks/1`. Переводите ошибки соседа в понятные для своего API — как в [примере с двумя сервисами](../examples/fastapi/README.md).

## Связанные темы

- [Как проходит HTTP-запрос](../../../web/http/README.md)
- [Асинхронность в Python](../../../python/multitask/async.md)
- [API Gateway](../../api_gateway/README.md)
