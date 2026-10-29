# Подключение к PostgreSQL из Python: asyncpg

Чтобы обратиться к базе данных, программа открывает с ней соединение (connection). Здесь показано, как это делать асинхронным драйвером asyncpg: одиночным соединением на каждый запрос и через пул соединений (connection pool), — и какие методы соединения возвращают строки, одну строку, одно значение или статус операции.

::: warning Примеры этой заметки запускайте локально
Код написан для Python-драйвера asyncpg, ему нужен настоящий сервер PostgreSQL — в браузере его нет. Как поднять сервер, описано в [README раздела](README.md). Запросы выполняются через `await`, поэтому удобнее всего запускать их в Jupyter или в `python -m asyncio`, где `await` работает на верхнем уровне.
:::

## Настройка окружения

```python
# pip install asyncpg
import asyncpg

# Настройки подключения к базе данных
DB_DSN = 'postgresql://postgres:postgres@localhost:5432/test_db'
```

## Одиночное соединение

Для каждого запроса открывается соединение (`asyncpg.connect`), выполняется запрос, и соединение закрывается — даже если произошла ошибка, за это отвечает `try ... finally`.

```python
async def connect():
    """Создаёт одно асинхронное соединение с базой."""
    return await asyncpg.connect(DB_DSN)


async def run_fetch(query, *args):
    """Выполняет SELECT и возвращает список строк (list[Record])."""
    conn = await connect()
    try:
        return await conn.fetch(query, *args)
    finally:
        await conn.close()


async def run_fetchrow(query, *args):
    """Возвращает только первую строку (Record) или None.

    Подходит и для других запросов, возвращающих одну строку,
    например INSERT ... RETURNING.
    """
    conn = await connect()
    try:
        return await conn.fetchrow(query, *args)
    finally:
        await conn.close()


async def run_fetchval(query, *args):
    """Возвращает одно значение: первый столбец первой строки (например, count(*))."""
    conn = await connect()
    try:
        return await conn.fetchval(query, *args)
    finally:
        await conn.close()


async def run_execute(query, *args):
    """Выполняет INSERT/UPDATE/DELETE и возвращает статус операции."""
    conn = await connect()
    try:
        return await conn.execute(query, *args)
    finally:
        await conn.close()
```

Открытие соединения — дорогая операция: сетевое рукопожатие, аутентификация, запуск отдельного процесса на сервере. Для скрипта, который делает пару запросов, это не важно, а для веб-сервиса, который обрабатывает сотни запросов в секунду, — заметно.

## Пул соединений

Пул (`asyncpg.create_pool`) держит несколько уже открытых соединений с PostgreSQL. Когда нужно выполнить запрос, готовое соединение берут из пула через `pool.acquire()`. Внутри блока `async with` доступен объект соединения `conn`, через который вызывают нужный метод; после выхода из блока соединение автоматически возвращается в пул, а не закрывается.

```python
pool = None  # глобальный пул соединений


async def init_pool():
    """Создаёт пул один раз: от 1 до 5 открытых соединений."""
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(DB_DSN, min_size=1, max_size=5)
    return pool


await init_pool()


async def run_fetch(query, *args):
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args)


async def run_fetchrow(query, *args):
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, *args)


async def run_fetchval(query, *args):
    async with pool.acquire() as conn:
        # fetchval берёт значение первого столбца первой строки
        return await conn.fetchval(query, *args)


async def run_execute(query, *args):
    async with pool.acquire() as conn:
        # execute возвращает строку вида 'INSERT 0 1' или 'UPDATE 3'
        return await conn.execute(query, *args)
```

Функции с тем же интерфейсом, что и в варианте с одиночным соединением, поэтому остальной код менять не нужно. В приложении пул создают при старте и закрывают при остановке: `await pool.close()`.

## Сброс и заполнение базы

```python
RESET_QUERY = '''
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    age INT NOT NULL
);
'''

SEED_QUERY = '''
INSERT INTO users (name, age)
VALUES
    ('Alice', 30),
    ('Bob', 22),
    ('Carol', 27);
'''


async def reset_and_seed():
    await run_execute(RESET_QUERY)
    await run_execute(SEED_QUERY)
    print('База сброшена и заполнена!')


await reset_and_seed()
```

```text
База сброшена и заполнена!
```

`execute` без параметров умеет выполнить сразу несколько команд, разделённых `;`, — поэтому `RESET_QUERY` проходит одним вызовом.

## Основные операции

Значения в запрос передаются отдельными аргументами и обозначаются в SQL как `$1`, `$2`, … Драйвер отправляет их на сервер отдельно от текста запроса, поэтому подставлять их в строку через f-строку не нужно и опасно (SQL-инъекция).

```python
# Выборка данных
results = await run_fetch('SELECT * FROM users')
print('Все пользователи:', results)

# Вставка данных: RETURNING возвращает id новой строки, fetchval достаёт это значение
created_id = await run_fetchval(
    'INSERT INTO users (name, age) VALUES ($1, $2) RETURNING id',
    'Dave', 40,
)
results = await run_fetch('SELECT * FROM users ORDER BY id')
print('Все пользователи:', results)
print('Создан пользователь с ID:', created_id)

# Обновление данных
await run_execute('UPDATE users SET age = $1 WHERE id = $2', 41, created_id)
results = await run_fetch('SELECT * FROM users ORDER BY id')
print('Все пользователи:', results)

# Удаление данных
await run_execute('DELETE FROM users WHERE id = $1', created_id)
results = await run_fetch('SELECT * FROM users ORDER BY id')
print('Все пользователи:', results)
```

```text
Все пользователи: [<Record id=1 name='Alice' age=30>, <Record id=2 name='Bob' age=22>, <Record id=3 name='Carol' age=27>]
Все пользователи: [<Record id=1 name='Alice' age=30>, <Record id=2 name='Bob' age=22>, <Record id=3 name='Carol' age=27>, <Record id=4 name='Dave' age=40>]
Создан пользователь с ID: 4
Все пользователи: [<Record id=1 name='Alice' age=30>, <Record id=2 name='Bob' age=22>, <Record id=3 name='Carol' age=27>, <Record id=4 name='Dave' age=41>]
Все пользователи: [<Record id=1 name='Alice' age=30>, <Record id=2 name='Bob' age=22>, <Record id=3 name='Carol' age=27>]
```

`Record` ведёт себя как кортеж и как словарь одновременно: `row[0]`, `row['name']`, `dict(row)`.

### Что видит сервер

Сами SQL-запросы можно попробовать прямо здесь. `INSERT ... RETURNING` возвращает таблицу из одной строки с одной колонкой — `fetchrow` превратит её в `Record`, а `fetchval` достанет из неё значение `4`. Для `UPDATE` и `DELETE` сервер возвращает только метку вида `UPDATE 1` — её и отдаёт `execute`.

```sql run
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    age INT NOT NULL
);
INSERT INTO users (name, age) VALUES ('Alice', 30), ('Bob', 22), ('Carol', 27);

INSERT INTO users (name, age) VALUES ('Dave', 40) RETURNING id;

UPDATE users SET age = 41 WHERE id = 4;

DELETE FROM users WHERE id = 4;

SELECT * FROM users ORDER BY id;
```

## Какой метод выбрать

| Метод | Возвращает | Когда использовать |
|---|---|---|
| `fetch` | список `Record` | выборка нескольких строк |
| `fetchrow` | один `Record` или `None` | одна строка: поиск по id, `INSERT ... RETURNING *` |
| `fetchval` | одно значение | `count(*)`, `INSERT ... RETURNING id` |
| `execute` | строка статуса (`'UPDATE 3'`) | `INSERT`/`UPDATE`/`DELETE` без результата, DDL |

## Связанные темы

- [Запросы к PostgreSQL](query.md)
- [Транзакции](transaction.md)
- [Практические задачи по PostgreSQL](tasks.md)
- [Быстрая загрузка данных](bulk_load.md)
