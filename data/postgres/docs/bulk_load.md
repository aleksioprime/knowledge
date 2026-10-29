# Быстрая загрузка данных

Прототип «Задачника» жил на SQLite, и в нём накопилось сто тысяч задач. Теперь их нужно перенести в PostgreSQL. Самый очевидный скрипт — прочитать все строки и вставить их по одной — работает, но медленно: на моей машине полминуты на 100 000 строк, на десяти миллионах — почти час. Тот же перенос через `COPY` занимает меньше секунды. Разница не в языке и не в железе, а в том, сколько раз программа ходит в базу и сколько раз база фиксирует транзакцию.

Примеры проверены на Python 3.12, psycopg 3.3 и PostgreSQL 16 в Docker.

## Минимальный пример

Исходная таблица в SQLite:

```sql
CREATE TABLE task (
    id TEXT PRIMARY KEY,        -- uuid строкой
    title TEXT NOT NULL,
    done INTEGER NOT NULL,      -- 0/1, своего boolean в SQLite нет
    due_date TEXT,              -- '2026-01-29'
    created TEXT NOT NULL       -- '2026-01-01 00:01:00+00:00'
);
```

Целевая таблица в PostgreSQL (упрощённая версия из [проектирования схемы](schema_design.md)):

```sql
CREATE SCHEMA IF NOT EXISTS content;
CREATE TABLE IF NOT EXISTS content.task (
    id uuid PRIMARY KEY,
    title text NOT NULL,
    done boolean NOT NULL DEFAULT false,
    due_date date,
    created timestamptz NOT NULL DEFAULT now()
);
```

Скрипт переноса:

```python
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from dataclasses import astuple, dataclass, fields

import psycopg

SQLITE_PATH = 'tasks.sqlite'
PG_DSN = 'postgresql://app:app@localhost:5432/tasks'
BATCH_SIZE = 1000


@dataclass
class Task:
    id: str
    title: str
    done: bool
    due_date: str | None
    created: str

    def __post_init__(self):
        self.done = bool(self.done)  # в SQLite это 0/1


COLUMNS = ', '.join(f.name for f in fields(Task))


def read_tasks(path: str) -> Iterator[list[Task]]:
    with closing(sqlite3.connect(path)) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(f'SELECT {COLUMNS} FROM task')
        while rows := cursor.fetchmany(BATCH_SIZE):
            yield [Task(**row) for row in rows]


def load_tasks(pg: psycopg.Connection, batches: Iterator[list[Task]]) -> int:
    loaded = 0
    with pg.transaction(), pg.cursor() as cur:
        with cur.copy(f'COPY content.task ({COLUMNS}) FROM STDIN') as copy:
            for batch in batches:
                for task in batch:
                    copy.write_row(astuple(task))
                loaded += len(batch)
    return loaded


with psycopg.connect(PG_DSN, autocommit=True) as pg:
    print(load_tasks(pg, read_tasks(SQLITE_PATH)))  # 100000
    print(pg.execute('SELECT count(*), min(created), max(created) FROM content.task').fetchone())
    # (100000, datetime.datetime(2026, 1, 1, 0, 1, tzinfo=zoneinfo.ZoneInfo(key='Etc/UTC')), datetime.datetime(2026, 3, 11, 10, 40, ...))
```

Весь перенос — меньше секунды. Дальше разберём каждую часть.

## Чтение из SQLite пачками

**`fetchmany`, а не `fetchall`.** `fetchall()` загружает в память всю таблицу разом; на миллионах строк скрипт съест гигабайты или упадёт. `fetchmany(1000)` возвращает следующую тысячу строк, а пустой список означает конец. Генератор `read_tasks` отдаёт пачки по одной, и в памяти одновременно живёт только одна пачка.

**`row_factory = sqlite3.Row`.** По умолчанию строка — кортеж, и к полям обращаются по номеру. С `sqlite3.Row` строка ведёт себя и как кортеж, и как словарь:

```python
row = conn.execute('SELECT id, title, done, due_date, created FROM task LIMIT 1').fetchone()
print(row.keys())      # ['id', 'title', 'done', 'due_date', 'created']
print(row['title'])    # Задача 1
print(dict(row))       # {'id': '0863...', 'title': 'Задача 1', 'done': 1, ...}
```

Поэтому работает `Task(**row)`: ключи строки совпадают с полями dataclass.

**Закрытие соединения.** Частая ошибка — считать, что `with sqlite3.connect(...)` закрывает соединение. Он управляет **транзакцией**: при выходе делает `commit` (или `rollback` при исключении), а соединение остаётся открытым:

```python
with sqlite3.connect('tasks.sqlite') as conn:
    conn.execute('SELECT count(*) FROM task').fetchone()

print(conn.execute('SELECT 1').fetchone())  # (1,) — соединение всё ещё открыто
```

Закрывает соединение `contextlib.closing`: он вызывает `close()` при выходе из блока.

```python
with closing(sqlite3.connect('tasks.sqlite')) as conn:
    pass

conn.execute('SELECT 1')  # sqlite3.ProgrammingError: Cannot operate on a closed database.
```

Можно написать и свой контекстный менеджер через `@contextmanager` с `try/finally: conn.close()` — например, если при открытии нужно сразу выставить `row_factory`. У соединения psycopg, в отличие от sqlite3, `with` закрывает соединение.

## Строка как dataclass

Dataclass даёт строке имена полей и одно место для преобразований. Три функции из модуля `dataclasses` здесь особенно полезны:

```python
task = Task(**row)
print(task)          # Task(id='0863...', title='Задача 1', done=True, due_date='2026-01-29', created='2026-01-01 00:01:00+00:00')
print(asdict(task))  # {'id': '0863...', 'title': 'Задача 1', 'done': True, ...}
print(astuple(task)) # ('0863...', 'Задача 1', True, '2026-01-29', '2026-01-01 00:01:00+00:00')
print([f.name for f in fields(Task)])  # ['id', 'title', 'done', 'due_date', 'created']
```

`fields()` собирает список колонок для `SELECT`, `INSERT` и `COPY`, поэтому порядок колонок задан в одном месте — в описании класса. `astuple()` превращает объект в кортеж параметров в том же порядке.

`__post_init__` с `bool(self.done)` здесь не украшение. psycopg передаёт Python-`int` как целое число, а PostgreSQL не приводит его к `boolean` сам:

```text
DatatypeMismatch: column "done" is of type boolean but expression is of type smallint
```

Строки `'2026-01-29'` и `'2026-01-01 00:01:00+00:00'` PostgreSQL разбирает сам, переводить их в `date` и `datetime` не обязательно.

## Способы записи в PostgreSQL

Все варианты ниже пишут одни и те же строки: `INSERT` с параметрами `%s`.

```python
INSERT = f'INSERT INTO task ({COLUMNS}) VALUES (%s, %s, %s, %s, %s)'
```

**1. По одной строке в автокоммите.** Каждый `execute` — отдельная транзакция: запрос по сети, ответ, запись WAL на диск при `COMMIT`.

```python
pg.autocommit = True
for batch in read_tasks(SQLITE_PATH):
    for task in batch:
        pg.execute(INSERT, astuple(task))
```

**2. По одной строке в одной транзакции.** Запросов столько же, но фиксация на диск одна, в конце.

```python
with pg.transaction():
    for batch in read_tasks(SQLITE_PATH):
        for task in batch:
            pg.execute(INSERT, astuple(task))
```

**3. `executemany`.** Тот же `INSERT` для списка параметров. В psycopg 3 он отправляет запросы в режиме конвейера (pipeline): не ждёт ответа на каждый, поэтому задержка сети почти не складывается.

```python
with pg.transaction(), pg.cursor() as cur:
    for batch in read_tasks(SQLITE_PATH):
        cur.executemany(INSERT, [astuple(task) for task in batch])
```

**4. Многострочный `INSERT ... VALUES (...), (...)`.** Одна команда вставляет всю пачку — 1000 строк за один запрос.

```python
with pg.transaction(), pg.cursor() as cur:
    for batch in read_tasks(SQLITE_PATH):
        row = '(' + ', '.join(['%s'] * 5) + ')'
        params = [value for task in batch for value in astuple(task)]
        cur.execute(f'INSERT INTO task ({COLUMNS}) VALUES {", ".join([row] * len(batch))}', params)
```

У одного запроса есть предел — 65 535 параметров, поэтому пачку больше ~13 000 строк по 5 колонок так не вставить.

**5. `COPY ... FROM STDIN`.** Специальная команда массовой загрузки: данные идут сплошным потоком, без разбора отдельных `INSERT`. В psycopg 3 — `cursor.copy()` и `copy.write_row()`, как в минимальном примере.

### Замеры

100 000 строк из SQLite в пустую таблицу с первичным ключом, три прогона. Чтение из SQLite само по себе занимает 0,14 с.

| Способ | Время | Строк в секунду |
|---|---:|---:|
| По одной, автокоммит | 34–36 с | ~2 900 |
| По одной, одна транзакция | 18–19 с | ~5 500 |
| `executemany` | 2,2–2,6 с | ~42 000 |
| Многострочный `VALUES` по 1000 | 1,5 с | ~67 000 |
| `COPY` | 0,3–0,35 с | ~300 000 |

Цифры зависят от машины: здесь Apple M1, PostgreSQL в Docker, подключение через проброшенный порт. Именно поэтому построчная вставка так медленна — каждая из 100 000 команд платит за путь до контейнера и обратно. На сервере рядом с базой разрыв будет меньше, на удалённой базе — больше. Порядок способов от этого не меняется.

Что видно из таблицы:

- автокоммит против одной транзакции — это цена 100 000 фиксаций на диск;
- одна транзакция против `executemany` — цена 100 000 ожиданий ответа;
- `COPY` быстрее всего, потому что база не разбирает и не планирует отдельные команды.

## Повторный запуск: ON CONFLICT

Перенос редко проходит с первого раза. Если скрипт упал на середине или его запустили второй раз, обычный `INSERT` и `COPY` упадут на первом же дубликате первичного ключа. Вставку можно сделать терпимой к повторам:

```python
with pg.cursor() as cur:
    cur.execute(INSERT + ' ON CONFLICT (id) DO NOTHING', astuple(task))
    print(cur.rowcount)  # 0 — строка уже была, пропущена

    task.title = 'Задача 1 (исправлено)'
    cur.execute(INSERT + '''
        ON CONFLICT (id) DO UPDATE SET title = EXCLUDED.title, done = EXCLUDED.done
    ''', astuple(task))
    print(cur.rowcount)  # 1 — строка обновлена
```

`DO NOTHING` пропускает существующие строки, `DO UPDATE` обновляет их. `EXCLUDED` — строка, которую пытались вставить. Пример upsert-счётчика есть в [практических задачах](tasks.md), здесь — применение к переносу.

`ON CONFLICT` есть у `INSERT`, но не у `COPY`. Чтобы получить и скорость `COPY`, и терпимость к повторам, грузят во временную таблицу, а уже из неё переливают одним `INSERT ... SELECT`:

```python
def load_tasks_idempotent(pg: psycopg.Connection, batches: Iterator[list[Task]]) -> int:
    with pg.transaction(), pg.cursor() as cur:
        cur.execute('CREATE TEMP TABLE task_stage (LIKE content.task) ON COMMIT DROP')
        with cur.copy(f'COPY task_stage ({COLUMNS}) FROM STDIN') as copy:
            for batch in batches:
                for task in batch:
                    copy.write_row(astuple(task))
        cur.execute(f'''
            INSERT INTO content.task ({COLUMNS})
            SELECT {COLUMNS} FROM task_stage
            ON CONFLICT (id) DO UPDATE
            SET title = EXCLUDED.title, done = EXCLUDED.done, due_date = EXCLUDED.due_date
        ''')
        return cur.rowcount


with psycopg.connect(PG_DSN, autocommit=True) as pg:
    print(load_tasks_idempotent(pg, read_tasks(SQLITE_PATH)))  # 100000
    print(load_tasks_idempotent(pg, read_tasks(SQLITE_PATH)))  # 100000 — обновлены, не задвоены
    print(pg.execute('SELECT count(*) FROM content.task').fetchone())  # (100000,)
```

Каждый запуск занимает около секунды.

## Подготовленные запросы

`PREPARE` разбирает и планирует запрос один раз, `EXECUTE` выполняет его с новыми параметрами:

```sql
PREPARE add_task(uuid, text) AS INSERT INTO content.task (id, title) VALUES ($1, $2);
EXECUTE add_task(gen_random_uuid(), 'Через PREPARE');
DEALLOCATE add_task;
```

Вручную это делать почти не нужно. psycopg 3 сам готовит запрос, который на одном соединении выполнился `prepare_threshold` раз (по умолчанию 5):

```python
for _ in range(6):
    pg.execute('SELECT title FROM task WHERE id = %s', (task.id,))
print(pg.execute('SELECT name, statement FROM pg_prepared_statements').fetchall())
# [('_pg3_0', 'SELECT title FROM task WHERE id = $1')]
```

Для массовой загрузки это мелкая экономия: главное — число обращений к базе, а не стоимость разбора.

## Индексы при большой загрузке

Каждый индекс обновляется при каждой вставленной строке. Если загрузка большая, а таблица пока никому не нужна, индексы выгоднее удалить, загрузить данные и построить индексы заново: построить индекс по готовым данным дешевле, чем поддерживать его на каждой вставке.

Замер на миллионе строк через `COPY`, таблица с первичным ключом и тремя индексами (`title`, `created`, `due_date`), два прогона:

| Вариант | Время |
|---|---:|
| Индексы есть во время загрузки | 12,7–13,7 с |
| Загрузка без индексов + `CREATE INDEX` после | 6,2–6,8 с |

На 100 000 строк разница почти незаметна: 0,85 с против 0,78 с. Первичный ключ обычно оставляют: без него не поймать дубликаты.

Если таблицей уже пользуются, обычный `CREATE INDEX` заблокирует запись в неё на всё время построения. Для живой таблицы есть `CREATE INDEX CONCURRENTLY`: строится дольше, но не мешает работе. Выполнять его можно только вне транзакции, поэтому в psycopg нужен автокоммит:

```python
pg.execute('CREATE INDEX CONCURRENTLY task_created_idx ON task (created)')
# в транзакции: ActiveSqlTransaction: CREATE INDEX CONCURRENTLY cannot run inside a transaction block

pg.autocommit = True
pg.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS task_created_idx ON task (created)')
```

## \copy в psql

Если данные уже лежат в CSV, Python не нужен. Команда `\copy` в `psql` читает файл **на стороне клиента** и отправляет его серверу как `COPY ... FROM STDIN`:

```sql
\copy (SELECT id, title, done, due_date, created FROM content.task) TO 'tasks.csv' WITH (FORMAT csv, HEADER)
\copy content.task_copy FROM 'tasks.csv' WITH (FORMAT csv, HEADER)
-- COPY 2
```

SQL-команда `COPY content.task FROM '/path/tasks.csv'` без обратной косой черты читает файл **на сервере базы** и требует особых прав. С ноутбука почти всегда нужен `\copy`.

## Частые ошибки

- `fetchall()` на большой таблице → процесс съедает всю память → `fetchmany()` в цикле или перебор курсора.
- `with sqlite3.connect(...)` вместо закрытия → соединение остаётся открытым, пока жив объект, а в долгоживущем процессе соединения копятся → `contextlib.closing` или свой контекстный менеджер.
- Коммит после каждой строки (или автокоммит при построчной вставке) → в десятки раз медленнее → одна транзакция и пачки, а лучше `COPY`.
- `COPY` падает целиком на первом дубликате: `UniqueViolation ... CONTEXT: COPY task, line 1`, в таблицу не попадает ни одна строка из этого `COPY` → загрузка во временную таблицу и `INSERT ... SELECT ... ON CONFLICT`.
- `ON CONFLICT (title)` без уникального индекса на `title` → `there is no unique or exclusion constraint matching the ON CONFLICT specification` → конфликт определяется только уникальным индексом или ограничением, создайте его или укажите другие колонки.
- Время без часового пояса → строка `'2026-01-01 09:00:00'` в колонку `timestamptz` трактуется в поясе **сессии**: при `timezone = 'Europe/Moscow'` сохранится `06:00 UTC`, а при UTC — `09:00 UTC`, и одни и те же данные загрузятся по-разному → выгружайте время с поясом (`+00:00`) или задайте пояс сессии явно перед загрузкой.
- Целые 0/1 в колонку `boolean` → `column "done" is of type boolean but expression is of type smallint` → преобразуйте в `bool` в Python.
- Ошибка в середине транзакции и `rollback()` → откатывается всё, что было в незакоммиченной транзакции, в том числе уже загруженные данные → работайте с `autocommit=True` и явными блоками `with pg.transaction()`, тогда граница каждой транзакции видна в коде.

## Когда не использовать

Для пары сотен строк хватит обычного `executemany` — `COPY` и временные таблицы только усложнят код. Если перенос — одноразовая операция между двумя PostgreSQL, проще `pg_dump` и `pg_restore`. Для регулярных переносов между системами со своим расписанием, повторами и мониторингом нужен оркестратор (например, Airflow), а не скрипт.

## Связанные темы

- [Проектирование схемы](schema_design.md)
- [PostgreSQL: индексы, транзакции, MVCC](../README.md)
- [Практические задачи: upsert, CREATE INDEX CONCURRENTLY](tasks.md)
- [Транзакции и оптимизация](../../sql/docs/transactions-and-optimization.md)
- [dataclasses](../../../python/typing/dataclasses.md)
- [Django](../../../framework/django/README.md)
- [Elasticsearch](../../elasticsearch/README.md) — следующий шаг такого же переноса: из PostgreSQL в поисковый индекс
