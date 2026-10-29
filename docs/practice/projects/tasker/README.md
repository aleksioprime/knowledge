# Задачник

Учебный API для списка задач. Проект небольшой, но на нём удобно показывать, как складываются вместе темы из базы знаний: каждая заметка добавляет в него одну деталь.

Сейчас в нём есть регистрация и вход по JWT, задачи пользователя в PostgreSQL, миграции Alembic, кэш и ограничение попыток входа на Redis, напоминания о сроках через Celery, метрики Prometheus, тесты и CI.

## Запуск

```bash
cp .env.example .env
docker compose up --build
```

При старте контейнер сам применяет миграции (`alembic upgrade head`). Документация API откроется на http://localhost:8000/docs.

Запускаются пять сервисов: API, Celery-воркер, Celery Beat (каждый день в 9:00 ставит рассылку напоминаний), PostgreSQL и Redis. Разослать напоминания вручную:

```bash
docker compose exec worker celery -A app.worker call app.worker.remind_about_due_tasks
docker compose logs worker
# Письмо для anna@example.com: Срок задачи — завтра — Сдать отчёт
```

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

curl localhost:8000/tasks/stats -H "Authorization: Bearer $TOKEN"
# {"total":1,"done":1} — ответ кэшируется в Redis на минуту
```

## Мониторинг

```bash
docker compose -f docker-compose.yaml -f docker-compose.monitoring.yaml up -d --build
```

- Grafana: http://localhost:3000 → дашборд «Задачник» (запросы, время ответа, ошибки, логи);
- Prometheus: http://localhost:9090, метрики приложения — http://localhost:8000/metrics;
- логи всех контейнеров проекта собирает Grafana Alloy в Loki.

## Структура

```text
app/
├── main.py            # создание приложения, подключение роутеров, обработчики ошибок
├── worker.py          # Celery: фоновые задачи и расписание
├── models.py          # таблицы SQLAlchemy: User, Task
├── schemas.py         # схемы Pydantic: что принимает и отдаёт API
├── core/
│   ├── config.py      # настройки из переменных окружения
│   ├── database.py    # подключение к БД и сессия
│   ├── cache.py       # клиент Redis
│   ├── email.py       # отправка писем (учебная заглушка)
│   ├── metrics.py     # метрики Prometheus
│   └── security.py    # хэширование паролей и JWT
├── api/
│   ├── deps.py        # зависимости: сессия БД, Redis, текущий пользователь, лимит попыток входа
│   └── routers/       # HTTP-слой: auth.py, tasks.py
└── services/          # бизнес-логика и запросы к БД
migrations/            # миграции Alembic
tests/                 # тесты API на отдельной тестовой базе
postman/               # коллекция Postman для проверки работающего API
monitoring/            # Prometheus, Grafana, Loki и Alloy
```

Почему так разложено — в заметке [Структура проекта FastAPI](../../../backend/frameworks/fastapi/structure.md).

## Тесты

Тесты создают таблицы в отдельной базе `tasker_test` и удаляют их после каждого теста, а Redis используют с отдельной базой номер 15.

```bash
docker compose up -d db redis
docker compose exec db createdb -U tasker tasker_test

pip install -r requirements-dev.txt
pytest
# 15 passed
```

Адреса можно поменять переменными `TEST_DATABASE_URL` и `TEST_REDIS_URL`.

Проверка работающего API коллекцией Postman:

```bash
docker run --rm -v "$PWD/postman":/etc/newman postman/newman:6-alpine \
  run tasker.postman_collection.json --env-var baseUrl=http://host.docker.internal:8000
```

Всё это — линтер, тесты и проверка API в Docker — запускается в [GitHub Actions](../../../../.github/workflows/tasker.yml) при каждом изменении проекта.

## Как растёт проект

| Что добавляется | Заметка |
|---|---|
| Схемы и валидация данных | [Pydantic](../../../languages/python/typing/pydantic.md) |
| Эндпоинты, зависимости, ошибки, структура, JWT | [FastAPI](../../../backend/frameworks/fastapi/README.md) |
| Хранение в PostgreSQL | [SQLAlchemy](../../../backend/databases/sqlalchemy/README.md) |
| Миграции | [Alembic](../../../backend/databases/alembic/README.md) |
| Кэш и ограничение частоты запросов | [Redis](../../../backend/databases/redis/fastapi.md) |
| Напоминания о сроках в фоне | [Celery](../../../backend/frameworks/celery/first_task.md) |
| Вложения к задачам | [S3](../../../backend/databases/s3/README.md) — пока отдельным примером, в проект не встроено |
| Проверка работающего API | [Postman и Newman](../../../backend/testing/postman/README.md) |
| CI | [GitHub Actions](../../../infrastructure/cicd/github/README.md) |
| Метрики, дашборд и логи | [Prometheus](../../../infrastructure/monitoring/prometheus/README.md), [Grafana](../../../infrastructure/monitoring/grafana/README.md), [Loki](../../../infrastructure/monitoring/logging/README.md) |

