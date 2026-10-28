# Задачник

Учебный API для списка задач. Проект небольшой, но на нём удобно показывать, как складываются вместе темы из базы знаний: каждая заметка добавляет в него одну деталь.

Сейчас это каркас: FastAPI отдаёт задачи из памяти, а PostgreSQL уже запускается рядом и ждёт этапа с SQLAlchemy.

## Запуск

```bash
cp .env.example .env
docker compose up --build
```

Документация API откроется на http://localhost:8000/docs.

Без Docker:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Попробовать

```bash
curl -X POST localhost:8000/tasks -H 'Content-Type: application/json' -d '{"title": "Купить хлеб", "due_date": "2026-11-01"}'
# {"title":"Купить хлеб","due_date":"2026-11-01","id":1,"done":false}

curl localhost:8000/tasks/5
# {"detail":"Задача не найдена"}
```

## Как будет расти проект

| Что добавляется | Заметка |
|---|---|
| Схемы и валидация данных | [Pydantic](../../python/typing/pydantic.md) |
| Хранение в PostgreSQL | SQLAlchemy, Alembic |
| Структура проекта, зависимости, ошибки, JWT | FastAPI |
| Кэш и ограничение частоты запросов | Redis |
| Напоминания о сроках в фоне | Celery |
| Вложения к задачам | S3 / MinIO |
| Тесты и CI | Pytest, GitHub Actions |
| Метрики и дашборд | Prometheus, Grafana |

Заметки без ссылок ещё не написаны.
