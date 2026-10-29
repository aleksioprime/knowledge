# Асинхронный сервис поиска на FastAPI и Elasticsearch

Задачи лежат в PostgreSQL, [ETL](../../databases/elasticsearch/etl.md) копирует их в индекс Elasticsearch `tasks`, и теперь пользователям нужен API: найти задачи по словам, показать задачи с меткой «срочно», открыть одну задачу. Такой сервис почти ничего не считает сам: он принимает запрос, ходит в Elasticsearch и Redis и ждёт ответа. Поэтому его пишут асинхронным: пока один запрос ждёт Elasticsearch, тот же процесс обслуживает другие.

Весь код ниже — из [учебного примера](examples/search_api/README.md), который запускается в Docker одной командой.

## Минимальный пример

Сервис получает клиенты снаружи и ничего не знает про HTTP:

```python
# src/services/task.py
class TaskService:
    def __init__(self, elastic: AsyncElasticsearch, cache: Cache, index: str):
        self.elastic = elastic
        self.cache = cache
        self.index = index

    async def get_by_id(self, task_id: UUID) -> Task | None:
        key = f'tasks:id:{task_id}'
        if (cached := await self.cache.get(key)) is not None:
            return Task.model_validate_json(cached)
        try:
            hit = await self.elastic.get(index=self.index, id=str(task_id))
        except NotFoundError:
            return None
        task = Task.from_hit(hit)
        await self.cache.set(key, task.model_dump_json())
        return task
```

Эндпоинт получает готовый сервис через зависимость и превращает «не нашлось» в 404:

```python
# src/api/v1/tasks.py
@router.get('/{task_id}')
async def get_task(task_id: UUID, service: TaskServiceDep) -> Task:
    task = await service.get_by_id(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Задача не найдена')
    return task
```

```bash
curl -s localhost:28000/api/v1/tasks/0b6f6a52-6b0e-4d4c-9a3e-1f0a2c7d1003
# {"id":"0b6f6a52-...-1f0a2c7d1003","title":"Купить продукты","description":"Хлеб, молоко, сыр","done":true,"owner":"anna","tags":["дом"],"modified":"2026-10-19T18:00:00Z"}
curl -s localhost:28000/api/v1/tasks/0b6f6a52-6b0e-4d4c-9a3e-1f0a2c7d9999
# {"detail":"Задача не найдена"}
```

## Как это работает

### Слои

Раскладка та же, что в [структуре проекта](structure.md), только вместо базы данных — поисковый движок:

```text
src/
├── main.py              # приложение и lifespan
├── core/config.py       # настройки из окружения
├── db/                  # создать клиент и отдать его зависимостью
│   ├── elastic.py
│   └── redis.py
├── models/task.py       # схема ответа
├── services/
│   ├── cache.py         # get/set с TTL и построение ключа
│   └── task.py          # TaskService: запросы к Elasticsearch и кэш
└── api/
    ├── deps.py          # get_task_service — собирает сервис из клиентов
    └── v1/tasks.py      # эндпоинты
```

Префикс `/api/v1` оставляет место для второй версии API: старые клиенты продолжат ходить в `v1`, пока новые переходят на `v2`.

### Клиенты живут столько же, сколько приложение

Клиент Elasticsearch и клиент Redis держат пулы соединений. Создавать их на каждый запрос — значит каждый раз заново открывать TCP-соединения. Их создают один раз при старте и закрывают при остановке. Для этого есть `lifespan`: код до `yield` выполняется при запуске, после — при остановке.

```python
# src/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.elastic = create_elastic()
    app.state.redis = create_redis()
    yield
    await app.state.elastic.close()
    await app.state.redis.aclose()


app = FastAPI(title=settings.project_name, lifespan=lifespan)
```

Старый способ — `@app.on_event('startup')` и `@app.on_event('shutdown')`. В FastAPI 0.143 он помечен устаревшим, а в Starlette 1.x, на которой FastAPI построен, его уже убрали. В `lifespan` создание и закрытие ресурса стоят рядом, и забыть закрыть сложнее.

Клиенты лежат в `app.state`, а [зависимости](dependencies.md) достают их оттуда:

```python
# src/db/elastic.py
def get_elastic(request: Request) -> AsyncElasticsearch:
    return request.app.state.elastic
```

```python
# src/api/deps.py
def get_task_service(
    elastic: Annotated[AsyncElasticsearch, Depends(get_elastic)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> TaskService:
    cache = Cache(redis, ttl_seconds=settings.cache_ttl_seconds)
    return TaskService(elastic=elastic, cache=cache, index=settings.tasks_index)


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
```

Сервис создаётся на каждый запрос, но это дёшево: он только хранит ссылки на общие клиенты. Зато его легко собрать в тесте с другими клиентами или вызвать из скрипта без FastAPI.

### Почему всё асинхронное

Всё приложение работает в одном потоке с одним циклом событий (event loop). Пока `await` ждёт ответа сети, цикл переключается на другие запросы. Но если внутри `async def` вызвать что-то **блокирующее** — `time.sleep`, синхронный клиент Elasticsearch, `requests.get`, — цикл стоит, и ждут **все** запросы процесса.

```python
@app.get('/blocking')
async def blocking():
    time.sleep(1)  # так же ведёт себя синхронный Elasticsearch(...).search(...)
    return {'ok': True}


@app.get('/async')
async def non_blocking():
    await asyncio.sleep(1)
    return {'ok': True}
```

Пять одновременных запросов к каждому эндпоинту:

```text
/blocking 5.1 с
/async 1.1 с
```

Запросы к `/blocking` выполнились строго по очереди. Поэтому в асинхронном сервисе нужны асинхронные клиенты: `AsyncElasticsearch` (пакет `elasticsearch[async]`, внутри aiohttp) и `redis.asyncio.Redis`.

Если асинхронной библиотеки нет, объявите эндпоинт через обычный `def`: FastAPI выполнит его в пуле потоков и цикл событий не заблокирует (подробнее — в [первом приложении](first_app.md)). Внутри `async def` блокирующий вызов можно вынести в поток через `await run_in_threadpool(func, ...)` из `fastapi.concurrency`.

### Поиск и параметры

```python
# src/api/v1/tasks.py
PageNumber = Annotated[int, Query(ge=1, description='Номер страницы, с единицы')]
PageSize = Annotated[int, Query(ge=1, le=100, description='Размер страницы')]


@router.get('/search')
async def search_tasks(
    service: TaskServiceDep,
    query: Annotated[str, Query(min_length=1, max_length=200)],
    page_number: PageNumber = 1,
    page_size: PageSize = 50,
) -> list[Task]:
    check_result_window(page_number, page_size)
    return await service.search(query, page_number, page_size)
```

`/search` и `/` объявлены **раньше** `/{task_id}`. Иначе запрос `/api/v1/tasks/search` попал бы в `get_task`, и FastAPI ответил бы 422: `search` — не UUID.

Ограничение `le=100` защищает Elasticsearch: без него клиент может попросить `page_size=1000000`. Нарушение любого ограничения FastAPI сам превращает в ответ 422 с описанием ошибки.

В сервисе поиск идёт по двум полям, совпадение в названии весит вдвое больше:

```python
body = {'multi_match': {'query': query, 'fields': ['title^2', 'description']}}
```

Сортировка списка задаётся параметром `sort: Literal['modified', '-modified'] = '-modified'`: минус — по убыванию. Любое другое значение FastAPI отклонит с 422 ещё до вызова сервиса. О самих запросах Elasticsearch — в [заметке о поиске](../../databases/elasticsearch/search.md).

### Пагинация: `from`/`size` и предел в 10 000

Номер и размер страницы превращаются в `from` и `size`:

```python
response = await self.elastic.search(
    index=self.index,
    query=query,
    sort=sort,
    from_=(page_number - 1) * page_size,
    size=page_size,
)
```

Чтобы отдать сотую страницу, Elasticsearch собирает и сортирует все документы до неё на каждом шарде. Поэтому глубина ограничена настройкой индекса `index.max_result_window`, по умолчанию 10 000:

```text
Result window is too large, from + size must be less than or equal to: [10000] but was [10005].
```

Elasticsearch отвечает на это кодом 400, и без проверки сервис вернул бы клиенту 500. В примере эндпоинт заранее отвечает понятной 422:

```python
def check_result_window(page_number: int, page_size: int) -> None:
    if page_number * page_size > MAX_RESULT_WINDOW:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f'Можно получить только первые {MAX_RESULT_WINDOW} результатов, уточните запрос',
        )
```

Поднимать `max_result_window` — плохая идея: глубокие страницы станут медленными и прожорливыми. Людям столько страниц не нужно, а если нужно пройти по всем результатам (выгрузка, бесконечная лента), используют `search_after`: клиент передаёт значения сортировки последнего документа, и Elasticsearch продолжает с них. Для этого нужна однозначная сортировка с полем-«разрешителем ничьих», например `[{'modified': 'desc'}, {'id': 'asc'}]`, где `id` — отдельное `keyword`-поле в документе. По системному `_id` Elasticsearch 8 сортировать не даёт: `Fielddata access on the _id field is disallowed`. Если данные меняются во время обхода, добавляют снимок индекса — point in time (PIT).

### Кэш ответов

Как устроен кэш в Redis, почему клиент один на приложение и как сбрасывать кэш после изменения, разобрано в [заметке о Redis в FastAPI](../../databases/redis/fastapi.md). Здесь два отличия.

**Ключ строится из всех параметров запроса.** Иначе вторая страница вернёт закэшированную первую:

```python
def make_key(prefix: str, **params) -> str:
    filled = {name: value for name, value in params.items() if value is not None}
    return f'{prefix}:{urlencode(sorted(filled.items()))}'


make_key('tasks:search', query='отчёт', page_number=1, page_size=50)
# 'tasks:search:page_number=1&page_size=50&query=%D0%BE%D1%82%D1%87%D1%91%D1%82'
```

Параметры сортируются, чтобы порядок в URL не плодил одинаковых записей, а `urlencode` не даёт символам `&` и `=` из поискового запроса смешаться с разделителями.

**Кэш поиска не сбрасывают точечно, его ограничивают сроком жизни (TTL).** Задачу «Подготовить отчёт» переименовали. Какие ключи сбросить? Её мог вернуть поиск по «отчёт», «отчёты», «подготовить», на любой странице и с любым размером страницы. Список возможных запросов бесконечен, а по ключу не понять, какие задачи лежат внутри. Сбросить все `tasks:search:*` — значит пройти по всем ключам через `SCAN` при каждом изменении и всё равно не успеть за параллельными запросами. К тому же данные меняет не этот сервис, а ETL, который о Redis ничего не знает.

Поэтому ответ живёт 60 секунд (`CACHE_TTL_SECONDS`), и это осознанный компромисс: поиск может отставать от данных на минуту, зато популярные запросы не нагружают Elasticsearch. Для одной задачи по `id` точечный сброс возможен (ключ `tasks:id:<id>`), но изменения всё равно приходят через ETL, так что в примере и здесь работает тот же срок жизни.

### `ORJSONResponse` больше не нужен

Раньше для скорости ставили `default_response_class=ORJSONResponse`: стандартный путь прогонял ответ через `jsonable_encoder` и `json.dumps`, а orjson делал это заметно быстрее. В FastAPI 0.143 (версия примера) `ORJSONResponse` и `UJSONResponse` помечены устаревшими. Если у эндпоинта указан тип ответа (`-> list[Task]`) или `response_model`, FastAPI сам сериализует данные сразу в JSON-байты через Pydantic, который написан на Rust. Это быстрее и не требует дополнительного пакета.

Условие важно: эндпоинт без аннотации, возвращающий `dict`, идёт старым медленным путём. Указывайте тип ответа — это ещё и документация в `/docs`.

### Запуск

Для разработки — uvicorn с перезагрузкой при изменении кода:

```bash
uvicorn src.main:app --port 28000 --reload
```

В продакшене нужно несколько процессов: один процесс Python использует одно ядро. Два варианта:

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

```bash
gunicorn src.main:app --worker-class uvicorn_worker.UvicornWorker --workers 4 --bind 0.0.0.0:8000
```

Gunicorn перезапускает упавшие процессы и умеет плавно перезагружать их по сигналу. Класс воркера `uvicorn.workers.UvicornWorker` из старых инструкций в uvicorn 0.54 выдаёт `DeprecationWarning`: его вынесли в отдельный пакет `uvicorn-worker`, отсюда `uvicorn_worker.UvicornWorker`. В контейнере, где перезапуском занимается Docker или Kubernetes, часто хватает `uvicorn --workers` или вовсе одного процесса на контейнер и нескольких контейнеров.

У каждого процесса свой `lifespan`, а значит, свои клиенты и пулы соединений: при `--workers 4` к Elasticsearch откроется вчетверо больше соединений.

## Частые ошибки

- **Синхронный клиент внутри `async def`.** `Elasticsearch(...)` вместо `AsyncElasticsearch(...)` работает, но под нагрузкой запросы выстраиваются в очередь, как в примере с `time.sleep`. Ошибки при этом нет, только медленно.
- **Клиент на каждый запрос.** Соединения не переиспользуются, а незакрытые клиенты дают `Unclosed client session` в логах. Создавайте клиенты в `lifespan`.
- **Ключ кэша не из всех параметров.** Вторая страница возвращает первую, сортировка по возрастанию — результат по убыванию.
- **Глубокие страницы без проверки.** `page_number=1000` даёт 500 вместо понятной ошибки. Проверяйте `from + size` или переходите на `search_after`.
- **Python-клиент 9.x с сервером 8.x.** Клиент отправляет заголовки совместимости с версией 9, и сервер 8 отвечает 400 `media_type_header_exception`. Мажорная версия клиента должна совпадать с сервером: в примере `elasticsearch[async]==8.19.3` и сервер 8.15.
- **Нет индекса.** Если ETL ещё не создал индекс, `search` бросает `NotFoundError`, и сервис отвечает 500. Индекс создаёт тот, кто пишет данные, а сервис чтения можно научить отвечать пустым списком или 503.

## Когда не использовать

Если задач немного и поиск простой, хватит [полнотекстового поиска PostgreSQL](https://www.postgresql.org/docs/current/textsearch.html) прямо в основном приложении: без второго хранилища, ETL и задержки между записью и поиском. Отдельный сервис поиска нужен, когда поиск нагружен, требует релевантности, опечаток и фильтров по многим полям или живёт отдельно от сервиса, который меняет данные.

## Связанные темы

- [Учебный пример: сервис поиска задач](examples/search_api/README.md)
- [Функциональные тесты в Docker Compose](../../testing/pytest/functional.md) — как проверить этот сервис снаружи
- [Elasticsearch: полнотекстовый поиск](../../databases/elasticsearch/search.md)
- [ETL из PostgreSQL в Elasticsearch](../../databases/elasticsearch/etl.md) — откуда данные в индексе
- [Redis в FastAPI](../../databases/redis/fastapi.md) — кэш и его сброс
- [Зависимости](dependencies.md) и [структура проекта](structure.md)
