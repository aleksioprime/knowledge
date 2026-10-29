# Функциональные тесты в Docker Compose

Юнит-тесты сервиса поиска зелёные, а после выкладки поиск отвечает 500: в образ не попал пакет, адрес Elasticsearch в настройках указывает на `localhost`, а индекс создаётся с другим маппингом. Юнит-тесты этого не видят: они проверяют функции по отдельности, с подменёнными клиентами. Функциональные тесты проверяют сервис целиком, как его увидит клиент: собранный образ, настоящие Elasticsearch и Redis, запросы по HTTP.

Код ниже — из [учебного примера сервиса поиска задач](../../frameworks/fastapi/examples/search_api/README.md) (сам сервис разобран в [отдельной заметке](../../frameworks/fastapi/elasticsearch.md)). Основы pytest — фикстуры, параметризация, `conftest.py` — в [README](README.md).

## Минимальный пример

Тесты живут в собственном контейнере и ходят к сервису по сети:

```yaml
# tests/functional/docker-compose.yml (сокращённо)
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.15.3
    healthcheck:
      test: ["CMD-SHELL", "curl -fs 'localhost:9200/_cluster/health?wait_for_status=yellow&timeout=1s'"]

  api:
    build: ../..
    image: kb-search-api
    environment:
      ELASTIC_URL: http://elasticsearch:9200
    depends_on:
      elasticsearch:
        condition: service_healthy

  tests:
    build: .
    environment:
      SERVICE_URL: http://api:8000
    depends_on:
      api:
        condition: service_healthy
```

```python
# tests/functional/test_tasks.py
async def test_get_task(http_client, es_write_data):
    task = make_task(1, title='Купить хлеб', tags=['дом'])
    await es_write_data([task])

    response = await http_client.get(f'/api/v1/tasks/{task["id"]}')

    assert response.status_code == 200
    assert response.json()['title'] == 'Купить хлеб'
```

```bash
docker compose -p kb-search -f tests/functional/docker-compose.yml up --build --abort-on-container-exit --exit-code-from tests
```

```text
tests-1  | test_cache.py::test_search_is_cached PASSED          [  4%]
...
tests-1  | test_tasks.py::test_list_invalid_sort PASSED         [100%]
tests-1  | ============================= 21 passed in 12.14s ==============================
tests-1 exited with code 0
```

## Как это работает

### Юнит, интеграционные и функциональные тесты

| | Что проверяют | Зависимости | Как вызывают код |
|---|---|---|---|
| Юнит | одну функцию или класс | подменены (моки, фейки) | импортом |
| Интеграционные | связку частей: сервис и настоящая база | настоящие, но приложение в том же процессе | импортом или через `TestClient` |
| Функциональные | поведение системы целиком, глазами клиента | настоящие, в контейнерах | только по сети: HTTP, очередь |

Границы размыты, и в разных командах слова используют по-разному. Главный признак функциональных тестов: **они не импортируют код приложения**. Тест знает только адрес сервиса и его контракт — пути, параметры, формат ответа.

### Почему снаружи, а не через `TestClient`

С `TestClient(app)` или `httpx.AsyncClient(transport=ASGITransport(app))` запрос не выходит из процесса тестов. Это быстро и удобно для интеграционных тестов, но мимо проходят:

- **образ**: забытый пакет в `requirements.txt`, файл, не скопированный в `Dockerfile`;
- **настройки**: переменные окружения, адреса соседних сервисов в сети Compose;
- **запуск**: gunicorn с несколькими процессами, `lifespan`, порты;
- **настоящий Redis и Elasticsearch** с их задержками и поведением.

Функциональные тесты запускают сервис так же, как в продакшене, и поэтому ловят эти ошибки. Плата — время: в примере полный прогон вместе с запуском контейнеров занимает около 45 секунд, из них сами тесты — 12.

Из того, что тесты не импортируют приложение, следуют ещё две вещи. Тестам не важно, на чём написан сервис: его можно переписать, а тесты останутся. И у тестов свои зависимости, свой `Dockerfile` и свой `requirements.txt`.

### Тест-план

Прежде чем писать код, полезно перечислить сценарии: что делаем, что ожидаем. Для сервиса поиска:

| Сценарий | Шаги | Ожидание |
|---|---|---|
| Поиск находит формы слова | записать 30 задач «Подготовить отчёт №N», 20 «Купить продукты №N», 1 с «отчёты» в описании; искать `отчёты` | 200, 31 задача |
| Пагинация | тот же набор; `query=отчёт&page_size=10&page_number=4` | 1 задача; пятая страница — пустой список |
| Неверные параметры | `page_size=0`, `page_size=101`, `page_number=0`, без `query`, `page_number=101&page_size=100` | 422 |
| Детали задачи | записать задачу; запросить по `id` | 200, поля совпадают |
| Нет задачи | запросить случайный UUID | 404, `{"detail": "Задача не найдена"}` |
| Фильтр и сортировка | 4 задачи, 3 с меткой «работа»; запросить `tag=работа` и `sort=modified` | только 3 задачи, по убыванию и по возрастанию даты |
| Ответ берётся из кэша | записать задачу; искать; удалить документ прямо в Elasticsearch; искать снова | второй ответ равен первому |
| Ключ кэша учитывает все параметры | то же, но второй запрос с другим `page_size` | пустой список: в кэше такого ключа нет |

Каждая строка превращается в тест, а похожие — в один параметризованный:

```python
@pytest.mark.parametrize(
    ('params', 'expected_count'),
    [
        ({'query': 'отчёты'}, 31),
        ({'query': 'продукты'}, 20),
        ({'query': 'отчёт', 'page_size': 10}, 10),
        ({'query': 'отчёт', 'page_size': 10, 'page_number': 4}, 1),
        ({'query': 'отчёт', 'page_size': 10, 'page_number': 5}, 0),
        ({'query': 'несуществующее'}, 0),
    ],
)
async def test_search(http_client, search_data, params, expected_count):
    response = await http_client.get('/api/v1/tasks/search', params=params)

    assert response.status_code == 200
    assert len(response.json()) == expected_count
```

Проверка кэша — самый показательный сценарий: изнутри сервиса не видно, откуда пришёл ответ, а снаружи это легко проверить, изменив данные в обход сервиса:

```python
async def test_search_is_cached(http_client, es_client, es_write_data):
    task = make_task(1, title='Подготовить отчёт')
    await es_write_data([task])
    first = await http_client.get('/api/v1/tasks/search', params={'query': 'отчёт'})

    await es_client.delete(index=settings.tasks_index, id=task['id'], refresh=True)
    second = await http_client.get('/api/v1/tasks/search', params={'query': 'отчёт'})

    assert len(first.json()) == 1
    assert second.json() == first.json()
```

Если отключить чтение из кэша (`Cache.get` всегда возвращает `None`), падают ровно тесты кэша:

```text
FAILED test_cache.py::test_search_is_cached - AssertionError: assert [] == [{...
FAILED test_cache.py::test_task_details_are_cached - assert 404 == 200
======================== 2 failed, 19 passed in 11.64s =========================
```

### Структура

```text
search_api/
├── Dockerfile, requirements.txt, src/   # сервис
└── tests/functional/
    ├── docker-compose.yml   # elasticsearch, redis, api, tests
    ├── Dockerfile           # образ с тестами
    ├── requirements.txt     # зависимости тестов, не сервиса
    ├── pytest.ini
    ├── settings.py          # адреса из окружения
    ├── conftest.py          # клиенты, подготовка и очистка данных
    ├── testdata/            # маппинг индекса и фабрика документов
    ├── utils/wait_for_es.py # ожидание с backoff, если нет healthcheck
    └── test_*.py
```

Маппинг индекса лежит в `testdata/tasks_mapping.json` — копией, а не импортом из сервиса: тесты не зависят от кода приложения. В этом примере индекс создаёт ETL, поэтому тесты сами играют его роль.

### Настройки: одни тесты, два места запуска

```python
# tests/functional/settings.py
class Settings(BaseSettings):
    service_url: str = 'http://localhost:28001'
    elastic_url: str = 'http://localhost:29201'
    redis_url: str = 'redis://localhost:26380/0'
    tasks_index: str = 'tasks'
```

Значения по умолчанию — порты тестового Compose на вашей машине. В контейнере `tests` их заменяют переменные окружения из `docker-compose.yml` (`SERVICE_URL: http://api:8000` и так далее). Так одни и те же тесты запускаются и в Compose, и из IDE.

### Фикстуры

```python
# tests/functional/conftest.py
@pytest.fixture(scope='session')
async def http_client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(base_url=settings.service_url, timeout=10) as client:
        yield client


@pytest.fixture(scope='session', autouse=True)
async def tasks_index(es_client: AsyncElasticsearch) -> None:
    await es_client.indices.delete(index=settings.tasks_index, ignore_unavailable=True)
    await es_client.indices.create(index=settings.tasks_index, mappings=TASKS_MAPPING)


@pytest.fixture(autouse=True)
async def clean_state(tasks_index, es_client: AsyncElasticsearch, redis_client: Redis) -> None:
    await es_client.delete_by_query(
        index=settings.tasks_index, query={'match_all': {}}, refresh=True, conflicts='proceed',
    )
    await redis_client.flushdb()


@pytest.fixture
def es_write_data(es_client: AsyncElasticsearch) -> WriteTasks:
    async def write(tasks: list[dict]) -> None:
        actions = [
            {'_index': settings.tasks_index, '_id': task['id'], '_source': {k: v for k, v in task.items() if k != 'id'}}
            for task in tasks
        ]
        _, errors = await async_bulk(es_client, actions, refresh='wait_for', raise_on_error=False)
        assert not errors, errors

    return write
```

- Клиенты — на всю сессию: соединения открываются один раз.
- Индекс пересоздаётся один раз за сессию, а **перед каждым тестом** очищаются и индекс, и Redis. Без `FLUSHDB` тест кэша получит ответ, закэшированный соседним тестом с тем же запросом, и результат будет зависеть от порядка запуска.
- `es_write_data` — **фабрика**: фикстура возвращает функцию, и тест сам решает, какие документы записать.
- `refresh='wait_for'` дожидается, пока документы станут видны поиску. Без него Elasticsearch покажет их примерно через секунду, и тест, который ищет сразу после записи, будет то проходить, то падать.

### Асинхронные фикстуры: pytest-asyncio

```ini
# tests/functional/pytest.ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = session
asyncio_default_test_loop_scope = session
```

`asyncio_mode = auto` делает каждую `async def`-функцию тестом и каждую `async`-фикстуру асинхронной без маркеров `@pytest.mark.asyncio`.

Две строки про `loop_scope` нужны в pytest-asyncio 1.x. Цикл событий там создаётся отдельно для каждого теста, если не сказано иное. А клиенты ES, Redis и httpx из сессионных фикстур привязаны к циклу, в котором их создали. Если оставить тестам цикл на функцию (`asyncio_default_test_loop_scope = function`), в этом примере 13 тестов из 21 падают с `RuntimeError: Event loop is closed` и `RuntimeError: Timeout context manager should be used inside a task` (это aiohttp внутри клиента Elasticsearch). Поэтому тесты и фикстуры здесь работают в одном цикле на сессию. Без `asyncio_default_fixture_loop_scope` pytest-asyncio выводит предупреждение о том, что настройка не задана. Старый приём с переопределением фикстуры `event_loop` в версии 1.x больше не работает.

### Ожидание зависимостей

Elasticsearch становится готов к запросам не сразу, а через десятки секунд после старта контейнера. Если тесты начнутся раньше, все упадут.

**`depends_on` без условия** ждёт только запуска контейнера, а не готовности сервиса внутри. Тот же прогон без условий:

```text
elastic_transport.ConnectionError: Connection error caused by: ... Cannot connect to host elasticsearch:9200
============================== 21 errors in 4.42s ==============================
```

**`healthcheck` + `condition: service_healthy`** — основной способ. Compose сам опрашивает сервис и запускает зависимый контейнер, только когда проверка проходит. Цепочка в примере: Elasticsearch и Redis здоровы → стартует `api` → его `/health` отвечает → стартуют `tests`. Проверка у Elasticsearch — `_cluster/health?wait_for_status=yellow`: открытый порт ещё не значит, что кластер готов искать. В образе `python:3.12-slim` нет `curl`, поэтому `api` проверяется самим Python:

```yaml
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 2s
      retries: 15
```

**Скрипт ожидания с backoff** (`utils/wait_for_es.py`) — запасной путь: опрашивать `ping()` с растущей паузой, пока не ответит или не выйдет время. Он нужен там, где healthcheck недоступен: зависимости подняты не через Compose, или тесты запускаются с вашей машины против только что стартовавших контейнеров (`python -m utils.wait_for_es && pytest`). В Compose он дублирует healthcheck и прячет логику ожидания в коде тестов.

### Тестировать тот же образ

```yaml
  api:
    build: ../..
    image: kb-search-api
```

`build` указывает на тот же `Dockerfile`, что используется для выкладки, а `image` даёт собранному образу то же имя, что в основном `docker-compose.yml` сервиса. Тесты проверяют ровно тот артефакт, который поедет в продакшен, а не отдельную «тестовую» сборку. В CI образ собирают один раз, прогоняют на нём тесты и публикуют именно его.

Тестовый Compose использует свои порты на машине (`29201`, `26380`, `28001`): тесты очищают индекс и `FLUSHDB`, и случайно запустить их против данных разработки было бы обидно.

## Запуск

Всё в контейнерах — как в CI:

```bash
cd docs/backend/frameworks/fastapi/examples/search_api
docker compose -p kb-search -f tests/functional/docker-compose.yml up --build --abort-on-container-exit --exit-code-from tests
echo $?   # 0, если все тесты прошли
docker compose -p kb-search -f tests/functional/docker-compose.yml down -v
```

- `--build` пересобирает образы: без него тесты пойдут против старого кода сервиса.
- `--abort-on-container-exit` останавливает всё окружение, когда контейнер `tests` завершился. Иначе Elasticsearch и сервис продолжат работать, и команда не вернёт управление.
- `--exit-code-from tests` делает код выхода команды равным коду выхода pytest. Без него CI не узнает, что тесты упали.
- `-p kb-search` — имя проекта: контейнеры и тома не пересекутся с другими проектами из той же папки.
- `down -v` удаляет контейнеры вместе с томами, следующий прогон начнётся с чистого листа.

Для отладки удобнее поднять только зависимости и сервис, а тесты запускать с вашей машины: работают точки останова, `-k`, `--lf`, повторный запуск за секунды.

```bash
docker compose -p kb-search -f tests/functional/docker-compose.yml up -d --build --wait elasticsearch redis api
cd tests/functional
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/pytest -k cache
```

Адреса по умолчанию в `settings.py` указывают на опубликованные порты, так что ничего настраивать не нужно. Изменили код сервиса — пересоберите `api` той же командой `up -d --build`.

## Pytest или коллекция Postman

Сценарии API часто проверяют коллекцией Postman, запущенной через Newman. Для функциональных тестов сервиса pytest удобнее:

- **Подготовка данных.** Тесту нужно записать документы прямо в Elasticsearch, очистить Redis, удалить документ в обход API. В pytest это обычный код с клиентами; в Postman — цепочки запросов и скрипты в песочнице.
- **Параметризация.** Шесть вариантов поиска — шесть строк в `parametrize`, а не шесть копий запроса.
- **Изоляция.** Фикстуры с очисткой между тестами, а не порядок запросов в коллекции, от которого зависит результат.
- **Код рядом с сервисом.** Тесты лежат в том же репозитории, проходят ревью и рефакторинг; diff читается, а JSON коллекции — с трудом.

Postman уместен для ручной проверки и знакомства с API, для дымового прогона после выкладки на стенд (несколько запросов «жив ли сервис») и когда тесты пишут тестировщики, которые не работают с Python. Если в команде уже есть хорошая коллекция для ручной проверки, держать её стоит, но как дополнение, а не замену.

## Частые ошибки

- **Импорт кода приложения в тесты.** `from src.main import app` или общий маппинг из `src` — и тесты уже проверяют не образ, а код в соседней папке. Тесты должны знать только адрес и контракт.
- **Поиск сразу после записи без `refresh`.** Тест проходит на быстрой машине и падает в CI. Записывайте с `refresh='wait_for'` или вызывайте `indices.refresh` перед поиском.
- **Общий кэш между тестами.** Без `FLUSHDB` перед каждым тестом второй тест получает ответ первого из Redis. Особенно коварно: тест проходит в одиночку (`-k`) и падает в полном прогоне.
- **Данные, оставшиеся от прошлого теста.** Тест, который ждёт «ровно 20 задач», зависит от того, кто записал задачи до него. Очищайте индекс перед каждым тестом, а не после: упавший тест может не дойти до очистки.
- **`depends_on` без `condition: service_healthy`.** Все тесты падают с `ConnectionError`, потому что Elasticsearch ещё не стартовал.
- **Незафиксированные версии.** `elasticsearch` без версии в `requirements.txt` однажды поставит клиент 9.x, и сервер 8.x ответит `media_type_header_exception`; образ `redis:latest` сменит мажорную версию. Фиксируйте версии пакетов и образов, обновляйте их осознанно.
- **Запуск без `--build`.** Тесты прогоняются против образа, собранного вчера, и проходят, хотя новый код сломан.
- **Сессионные async-фикстуры, а тесты в своём цикле.** `RuntimeError: Event loop is closed` начиная со второго теста. Задайте `asyncio_default_test_loop_scope = session` или `@pytest.mark.asyncio(loop_scope='session')`.

## Когда не использовать

Функциональные тесты медленные и требуют Docker. Правила вроде «ключ кэша учитывает все параметры» или «номер страницы превращается в `from`» быстрее и точнее проверять юнит-тестами сервиса. Функциональных тестов должно быть немного: основные сценарии и то, что ломается только на стыке (настройки, образ, кэш, реальный поиск).

## Связанные темы

- [Pytest: основы, фикстуры, параметризация](README.md)
- [Пример с полным бэкендом и функциональными тестами на PostgreSQL](examples/backend_full/README.md)
- [Асинхронный сервис поиска на FastAPI и Elasticsearch](../../frameworks/fastapi/elasticsearch.md)
- [Docker Compose на практике](../../../infrastructure/devtools/docker/compose.md) — `depends_on`, `healthcheck`, имена сервисов в сети
- [Elasticsearch: полнотекстовый поиск](../../databases/elasticsearch/search.md)
