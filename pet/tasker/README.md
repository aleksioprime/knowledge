# Задачник

Учебный API для списка задач. Проект небольшой, но на нём удобно показывать, как складываются вместе темы из базы знаний: каждая заметка добавляет в него одну деталь.

Сейчас в нём есть регистрация и вход по JWT, задачи пользователя в PostgreSQL, миграции Alembic и тесты.

## Запуск

```bash
cp .env.example .env
docker compose up --build
```

При старте контейнер сам применяет миграции (`alembic upgrade head`). Документация API откроется на http://localhost:8000/docs.

## Попробовать

```bash
curl -X POST localhost:8000/auth/register -H 'Content-Type: application/json' \
  -d '{"email": "anna@example.com", "password": "secret123"}'
# {"id":1,"email":"anna@example.com"}

TOKEN=$(curl -s -X POST localhost:8000/auth/token -d 'username=anna@example.com&password=secret123' | jq -r .access_token)

curl -X POST localhost:8000/tasks -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"title": "Купить хлеб", "due_date": "2026-11-01"}'
# {"id":1,"title":"Купить хлеб","done":false,"priority":1,"due_date":"2026-11-01","created_at":"..."}

curl -X PATCH localhost:8000/tasks/1 -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"done": true}'
curl "localhost:8000/tasks?done=true&limit=10" -H "Authorization: Bearer $TOKEN"
```

## Структура

```text
app/
├── main.py            # создание приложения, подключение роутеров, обработчики ошибок
├── models.py          # таблицы SQLAlchemy: User, Task
├── schemas.py         # схемы Pydantic: что принимает и отдаёт API
├── core/
│   ├── config.py      # настройки из переменных окружения
│   ├── database.py    # подключение к БД и сессия
│   └── security.py    # хэширование паролей и JWT
├── api/
│   ├── deps.py        # зависимости: сессия БД, текущий пользователь
│   └── routers/       # HTTP-слой: auth.py, tasks.py
└── services/          # бизнес-логика и запросы к БД
migrations/            # миграции Alembic
tests/                 # тесты API на отдельной тестовой базе
```

Почему так разложено — в заметке [Структура проекта FastAPI](../../framework/fast_api/docs/structure.md).

## Тесты

Тесты создают таблицы в отдельной базе `tasker_test` и удаляют их после каждого теста.

```bash
docker compose up -d db
docker compose exec db createdb -U tasker tasker_test

pip install -r requirements-dev.txt
pytest
# 10 passed
```

Адрес тестовой базы можно поменять переменной `TEST_DATABASE_URL`.

## Как растёт проект

| Что добавляется | Заметка |
|---|---|
| Схемы и валидация данных | [Pydantic](../../python/typing/pydantic.md) |
| Эндпоинты, зависимости, ошибки, структура, JWT | [FastAPI](../../framework/fast_api/README.md) |
| Хранение в PostgreSQL | [SQLAlchemy](../../data/sqlalchemy/README.md) |
| Миграции | [Alembic](../../data/alembic/README.md) |
| Кэш и ограничение частоты запросов | Redis |
| Напоминания о сроках в фоне | Celery |
| Вложения к задачам | S3 / MinIO |
| CI | GitHub Actions |
| Метрики и дашборд | Prometheus, Grafana |

Заметки без ссылок ещё не написаны.
