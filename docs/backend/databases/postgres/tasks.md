# Практические задачи по PostgreSQL

Задачи, которые встречаются на собеседованиях и в работе. У каждой — условие, идея решения и код. Идею и решение спрятаны под спойлер: сначала попробуйте решить сами.

Данные — таблицы «Задачника»: пользователи и их задачи. Блоки с кнопкой «Запустить» выполняются прямо в браузере: перед каждым запуском поднимается чистая база PostgreSQL, а подготовка данных выполняется автоматически. Свой сервер нужен только для двух примеров с несколькими одновременными соединениями — как его поднять, описано в [README раздела](README.md).

## Подготовка данных

Шесть пользователей (среди них есть повторяющиеся email) и 100 000 задач у первых трёх. Этот блок молча выполняется перед каждым запуском задач ниже.

```sql run setup=tasks
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL
);

CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    done BOOLEAN NOT NULL DEFAULT false,
    priority INT NOT NULL DEFAULT 1,
    owner_id INT REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

INSERT INTO users (email) VALUES
    ('anna@example.com'), ('boris@example.com'), ('vera@example.com'),
    ('anna@example.com'), ('gleb@example.com'), ('boris@example.com');

-- 100 000 задач у первых трёх пользователей
INSERT INTO tasks (title, done, priority, owner_id, created_at)
SELECT 'Задача ' || n, n % 3 = 0, n % 5 + 1, n % 3 + 1,
       '2026-01-01'::timestamp + n * interval '1 minute'
FROM generate_series(1, 100000) AS n;

ANALYZE;

SELECT count(*) AS tasks FROM tasks;
```

## 1. Найти и удалить дубликаты

В `users` есть повторяющиеся email. Найдите их, а затем удалите дубликаты, оставив запись с наименьшим `id`.

::: details Идея
`GROUP BY` + `HAVING` находят повторы. Для удаления пронумеруем строки внутри каждой группы оконной функцией `ROW_NUMBER()` и удалим все, кроме первой.
:::

::: details Решение
Поиск повторов:

```sql run session=dedupe uses=tasks
SELECT email, count(*) AS copies, array_agg(id ORDER BY id) AS ids
FROM users
GROUP BY email
HAVING count(*) > 1;
```

Удаление:

```sql run session=dedupe uses=tasks
DELETE FROM users
WHERE id IN (
    SELECT id FROM (
        SELECT id, ROW_NUMBER() OVER (PARTITION BY email ORDER BY id) AS n
        FROM users
    ) numbered
    WHERE n > 1
);

SELECT id, email FROM users ORDER BY id;
```

Чтобы дубликаты не появились снова, добавьте ограничение уникальности. Создать его до удаления дубликатов не получится — PostgreSQL проверит существующие строки:

```sql run session=dedupe uses=tasks
ALTER TABLE users ADD CONSTRAINT users_email_key UNIQUE (email);
```
:::

## 2. Пользователи без задач

Найдите пользователей, у которых нет ни одной задачи.

::: details Идея
`NOT EXISTS` или `LEFT JOIN ... WHERE tasks.id IS NULL`. А вот `NOT IN` — ловушка: если в подзапросе встретится `NULL`, результат станет пустым.
:::

::: details Решение
```sql run session=dedupe uses=tasks
SELECT u.id, u.email
FROM users u
WHERE NOT EXISTS (SELECT 1 FROM tasks t WHERE t.owner_id = u.id);
```

Ловушка `NOT IN`: добавим задачу без владельца. Сравнение `5 <> NULL` даёт `NULL`, а не `true`, поэтому ни одна строка не проходит условие и результат пустой. Транзакция в конце откатывается, чтобы задача без владельца не мешала следующим примерам.

```sql run session=dedupe uses=tasks
BEGIN;

INSERT INTO tasks (title, owner_id) VALUES ('Ничья задача', NULL);

SELECT id, email FROM users WHERE id NOT IN (SELECT owner_id FROM tasks);

ROLLBACK;
```
:::

## 3. Последние две задачи каждого пользователя

Классическая задача «top-N в группе»: для каждого пользователя выведите две самые новые задачи.

::: details Идея
`ROW_NUMBER()` нумерует задачи внутри каждого пользователя от новых к старым, затем оставляем номера 1 и 2. Для «второй по величине» — то же самое с `n = 2`.
:::

::: details Решение
```sql run uses=tasks
SELECT owner_id, id, title, created_at
FROM (
    SELECT t.*, ROW_NUMBER() OVER (PARTITION BY owner_id ORDER BY created_at DESC) AS n
    FROM tasks t
) ranked
WHERE n <= 2
ORDER BY owner_id, n;
```
:::

## 4. Медленный поиск: прочитать план и добавить индекс

Запрос «задачи пользователя 2 с высоким приоритетом» выполняется долго. Выясните почему и ускорьте.

```sql
SELECT id, title FROM tasks WHERE owner_id = 2 AND priority = 5;
```

::: details Идея
`EXPLAIN ANALYZE` выполняет запрос и показывает план. `Seq Scan` — полный проход по таблице. Составной индекс по колонкам из `WHERE` превратит его в поиск по индексу.
:::

::: details Решение
План без индекса:

```sql run session=plan uses=tasks
EXPLAIN ANALYZE
SELECT id, title FROM tasks WHERE owner_id = 2 AND priority = 5;
```

Добавляем составной индекс и смотрим план снова:

```sql run session=plan uses=tasks
CREATE INDEX tasks_owner_priority_idx ON tasks (owner_id, priority);

EXPLAIN ANALYZE
SELECT id, title FROM tasks WHERE owner_id = 2 AND priority = 5;
```

Сравните `Execution Time` до и после. Вместо `Seq Scan` теперь `Bitmap Index Scan`: база по индексу собирает адреса нужных строк и читает только их. Порядок колонок в индексе важен: индекс `(owner_id, priority)` поможет и запросу только по `owner_id`, но не запросу только по `priority`.

На рабочей базе обычный `CREATE INDEX` блокирует запись в таблицу на всё время построения. Там используют `CREATE INDEX CONCURRENTLY` — он строится дольше, но не мешает работе. Выполнять его нужно вне транзакции.
:::

## 5. Пагинация: OFFSET против keyset

Список задач листают страницами по 20. На дальних страницах всё начинает тормозить. Почему и как это исправить?

::: details Идея
`OFFSET 90000` заставляет базу прочитать и выбросить 90 000 строк. Пагинация по ключу (keyset pagination) — «дай 20 задач после id 90000» — сразу идёт по индексу к нужному месту.
:::

::: details Решение
```sql run uses=tasks
EXPLAIN ANALYZE
SELECT id, title FROM tasks ORDER BY id LIMIT 20 OFFSET 90000;

EXPLAIN ANALYZE
SELECT id, title FROM tasks WHERE id > 90000 ORDER BY id LIMIT 20;
```

В первом плане индекс первичного ключа проходится на 90 020 строк (`rows=90020` у `Index Scan`), во втором — ровно на 20. Время отличается на порядки.

Минус keyset: нельзя перейти сразу на страницу 4500, только «следующая» и «предыдущая». Для бесконечной ленты и API это обычно подходит.
:::

## 6. Создать или обновить: upsert

Счётчик задач по дням: если запись за этот день есть — увеличить, если нет — создать.

::: details Идея
`INSERT ... ON CONFLICT DO UPDATE` делает это одним запросом. Вариант «сначала SELECT, потом INSERT или UPDATE» ломается, когда два запроса приходят одновременно: оба не находят запись и оба пытаются её создать.
:::

::: details Решение
Выполним один и тот же upsert три раза: первый создаёт строку, два других увеличивают счётчик.

```sql run
CREATE TABLE counters (day DATE PRIMARY KEY, created INT NOT NULL);

INSERT INTO counters (day, created) VALUES ('2026-11-01', 1)
ON CONFLICT (day) DO UPDATE SET created = counters.created + 1;

INSERT INTO counters (day, created) VALUES ('2026-11-01', 1)
ON CONFLICT (day) DO UPDATE SET created = counters.created + 1;

INSERT INTO counters (day, created) VALUES ('2026-11-01', 1)
ON CONFLICT (day) DO UPDATE SET created = counters.created + 1;

SELECT * FROM counters;
```
:::

## 7. Потерянные обновления

Два процесса одновременно увеличивают один и тот же счётчик по 100 раз. Почему в итоге не 200?

::: details Идея
«Прочитать → прибавить в Python → записать» не атомарно: оба процесса читают одно и то же значение, и одно из увеличений теряется (lost update). Решение — считать прямо в базе (`SET n = n + 1`) или блокировать строку на время чтения (`SELECT ... FOR UPDATE`).
:::

::::: details Решение
::: warning Этот пример запускайте локально
Гонка возникает только между двумя одновременными соединениями, а в браузере база одна.
:::

```python
import asyncio

import asyncpg

DB_DSN = 'postgresql://postgres:postgres@localhost:5432/test_db'


async def unsafe_worker():
    conn = await asyncpg.connect(DB_DSN)
    for _ in range(100):
        value = await conn.fetchval("SELECT created FROM counters WHERE day = '2026-11-01'")
        await asyncio.sleep(0)  # в это время успевает поработать второй процесс
        await conn.execute("UPDATE counters SET created = $1 WHERE day = '2026-11-01'", value + 1)
    await conn.close()


async def safe_worker():
    conn = await asyncpg.connect(DB_DSN)
    for _ in range(100):
        await conn.execute("UPDATE counters SET created = created + 1 WHERE day = '2026-11-01'")
        await asyncio.sleep(0)
    await conn.close()


async def main():
    conn = await asyncpg.connect(DB_DSN)
    for worker in (unsafe_worker, safe_worker):
        await conn.execute('UPDATE counters SET created = 0')
        await asyncio.gather(worker(), worker())
        print(worker.__name__, await conn.fetchval('SELECT created FROM counters'))
    await conn.close()


asyncio.run(main())
```

```text
unsafe_worker 100
safe_worker 200
```

Оба безопасных варианта в одном соединении выглядят так. Здесь гонки нет, но это именно те запросы, которые её устраняют:

```sql run
CREATE TABLE counters (day DATE PRIMARY KEY, created INT NOT NULL);
INSERT INTO counters VALUES ('2026-11-01', 0);

-- Вариант 1: считаем в базе, чтение и запись — одна операция
UPDATE counters SET created = created + 1 WHERE day = '2026-11-01';

-- Вариант 2: блокируем строку до конца транзакции;
-- второй процесс на таком же SELECT ... FOR UPDATE будет ждать COMMIT
BEGIN;
SELECT created FROM counters WHERE day = '2026-11-01' FOR UPDATE;
UPDATE counters SET created = 2 WHERE day = '2026-11-01';  -- значение, посчитанное в приложении
COMMIT;

SELECT * FROM counters;
```
:::::

## 8. Очередь задач на таблице

Несколько воркеров берут задания из таблицы `jobs`. Нужно, чтобы одно задание не взяли двое и чтобы воркеры не ждали друг друга.

::: details Идея
`FOR UPDATE` блокирует выбранную строку до конца транзакции, а `SKIP LOCKED` пропускает строки, уже заблокированные другими. Каждый воркер получает своё задание без ожидания.
:::

::::: details Решение
Запрос воркера удобно записать одним `UPDATE ... RETURNING`: подзапрос выбирает первое свободное незаблокированное задание, `UPDATE` помечает его, `RETURNING` возвращает воркеру. Здесь три воркера берут задания по очереди в одном соединении — видно, что каждый получает следующее свободное. Параллельность, ради которой нужен `SKIP LOCKED`, видна только при запуске на своём сервере (пример ниже).

```sql run
CREATE TABLE jobs (id SERIAL PRIMARY KEY, payload TEXT, taken_by TEXT);
INSERT INTO jobs (payload) SELECT 'письмо ' || n FROM generate_series(1, 5) AS n;

UPDATE jobs SET taken_by = 'воркер A'
WHERE id = (
    SELECT id FROM jobs
    WHERE taken_by IS NULL
    ORDER BY id
    LIMIT 1
    FOR UPDATE SKIP LOCKED
)
RETURNING id, payload, taken_by;

UPDATE jobs SET taken_by = 'воркер B'
WHERE id = (
    SELECT id FROM jobs WHERE taken_by IS NULL ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED
)
RETURNING id, payload, taken_by;

UPDATE jobs SET taken_by = 'воркер C'
WHERE id = (
    SELECT id FROM jobs WHERE taken_by IS NULL ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED
)
RETURNING id, payload, taken_by;

SELECT * FROM jobs ORDER BY id;
```

::: warning Этот пример запускайте локально
Нужны три одновременных соединения, а в браузере база одна.
:::

Три воркера одновременно открывают транзакции и «обрабатывают» задание, держа строку заблокированной:

```python
import asyncio

import asyncpg

DB_DSN = 'postgresql://postgres:postgres@localhost:5432/test_db'


async def worker(name):
    conn = await asyncpg.connect(DB_DSN)
    async with conn.transaction():
        job = await conn.fetchrow('''
            SELECT id, payload FROM jobs
            WHERE taken_by IS NULL
            ORDER BY id
            LIMIT 1
            FOR UPDATE SKIP LOCKED
        ''')
        await asyncio.sleep(0.1)  # «обрабатываем» задание, строка заблокирована
        await conn.execute('UPDATE jobs SET taken_by = $1 WHERE id = $2', name, job['id'])
    await conn.close()
    return name, dict(job)


async def main():
    conn = await asyncpg.connect(DB_DSN)
    await conn.execute('''
        DROP TABLE IF EXISTS jobs;
        CREATE TABLE jobs (id SERIAL PRIMARY KEY, payload TEXT, taken_by TEXT);
        INSERT INTO jobs (payload) SELECT 'письмо ' || n FROM generate_series(1, 5) n;
    ''')
    await conn.close()
    for result in await asyncio.gather(worker('воркер A'), worker('воркер B'), worker('воркер C')):
        print(result)


asyncio.run(main())
```

```text
('воркер A', {'id': 1, 'payload': 'письмо 1'})
('воркер B', {'id': 2, 'payload': 'письмо 2'})
('воркер C', {'id': 3, 'payload': 'письмо 3'})
```

Без `SKIP LOCKED` второй и третий воркеры ждали бы, пока первый завершит транзакцию, и только потом получали бы свои задания — то есть работали бы последовательно.
:::::

## 9. Изменить тип колонки в нагруженной таблице

В огромной таблице постоянно идут чтение и запись, и нужно изменить тип колонки, не останавливая приложение. План такой: создать новую колонку, писать в обе колонки, читая из старой, перенести старые данные в новую, переключить чтение на новую колонку и удалить старую.

Пример: `priority INT` нужно превратить в `priority_level TEXT` (`high` для приоритетов 4–5, иначе `normal`).

::: details Идея
Подход «расширить → перенести → сузить» (expand → migrate → contract): схему меняют маленькими шагами, каждый из которых не блокирует таблицу надолго и совместим с работающим приложением.

1. **Добавить** новую колонку без `NOT NULL` и значения по умолчанию — это мгновенная операция.
2. **Писать в обе колонки.** Проще всего — триггером в базе, тогда старый код приложения менять не нужно.
3. **Перенести старые данные** пачками, чтобы не держать долгих блокировок.
4. **Переключить чтение** в приложении на новую колонку.
5. **Удалить** триггер и старую колонку.
:::

::: details Решение
Шаги 1 и 2: новая колонка и триггер, который заполняет её при каждой вставке и изменении приоритета.

```sql run session=retype uses=tasks
ALTER TABLE tasks ADD COLUMN priority_level TEXT;

CREATE FUNCTION sync_priority_level() RETURNS trigger AS $$
BEGIN
    NEW.priority_level := CASE WHEN NEW.priority >= 4 THEN 'high' ELSE 'normal' END;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tasks_sync_priority_level
BEFORE INSERT OR UPDATE OF priority ON tasks
FOR EACH ROW EXECUTE FUNCTION sync_priority_level();

INSERT INTO tasks (title, priority, owner_id) VALUES ('Новая срочная', 5, 1);

SELECT title, priority, priority_level FROM tasks WHERE title = 'Новая срочная';
```

Шаг 3: переносим старые строки пачками по 10 000, пока не останется незаполненных. Здесь цикл написан на PL/pgSQL; в рабочей миграции каждую пачку выполняют отдельной транзакцией (из скрипта или процедурой с `COMMIT` после каждой пачки), чтобы блокировки держались недолго.

```sql run session=retype uses=tasks
DO $$
DECLARE
    batches INT := 0;
    updated INT;
BEGIN
    LOOP
        UPDATE tasks
        SET priority_level = CASE WHEN priority >= 4 THEN 'high' ELSE 'normal' END
        WHERE id IN (SELECT id FROM tasks WHERE priority_level IS NULL LIMIT 10000);
        GET DIAGNOSTICS updated = ROW_COUNT;
        EXIT WHEN updated = 0;
        batches := batches + 1;
    END LOOP;
    RAISE NOTICE 'пачек: %', batches;
END;
$$;

SELECT priority_level, count(*) FROM tasks GROUP BY priority_level ORDER BY 1;
```

Шаг 4 выполняется в коде приложения: читаем `priority_level` вместо `priority`.

Шаг 5: убираем триггер и старую колонку, запрещаем `NULL` в новой.

```sql run session=retype uses=tasks
DROP TRIGGER tasks_sync_priority_level ON tasks;
DROP FUNCTION sync_priority_level();

ALTER TABLE tasks ALTER COLUMN priority_level SET NOT NULL;
ALTER TABLE tasks DROP COLUMN priority;

SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'tasks' AND column_name LIKE 'priority%';
```

`SET NOT NULL` проверяет всю таблицу под блокировкой. На очень большой таблице сначала добавляют ограничение `CHECK (priority_level IS NOT NULL) NOT VALID`, затем выполняют `VALIDATE CONSTRAINT` (без долгой блокировки) и только потом `SET NOT NULL` — PostgreSQL 12+ использует проверенное ограничение и не сканирует таблицу повторно:

```sql
ALTER TABLE tasks ADD CONSTRAINT tasks_priority_level_not_null
    CHECK (priority_level IS NOT NULL) NOT VALID;
ALTER TABLE tasks VALIDATE CONSTRAINT tasks_priority_level_not_null;
ALTER TABLE tasks ALTER COLUMN priority_level SET NOT NULL;
ALTER TABLE tasks DROP CONSTRAINT tasks_priority_level_not_null;
```
:::

## Связанные темы

- [Запросы к PostgreSQL](query.md)
- [Транзакции](transaction.md)
- [Подключение из Python через asyncpg](connect.md)
- [Проектирование схемы](schema_design.md)
