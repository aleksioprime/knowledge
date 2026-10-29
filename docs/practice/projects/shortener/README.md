# Сокращатель ссылок

Учебный сервис коротких ссылок вроде bit.ly: принимает длинный URL, выдаёт короткий и перенаправляет по нему на исходный адрес. Проект сделан по плану из разбора [«Сокращатель ссылок»](../../../backend/design/url_shortener.md): там объяснено, почему решения именно такие.

Что внутри: FastAPI, ссылки в PostgreSQL через асинхронный SQLAlchemy 2, миграции Alembic, кэш кодов и счётчики переходов в Redis, тесты на настоящих базах.

## Запуск

```bash
cp .env.example .env
docker compose up --build
```

При старте контейнер сам применяет миграции (`alembic upgrade head`). Документация API откроется на http://localhost:8001/docs.

Порты отличаются от [«Задачника»](../tasker/README.md) — API на 8001, PostgreSQL на 5433, Redis на 6380, — поэтому оба проекта можно держать запущенными одновременно.

## Попробовать

```bash
curl -X POST localhost:8001/api/links -H 'Content-Type: application/json' \
  -d '{"url": "https://github.com/fastapi/fastapi"}'
# {"code":"wKpIpXw","short_url":"http://localhost:8001/wKpIpXw"}

curl -i localhost:8001/wKpIpXw
# HTTP/1.1 302 Found
# location: https://github.com/fastapi/fastapi

curl localhost:8001/api/links/wKpIpXw/stats
# {"code":"wKpIpXw","url":"https://github.com/fastapi/fastapi","clicks":2,"created_at":"2026-10-28T20:43:49.253380"}

curl -i localhost:8001/nothing
# HTTP/1.1 404 Not Found
# {"detail":"Ссылка не найдена"}
```

Код каждый раз случайный, поэтому у вас он будет другим. Браузер по короткой ссылке сразу откроет исходную страницу.

## Как это работает

**Коды.** Семь случайных символов из 62 (цифры и латинские буквы обоих регистров) через `secrets.choice` — это 3,5 трлн вариантов. Коды идут не подряд, поэтому соседние ссылки не перебрать. Если код уже занят, уникальный индекс в базе не даст вставить дубль: сервис ловит `IntegrityError` и пробует новый код, до пяти раз. Если не повезло все пять раз, API отвечает `503`.

**Перенаправление.** Ответ `302`, а не `301`: браузер не запоминает перенаправление и каждый раз заходит в сервис, поэтому переходы можно посчитать.

**Кэш.** `GET /{code}` сначала ищет ключ `link:{code}` в Redis. При промахе берёт ссылку из PostgreSQL и кладёт в Redis на сутки (`CACHE_TTL_SECONDS`). Ссылки не меняются, поэтому сбрасывать кэш не нужно.

```bash
docker compose exec redis redis-cli ttl link:wKpIpXw
# 86400
```

**Статистика.** Каждый переход — `INCR clicks:{code}` в Redis, без `UPDATE` строки в базе: иначе популярная ссылка превратилась бы в горячую строку с постоянными блокировками. Чтобы счётчики пережили перезапуск, у Redis включена запись на диск (`--appendonly yes`). В большой системе их стоит периодически переносить в аналитическое хранилище — об этом в разборе.

## Тесты

Тесты создают таблицы в отдельной базе `shortener_test` и пересоздают их перед каждым тестом, а Redis используют с отдельной базой номер 15.

```bash
docker compose up -d db redis
docker compose exec db createdb -U shortener shortener_test

cd app
pip install -r requirements-dev.txt
pytest
# 10 passed
ruff check .
```

Адреса можно поменять переменными `TEST_DATABASE_URL` и `TEST_REDIS_URL`. Линтер и тесты запускаются в [GitHub Actions](../../../../.github/workflows/shortener.yml) при каждом изменении проекта.

## Структура

```text
docker-compose.yaml    # API, PostgreSQL и Redis с проверками здоровья
.env.example           # переменные окружения для docker compose
app/
├── Dockerfile
├── migrations/        # миграции Alembic
├── src/
│   ├── main.py        # приложение, маршруты, обработчики ошибок
│   ├── service.py     # создание ссылок, перенаправление через кэш, счётчики
│   ├── config.py      # настройки из переменных окружения
│   ├── models.py      # таблица links
│   ├── schemas.py     # схемы Pydantic для запросов и ответов
│   ├── exceptions.py  # ошибки предметной области
│   ├── database/      # подключение к PostgreSQL (db.py) и клиент Redis (cache.py)
│   └── utils/
│       └── shortener.py  # генерация кодов
└── tests/             # тесты API на отдельной тестовой базе
```

Устройство то же, что у «Задачника», только без разбиения на роутеры и сервисы: для трёх маршрутов это лишнее.

## Связанные темы

- [Разбор: сокращатель ссылок](../../../backend/design/url_shortener.md)
- [Кэширование](../../../backend/design/caching.md)
- [Redis в FastAPI](../../../backend/databases/redis/fastapi.md)
- [Alembic](../../../backend/databases/alembic/README.md)
- Обзорный ролик о задаче: https://www.youtube.com/watch?v=qe--uV1qJMI
