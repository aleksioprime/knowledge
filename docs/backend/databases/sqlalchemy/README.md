# SQLAlchemy

**SQLAlchemy** — самая распространённая библиотека Python для работы с реляционными базами. Она состоит из двух слоёв:

- **Core** — сборка SQL-запросов из Python-выражений;
- **ORM** — таблицы описываются классами, а строки становятся объектами.

Заметки написаны для SQLAlchemy 2.0 и PostgreSQL. Примеры совпадают с учебным проектом [«Задачник»](../../../practice/projects/tasker/README.md).

## Содержание

1. [Модели и сессия](basics.md) — описание таблиц, движок, сессия, выборка, изменение и удаление
2. [Связи и проблема N+1](relationships.md) — `relationship`, `selectinload` и `joinedload`, многие ко многим, каскады
3. [Асинхронный SQLAlchemy](async.md) — `AsyncSession`, asyncpg, ошибка `MissingGreenlet`, сессия в FastAPI

## Связанные темы

- [Alembic](../alembic/README.md) — миграции схемы
- [SQL](../sql/README.md) — что SQLAlchemy генерирует под капотом
- [PostgreSQL](../postgres/README.md)
- [Руководство по SQLAlchemy на русском](https://blog.skillfactory.ru/rukovodstvo-po-sqlalchemy-v-python/)
