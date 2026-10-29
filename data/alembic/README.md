# Alembic: миграции схемы базы данных

В «Задачнике» понадобился приоритет задач. Добавить поле в модель SQLAlchemy — одна строка. Но в базе таблица `tasks` уже есть, в ней лежат данные, а `create_all` существующие таблицы не трогает. Нужно выполнить `ALTER TABLE` одинаково на ноутбуке каждого разработчика, на тестовом стенде и в продакшене, и ничего не потерять. Эту задачу решают миграции: каждое изменение схемы оформляется отдельным файлом, а Alembic помнит, какие из них уже применены.

```bash
pip install alembic
```

## Минимальный пример

Добавили поле в модель:

```python
# app/models.py
class Task(Base):
    ...
    priority: Mapped[int] = mapped_column(default=1, server_default='1')
```

Попросили Alembic сравнить модели с базой и написать миграцию:

```bash
alembic revision --autogenerate -m "add task priority"
# Detected added column 'tasks.priority'
# Generating migrations/versions/18af122c5557_add_task_priority.py ... done
```

```python
# migrations/versions/18af122c5557_add_task_priority.py
revision = '18af122c5557'
down_revision = '0a0136b19b93'


def upgrade() -> None:
    op.add_column('tasks', sa.Column('priority', sa.Integer(), server_default='1', nullable=False))


def downgrade() -> None:
    op.drop_column('tasks', 'priority')
```

Применили:

```bash
alembic upgrade head
# Running upgrade 0a0136b19b93 -> 18af122c5557, add task priority
```

Это [настоящая миграция «Задачника»](../../pet/tasker/migrations/versions/18af122c5557_add_task_priority.py).

## Как это работает

**Миграции — цепочка.** У каждой есть `revision` (свой id) и `down_revision` (id предыдущей). Так Alembic знает порядок:

```bash
alembic history
# 0a0136b19b93 -> 18af122c5557 (head), add task priority
# <base> -> 0a0136b19b93, create users and tasks
```

**База помнит, где она.** Alembic создаёт в базе таблицу `alembic_version` с одной строкой — id последней применённой миграции. `upgrade head` применяет всё, что идёт после неё, а `downgrade -1` откатывает одну миграцию:

```bash
alembic current     # 18af122c5557 (head)
alembic downgrade -1
# Running downgrade 18af122c5557 -> 0a0136b19b93, add task priority
```

**Autogenerate сравнивает модели с базой.** Alembic подключается к базе, читает её текущую схему и сравнивает с `Base.metadata` — описанием всех моделей. Разница превращается в команды `op.add_column`, `op.create_table` и т. д. Это **черновик**, который нужно прочитать перед применением (подробнее ниже).

## Подключение к проекту

```bash
alembic init -t async migrations  # шаблон для асинхронного драйвера
```

Появятся `alembic.ini` и папка `migrations/`. В `migrations/env.py` нужно сделать две вещи: взять адрес базы из настроек приложения (а не хранить пароль в `alembic.ini`) и показать Alembic модели:

```python
# migrations/env.py
from app import models  # noqa: F401 — модели должны быть импортированы, чтобы попасть в metadata
from app.core.config import settings
from app.core.database import Base

config = context.config
config.set_main_option('sqlalchemy.url', settings.database_url)

target_metadata = Base.metadata
```

Команды Alembic запускают из корня проекта — там же, где лежит `alembic.ini`. В «Задачнике» миграции применяются сами при старте контейнера: `alembic upgrade head && uvicorn ...`.

## Чего autogenerate не понимает

**Переименование.** Переименовали `title` в `name` — Alembic видит, что одна колонка пропала, а другая появилась:

```bash
alembic revision --autogenerate -m "rename title"
# Detected added column 'tasks.name'
# Detected removed column 'tasks.title'
```

```python
op.add_column('tasks', sa.Column('name', sa.String(length=200), nullable=False))
op.drop_column('tasks', 'title')  # все названия задач будут удалены!
```

Перед применением такую миграцию нужно исправить вручную:

```python
op.alter_column('tasks', 'title', new_column_name='name')
```

Ещё autogenerate не замечает или замечает не всегда: изменение значений в `Enum`, переименование таблиц, некоторые изменения `server_default`, а также ограничения `CHECK`. Правило простое: **сгенерированную миграцию всегда читают глазами**.

## Обязательное поле в таблице с данными

Добавляем `color: Mapped[str]` без значения по умолчанию. Миграция сгенерируется, но на таблице, где уже есть строки, упадёт:

```text
NotNullViolationError: column "color" of relation "tasks" contains null values
```

PostgreSQL не может добавить колонку `NOT NULL`: у существующих строк в ней окажется `NULL`. Есть два выхода:

1. дать значение по умолчанию — `server_default='gray'`, как сделано с `priority`;
2. заполнить колонку данными в три шага:

```python
def upgrade() -> None:
    op.add_column('tasks', sa.Column('color', sa.String(length=20), nullable=True))
    op.execute("UPDATE tasks SET color = CASE WHEN done THEN 'green' ELSE 'gray' END")
    op.alter_column('tasks', 'color', nullable=False)
```

Это пример **миграции данных**: кроме схемы она меняет и содержимое таблицы.

## Посмотреть SQL, не выполняя его

Иногда миграцию выполняет администратор базы или нужно проверить, что именно будет сделано:

```bash
alembic upgrade 0a0136b19b93:18af122c5557 --sql
```

```sql
BEGIN;
ALTER TABLE tasks ADD COLUMN priority INTEGER DEFAULT '1' NOT NULL;
UPDATE alembic_version SET version_num='18af122c5557' WHERE alembic_version.version_num = '0a0136b19b93';
COMMIT;
```

## Частые ошибки

- **Пустая миграция после autogenerate.** Alembic не видит модели: в `env.py` не импортирован модуль с моделями или указан не тот `target_metadata`.
- **Правка уже применённой миграции.** Если миграцию применили хотя бы на одном стенде, менять её нельзя: там она больше не выполнится. Изменения оформляйте новой миграцией.
- **Две «головы».** Два разработчика одновременно создали миграции от одной и той же предыдущей. Alembic сообщит `Multiple head revisions`. Решение — `alembic merge heads -m "merge"` или переставить `down_revision` у своей миграции.
- **`create_all` вместе с Alembic.** Если таблицы создала `create_all`, Alembic о них не знает, и первая миграция упадёт с `relation already exists`. В рабочей базе схему меняют только миграциями. `create_all` уместен в тестах.
- **Тяжёлая миграция на большой таблице.** `ALTER TABLE` может заблокировать таблицу надолго. Как менять большие таблицы без простоя, разобрано в [задачах по PostgreSQL](../postgres/docs/tasks.md).

## Связанные темы

- [SQLAlchemy: модели и сессия](../sqlalchemy/docs/basics.md)
- [PostgreSQL](../postgres/README.md)
- [Учебный проект «Задачник»](../../pet/tasker/README.md)
