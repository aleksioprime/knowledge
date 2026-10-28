# Сервис поиска задач

Учебный пример к заметкам [Асинхронный сервис поиска на FastAPI и Elasticsearch](../../docs/elasticsearch.md) и [Функциональные тесты в Docker Compose](../../../../tests/pytest/docs/functional.md). Сервис только читает: задачи попадают в индекс `tasks` через [ETL из PostgreSQL](../../../../data/elasticsearch/examples/etl/README.md), а API ищет по ним и кэширует ответы в Redis.

## Состав

| Путь | Что внутри |
|---|---|
| `src/main.py` | сборка приложения, `lifespan` создаёт и закрывает клиенты Elasticsearch и Redis |
| `src/core/config.py` | настройки из окружения (pydantic-settings) |
| `src/db/` | создание клиентов и зависимости, которые их отдают |
| `src/models/task.py` | схема задачи |
| `src/services/` | `TaskService` (поиск, кэш) и обёртка над Redis |
| `src/api/deps.py`, `src/api/v1/tasks.py` | провайдер сервиса и эндпоинты |
| `scripts/load_fixtures.py`, `scripts/tasks.json` | пересоздать индекс и загрузить 8 примеров |
| `docker-compose.yml` | Elasticsearch на `29200`, Redis на `26379`, API на `28000` |
| `tests/functional/` | функциональные тесты в своём Compose |

## Эндпоинты

| Запрос | Что делает |
|---|---|
| `GET /api/v1/tasks/search?query=&page_number=1&page_size=50` | полнотекстовый поиск по `title` и `description` |
| `GET /api/v1/tasks/?tag=&sort=-modified&page_number=1&page_size=50` | список с фильтром по метке, сортировка `modified` или `-modified` |
| `GET /api/v1/tasks/{id}` | одна задача, `404`, если её нет |

`page_size` — от 1 до 100. Страницы дальше 10 000-го результата не отдаются (`422`).

## Запуск в Docker

```bash
cd framework/fast_api/examples/search_api
docker compose up -d --build --wait
docker compose run --rm api python -m scripts.load_fixtures
# Загружено задач: 8
```

```bash
curl -s -G localhost:28000/api/v1/tasks/search --data-urlencode 'query=счёт'
# [{"id":"0b6f6a52-...-1f0a2c7d1004","title":"Оплатить счета за квартиру",...}]
```

Кириллицу в адресе передавайте через `--data-urlencode`: без кодирования uvicorn отвечает `400 Invalid HTTP request received`.

Документация — `http://localhost:28000/docs`. Остановить и удалить данные: `docker compose down -v`.

## Запуск без Docker для разработки

Elasticsearch и Redis — в контейнерах, приложение — на своей машине с автоперезагрузкой:

```bash
docker compose up -d --wait elasticsearch redis
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m scripts.load_fixtures
.venv/bin/uvicorn src.main:app --port 28000 --reload
```

Адреса по умолчанию в `src/core/config.py` уже указывают на порты из `docker-compose.yml`. Другие задаются переменными `ELASTIC_URL`, `REDIS_URL`, `TASKS_INDEX`, `CACHE_TTL_SECONDS` или файлом `.env`.

## Кэш

Ключ собирается из всех параметров запроса, поэтому разные страницы и размеры страниц кэшируются отдельно:

```bash
docker compose exec redis redis-cli --raw KEYS '*'
# tasks:id:0b6f6a52-6b0e-4d4c-9a3e-1f0a2c7d1003
# tasks:search:page_number=1&page_size=5&query=%D0%BE%D1%82%D1%87%D1%91%D1%82%D1%8B
# tasks:list:page_number=1&page_size=50&sort=-modified&tag=%D1%81%D1%80%D0%BE%D1%87%D0%BD%D0%BE
```

Значения в ключе закодированы как в URL: так символы `&` и `=` из поискового запроса не перепутаются с разделителями. Ответ живёт 60 секунд, потом сервис снова идёт в Elasticsearch. Почему не сбрасывать кэш при изменении задачи — в [заметке](../../docs/elasticsearch.md#кэш-ответов).

## Функциональные тесты

```bash
docker compose -p kb-search -f tests/functional/docker-compose.yml up --build --abort-on-container-exit --exit-code-from tests
docker compose -p kb-search -f tests/functional/docker-compose.yml down -v
```

Тестовое окружение работает на своих портах (`29201`, `26380`, `28001`) и очищает индекс перед каждым тестом, поэтому данные разработки не пострадают. Как запустить тесты с вашей машины против поднятых контейнеров — в [заметке о функциональных тестах](../../../../tests/pytest/docs/functional.md#запуск).
