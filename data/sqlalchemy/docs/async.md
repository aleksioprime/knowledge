# Асинхронный SQLAlchemy

В асинхронном приложении на FastAPI обычный драйвер базы блокирует весь сервер: пока один запрос ждёт ответа PostgreSQL, остальные стоят. Асинхронный режим SQLAlchemy позволяет ждать базу через `await`, и в это время сервер обслуживает другие запросы. API почти тот же, что в синхронном режиме, но есть пара ловушек, о которые спотыкается каждый.

```bash
pip install "sqlalchemy[asyncio]" asyncpg
```

## Минимальный пример

```python
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

engine = create_async_engine('postgresql+asyncpg://tasker:tasker@localhost:5432/tasker')
Session = async_sessionmaker(engine, expire_on_commit=False)


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with Session() as session:
        session.add(Task(title='Купить хлеб', owner_id=1))
        await session.commit()

        tasks = await session.scalars(select(Task).where(Task.owner_id == 1))
        print([task.title for task in tasks])  # ['Купить хлеб']

    await engine.dispose()


asyncio.run(main())
```

Модели те же, что в [синхронном режиме](basics.md). Отличаются три вещи: асинхронный драйвер в адресе (`postgresql+asyncpg://`), `create_async_engine` с `AsyncSession` и `await` перед каждой операцией, которая ходит в базу.

## Как это работает

Каждая операция с сетью — `execute`, `scalars`, `get`, `commit`, `refresh` — теперь корутина, и её нужно дождаться через `await`. Операции без обращения к базе остаются обычными: `session.add(task)` просто кладёт объект в сессию.

Внутри SQLAlchemy использует библиотеку `greenlet`, чтобы основной код ORM оставался общим для двух режимов. Поэтому ставить нужно с дополнением `[asyncio]`. Без него на части систем `greenlet` не установится, и вы получите:

```text
ImportError: The SQLAlchemy asyncio module requires that the Python 'greenlet' library is installed.
```

В старых версиях SQLAlchemy та же проблема выглядит менее понятно: `ValueError: the greenlet library is required to use this function`.

## Ловушка 1: ленивая загрузка не работает

В синхронном режиме `user.tasks` тихо выполняет запрос при первом обращении. В асинхронном так нельзя: обычное обращение к атрибуту не может сделать `await`.

```python
user = await session.get(User, 1)
user.tasks
# MissingGreenlet: greenlet_spawn has not been called; can't call await_only() here.
# Was IO attempted in an unexpected place?
```

Сообщение пугающее, но смысл простой: «вы попросили данные, которые нужно загрузить из базы, в месте, где ждать нельзя». Решения:

```python
# Загрузить связь вместе с объектом
user = await session.scalar(select(User).options(selectinload(User.tasks)).where(User.id == 1))
print([task.title for task in user.tasks])  # ['Купить хлеб']

# Догрузить связь у уже полученного объекта
task = await session.get(Task, 1)
await session.refresh(task, ['owner'])
print(task.owner.email)  # anna@example.com
```

Неплохая привычка — сразу думать, какие связи нужны эндпоинту, и указывать их в запросе. Это заодно спасает от [проблемы N+1](relationships.md#проблема-n1).

## Ловушка 2: атрибуты после `commit`

По умолчанию после `commit()` сессия помечает все объекты устаревшими: следующее обращение к атрибуту перечитает его из базы. В асинхронном режиме это то же самое неявное обращение к базе:

```python
Session = async_sessionmaker(engine)  # expire_on_commit=True по умолчанию

user = await session.get(User, 1)
user.email = 'anna@new.example.com'
await session.commit()
user.email  # MissingGreenlet
```

Поэтому асинхронную фабрику сессий почти всегда создают с `expire_on_commit=False`: тогда объекты после `commit` сохраняют свои значения. Если нужны значения, которые посчитала база (например, `created_at` со `server_default`), перечитайте объект явно: `await session.refresh(task)`.

## Сессия в FastAPI

Сессию открывают на время одного запроса через [зависимость](../../../framework/fast_api/docs/dependencies.md) с `yield`. Так сделано в «Задачнике»:

```python
# app/core/database.py
engine = create_async_engine(settings.database_url)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
```

Движок один на приложение, а сессия своя у каждого запроса.

## Частые ошибки

- **Одна сессия на несколько параллельных задач.** `AsyncSession` нельзя использовать одновременно из нескольких корутин (`asyncio.gather` с одной сессией). У каждой параллельной задачи должна быть своя сессия.
- **Синхронный драйвер в адресе.** `postgresql+psycopg2://` с `create_async_engine` даст ошибку: нужен асинхронный драйвер — `asyncpg` или `psycopg` (третья версия умеет оба режима).
- **Забытый `await`.** `session.commit()` без `await` просто создаёт корутину и ничего не делает. Python предупредит `RuntimeWarning: coroutine ... was never awaited`, но легко пропустить.
- **Блокирующий код рядом.** Асинхронная база не поможет, если рядом в `async def` вызван `requests.get` или `time.sleep`.

## Связанные темы

- [Модели и сессия](basics.md)
- [Связи и проблема N+1](relationships.md)
- [Асинхронность в Python](../../../python/multitask/async.md)
- [Учебный проект «Задачник»](../../../pet/tasker/README.md)
