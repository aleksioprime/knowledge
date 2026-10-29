# Проектирование схемы

Сервис только начинается, ORM и миграций ещё нет, а таблицы под задачи и метки нужны уже сейчас. Их заводят одним SQL-скриптом, который лежит в репозитории рядом с кодом. Пока скрипт пишется, приходится принять десяток мелких решений: в какую схему класть таблицы, какой будет первичный ключ, как хранить время и строки, ставить ли внешние ключи и какие индексы нужны таблице связи. Каждое из них потом дорого менять, поэтому их стоит принять осознанно.

Примеры проверены на PostgreSQL 16.

## Минимальный пример

Файл `schema.ddl` для «Задачника»: пользователи, задачи, метки и связь задача–метка.

```sql
CREATE SCHEMA IF NOT EXISTS content;

CREATE TABLE IF NOT EXISTS content.app_user (
    id       bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email    text NOT NULL UNIQUE,
    created  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS content.task (
    id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title     text NOT NULL CHECK (length(title) BETWEEN 1 AND 200),
    done      boolean NOT NULL DEFAULT false,
    due_date  date,
    owner_id  bigint NOT NULL REFERENCES content.app_user (id) ON DELETE CASCADE,
    created   timestamptz NOT NULL DEFAULT now(),
    modified  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS content.tag (
    id    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name  text NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS content.task_tag (
    id       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id  uuid NOT NULL REFERENCES content.task (id) ON DELETE CASCADE,
    tag_id   uuid NOT NULL REFERENCES content.tag (id) ON DELETE CASCADE,
    created  timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS task_tag_task_tag_idx ON content.task_tag (task_id, tag_id);
CREATE INDEX IF NOT EXISTS task_tag_tag_idx ON content.task_tag (tag_id);
CREATE INDEX IF NOT EXISTS task_owner_idx ON content.task (owner_id);

CREATE OR REPLACE FUNCTION content.set_modified() RETURNS trigger AS $$
BEGIN
    NEW.modified := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER task_set_modified
BEFORE UPDATE ON content.task
FOR EACH ROW EXECUTE FUNCTION content.set_modified();
```

```bash
psql -U app -d tasks -v ON_ERROR_STOP=1 -f schema.ddl
```

Таблица пользователей называется `app_user`, а не `user`: `user` — зарезервированное слово, и без кавычек такую таблицу не создать.

Проверим, что всё связано:

```sql
SET search_path TO content;

INSERT INTO app_user (email) VALUES ('anna@example.com');
INSERT INTO tag (name) VALUES ('работа'), ('срочно');
INSERT INTO task (title, owner_id) VALUES ('Сдать отчёт', 1);
INSERT INTO task_tag (task_id, tag_id)
SELECT t.id, g.id FROM task t, tag g WHERE t.title = 'Сдать отчёт';

SELECT t.title, string_agg(g.name, ', ' ORDER BY g.name) AS tags
FROM task t
JOIN task_tag tt ON tt.task_id = t.id
JOIN tag g ON g.id = tt.tag_id
GROUP BY t.title;
--     title    |      tags
-- -------------+----------------
--  Сдать отчёт | работа, срочно
```

## Схемы

**Схема** (schema) — папка для таблиц внутри одной базы. Таблица `content.task` лежит в схеме `content`, и рядом может спокойно существовать `public.task` или `audit.task`.

Зачем раскладывать таблицы по схемам:

- **Отделить своё от чужого.** Django, Celery, Airflow создают служебные таблицы (`django_migrations`, `auth_user`, `celery_taskmeta`). Если таблицы бизнес-логики лежат в `content`, а служебные остаются в `public`, при беглом `\dt content.*` видно только то, что относится к предметной области.
- **Раздавать права целиком.** Аналитику можно разрешить читать всё в одной схеме и не дать ему доступа к остальному:

  ```sql
  CREATE ROLE analyst LOGIN PASSWORD 'analyst';
  GRANT USAGE ON SCHEMA content TO analyst;
  GRANT SELECT ON ALL TABLES IN SCHEMA content TO analyst;
  ```

  Под этой ролью `SELECT count(*) FROM content.tag` работает, а `DELETE FROM content.tag` и чтение таблицы из `public` дают `permission denied`. `ON ALL TABLES` касается только уже существующих таблиц; для будущих есть `ALTER DEFAULT PRIVILEGES`.
- **Одинаковые имена.** `content.task` и `archive.task` не конфликтуют.

Если схему не указать, таблица создаётся в **`public`** — она есть в каждой новой базе.

### search_path

Писать `content.` перед каждой таблицей утомительно. Какую схему подставить, если она не указана, решает **`search_path`** — список схем, которые PostgreSQL просматривает по порядку:

```sql
SHOW search_path;          -- "$user", public
SELECT count(*) FROM task; -- ERROR:  relation "task" does not exist

SET search_path TO content, public;
SELECT count(*) FROM task; -- 0, нашлась content.task
```

`"$user"` в начале означает схему с именем текущей роли, если такая существует. Если одна и та же таблица есть в нескольких схемах, берётся первая по списку: при `content, public` запрос к `task` идёт в `content.task`, даже если существует `public.task`.

Где задавать путь:

| Где | Как | Действует |
|---|---|---|
| В сессии | `SET search_path TO content, public;` | до конца соединения |
| Для роли | `ALTER ROLE app SET search_path TO content, public;` | для всех **новых** соединений этой роли |
| В строке подключения psycopg | `psycopg.connect(dsn, options='-c search_path=content')` | для этого соединения |

```python
import psycopg

with psycopg.connect('postgresql://app:app@localhost:5432/tasks', options='-c search_path=content') as conn:
    print(conn.execute('SHOW search_path').fetchone())  # ('content',)
```

В DDL-скриптах и миграциях надёжнее писать имя схемы явно (`content.task`): скрипт не зависит от того, с какими настройками его запустят.

## Первичный ключ

Два основных варианта — число из последовательности и UUID.

**Число.** Современная запись — `bigint GENERATED ALWAYS AS IDENTITY`. Старая — `bigserial`: под капотом то же самое (последовательность и `DEFAULT nextval(...)`), но identity строже. При `GENERATED ALWAYS` случайно вставить свой `id` не получится:

```sql
INSERT INTO app_user (id, email) VALUES (10, 'boris@example.com');
-- ERROR:  cannot insert a non-DEFAULT value into column "id"
-- HINT:  Use OVERRIDING SYSTEM VALUE to override.
```

А с `bigserial` такая вставка проходит молча, последовательность об этом не знает, и через какое-то время обычный `INSERT` падает на `duplicate key value violates unique constraint`. Если свои id всё же нужны (перенос данных), есть `OVERRIDING SYSTEM VALUE`, после которого последовательность сдвигают вручную через `setval`. Берите `bigint`, а не `int`: переполнить 2,1 миллиарда реально, а менять тип ключа в большой таблице больно.

**UUID** — 128-битный случайный идентификатор. С PostgreSQL 13 функция `gen_random_uuid()` встроена, расширение не нужно.

UUID выбирают, когда:

- id нужен **до вставки**: приложение создаёт задачу и сразу кладёт её id в сообщение для очереди, не дожидаясь ответа базы;
- записи создаются **в разных местах** (несколько баз, офлайн-клиенты) и потом сливаются — UUID не пересекутся, а числа из разных последовательностей пересекутся сразу;
- не хочется, чтобы id в URL выдавал количество записей и позволял перебрать соседние.

Минусы UUID:

- **Размер**: 16 байт против 8 у `bigint`. Он повторяется в каждом внешнем ключе и индексе. Хранить UUID в `text` ещё хуже — 40 байт: `pg_column_size(gen_random_uuid()::text)`.
- **Случайная вставка в B-tree.** Числа растут, и новая запись всегда дописывается в правый край индекса. Случайный UUID попадает в произвольную страницу, страницы делятся и заполнены наполовину.

Замер на моей машине, миллион строк, только первичный ключ:

| Ключ | Вставка (с генерацией ключа) | Таблица | Индекс PK |
|---|---:|---:|---:|
| `bigint identity` | 1,4 с | 35 MB | 21 MB |
| `uuid` (`gen_random_uuid()`) | 4,0 с | 42 MB | 38 MB |

Проблему случайной вставки решает **UUID версии 7**: первые 48 бит в нём — время, поэтому новые значения идут почти по порядку, как числа. В PostgreSQL 18 появилась функция `uuidv7()`, в Python 3.14 — `uuid.uuid7()`; на более старых версиях значение генерируют в приложении библиотекой.

Практическое правило: внутренний справочник или таблица без внешних потребителей — `bigint identity`; сущность, id которой уходит наружу или рождается вне базы, — `uuid` (лучше v7).

## Время

| Тип | Что хранит | Когда подходит |
|---|---|---|
| `timestamptz` | момент времени, внутри — UTC | почти всегда |
| `timestamp` | «дата и время на часах», без пояса | расписание «каждый день в 9:00 по местному» |
| `bigint` с unix-временем | секунды с 1970 года | обмен с системами, где так принято |

Название `timestamptz` (timestamp with time zone) обманчиво: пояс в колонке **не хранится**. При записи значение переводится в UTC, при чтении — в пояс текущей сессии. Обе колонки занимают по 8 байт.

```sql
SELECT '2026-11-01 09:00'::timestamp AS ts, '2026-11-01 09:00+03'::timestamptz AS tstz;
--          ts          |          tstz
-- ---------------------+------------------------
--  2026-11-01 09:00:00 | 2026-11-01 06:00:00+00

SET timezone = 'Asia/Vladivostok';
SELECT '2026-11-01 09:00+03'::timestamptz;  -- 2026-11-01 16:00:00+10, тот же момент
```

С `timestamp` непонятно, в каком поясе было записано «09:00» — это знает только код, который писал. Unix-время в `bigint` однозначно, но его неудобно читать глазами и нельзя использовать с функциями дат без преобразования (`to_timestamp(1793512800)`, `extract(epoch FROM ...)`). Рекомендация: `timestamptz`, а на сервере базы и в приложении — UTC.

Для дат без времени (срок задачи `due_date`) есть `date`.

## Строки

| Тип | Особенности |
|---|---|
| `text` | без ограничения длины |
| `varchar(n)` | то же самое, плюс проверка длины |
| `char(n)` | дополняет значение пробелами до `n`; почти никогда не нужен |

В PostgreSQL `text` и `varchar(n)` хранятся одинаково и одинаково быстры. Длина `n` — это просто встроенная проверка. Её проблема — в изменении. Увеличить `varchar(200)` до `varchar(300)` можно мгновенно, а вот уменьшение до `varchar(100)` переписывает всю таблицу под эксклюзивной блокировкой (видно по смене `pg_relation_filenode`) и падает, если хоть одна строка длиннее:

```sql
ALTER TABLE note ALTER COLUMN title TYPE varchar(100);
-- ERROR:  value too long for type character varying(100)
```

Поэтому часто берут `text`, а длину проверяют в приложении (в схеме Pydantic, в форме) или ограничением `CHECK`, как в `task.title` выше. Ограничение можно удалить и создать заново без перезаписи таблицы — новое лишь проверит существующие строки:

```sql
INSERT INTO content.task (title, owner_id) VALUES ('', 1);
-- ERROR:  new row for relation "task" violates check constraint "task_title_check"
```

## Внешние ключи

`owner_id bigint REFERENCES content.app_user (id)` — **внешний ключ** (foreign key): база не даст создать задачу несуществующего пользователя и не даст удалить пользователя, у которого есть задачи. `ON DELETE CASCADE` меняет второе правило: при удалении пользователя удаляются и его задачи, а вместе с задачами — их строки в `task_tag`:

```sql
DELETE FROM app_user WHERE email = 'anna@example.com';
SELECT (SELECT count(*) FROM task) AS tasks, (SELECT count(*) FROM task_tag) AS links;
--  tasks | links
-- -------+-------
--      0 |     0
```

Другие варианты — `ON DELETE RESTRICT` (по умолчанию, запретить), `ON DELETE SET NULL` (оставить задачу без владельца).

Иногда внешние ключи сознательно не ставят: данные приходят из разных источников в произвольном порядке, таблицы потом разносят по разным базам, важна скорость массовой загрузки. Это честный компромисс: без FK схема гибче, но целостность становится заботой приложения, и «висячие» ссылки на удалённые строки рано или поздно появятся. Для небольшого сервиса с одной базой внешние ключи почти всегда стоит оставить.

PostgreSQL **не создаёт индекс** на колонку внешнего ключа сам. Без индекса на `task.owner_id` каждое удаление пользователя проверяет задачи полным проходом по таблице. Поэтому в скрипте есть `task_owner_idx`.

## Таблица связи многие-ко-многим

У задачи много меток, у метки много задач. Связь хранят в отдельной таблице `task_tag` с двумя внешними ключами.

**Уникальный составной индекс `(task_id, tag_id)`** не даёт повесить одну метку на задачу дважды:

```sql
INSERT INTO task_tag (task_id, tag_id) SELECT task_id, tag_id FROM task_tag LIMIT 1;
-- ERROR:  duplicate key value violates unique constraint "task_tag_task_tag_idx"
```

Этот же индекс ускоряет поиск «метки задачи» — `task_id` стоит в нём первым, а B-tree умеет искать по префиксу составного ключа (подробнее — в [README](README.md#индексы)). Поэтому отдельный индекс на `task_id` не нужен. А вот для обратного вопроса «задачи с меткой» составной индекс не подходит, нужен свой индекс на `tag_id`. Проверка на 60 000 связей:

```text
-- WHERE task_id = ...
Bitmap Index Scan on task_tag_task_tag_idx
-- WHERE tag_id = ..., есть task_tag_tag_idx
Bitmap Index Scan on task_tag_tag_idx
-- WHERE tag_id = ..., индекс удалён
Seq Scan on task_tag
```

Индекс на `tag_id` нужен ещё и каскадному удалению: при `DELETE FROM tag` база ищет связи этой метки.

Отдельный `id` у строки связи не обязателен: можно объявить `PRIMARY KEY (task_id, tag_id)` — это и есть уникальный составной индекс. Суррогатный `id` оставляют, если фреймворк ждёт у каждой таблицы один столбец-ключ или на связь будут ссылаться другие таблицы.

## Поля created и modified

`created` и `modified` отвечают на вопросы «когда появилась» и «когда последний раз менялась». Ставить их лучше в базе, а не в приложении: у нескольких экземпляров приложения часы могут расходиться, а данные бывают изменены и не через приложение — скриптом, из `psql`, другим сервисом.

- `created` — `DEFAULT now()`, этого достаточно.
- `modified` — `DEFAULT now()` срабатывает только при вставке. При `UPDATE` его обновляет триггер `task_set_modified` из скрипта.

```sql
INSERT INTO task (title, owner_id) VALUES ('Сдать отчёт', 1);
-- через секунду
UPDATE task SET done = true WHERE title = 'Сдать отчёт' RETURNING created, modified;
--             created            |           modified
-- -------------------------------+-------------------------------
--  2026-10-28 20:59:07.629036+00 | 2026-10-28 20:59:08.635916+00
```

`now()` — это время **начала транзакции**: внутри одной транзакции все строки получат одинаковое значение. Если нужно реальное текущее время, есть `clock_timestamp()`.

ORM умеют ставить эти поля сами (`auto_now_add` и `auto_now` в Django), но делают это временем приложения и только для изменений через ORM.

## DDL-файл в репозитории

Скрипт `schema.ddl` хранится в репозитории и запускается так:

```bash
psql -U app -d tasks -v ON_ERROR_STOP=1 -f schema.ddl
```

`ON_ERROR_STOP=1` останавливает выполнение на первой ошибке; без него `psql` продолжит выполнять следующие команды и завершится с кодом 0.

Скрипт **идемпотентный**: его можно запускать повторно, и он не падает на уже созданных объектах. За это отвечают `IF NOT EXISTS` у схемы, таблиц и индексов и `CREATE OR REPLACE` у функции и триггера (`CREATE OR REPLACE TRIGGER` появился в PostgreSQL 14). При повторном запуске `psql` выводит `NOTICE: relation "task" already exists, skipping` и завершается успешно.

Важно, чего `IF NOT EXISTS` **не** делает: если таблица уже есть, но с другими колонками, скрипт её не изменит. Добавить колонку в существующую таблицу — это уже миграция, и как только схема начинает меняться, переходят на инструмент миграций (Alembic, миграции Django).

## Частые ошибки

- Таблицы создались не в той схеме → запрос падает с `relation "task" does not exist` или находит одноимённую таблицу из `public` → пишите схему явно в DDL, а `search_path` задавайте для роли или в строке подключения.
- `ALTER ROLE ... SET search_path` «не работает» → настройка применяется только к новым соединениям → переподключитесь.
- `int` в первичном ключе → через годы ключ переполняется → сразу `bigint`.
- `bigserial` и вставка своих id → позже обычная вставка падает на дубликате ключа → `GENERATED ALWAYS AS IDENTITY`, при переносе — `OVERRIDING SYSTEM VALUE` и `setval`.
- UUID в колонке `text` → ключ и индексы в 2,5 раза больше, сравнение строк медленнее → тип `uuid`.
- `timestamp` без пояса → одно и то же «09:00» значит разное у разных клиентов → `timestamptz`.
- Внешний ключ без индекса → удаление родительской строки медленно сканирует дочернюю таблицу → индекс на колонку FK.
- `psql -f` без `ON_ERROR_STOP` → половина скрипта упала, а CI зелёный → `-v ON_ERROR_STOP=1`.

## Когда не использовать

Ручной DDL-скрипт хорош в начале проекта и для учебных стендов. Как только схема начинает меняться, а базы есть у нескольких разработчиков и на нескольких стендах, нужны миграции: они хранят историю изменений и применяют только недостающие шаги. Если проект на Django или SQLAlchemy, таблицы обычно описывают моделями, а SQL генерирует инструмент миграций — но все решения из этой заметки (тип ключа, `timestamptz`, индексы таблицы связи) принимаются точно так же, просто записываются в модели.

## Связанные темы

- [PostgreSQL: индексы, транзакции, MVCC](README.md)
- [Быстрая загрузка данных](bulk_load.md)
- [Основы SQL: типы данных и ограничения](../sql/basics.md)
- [Транзакции и оптимизация](../sql/transactions_and_optimization.md)
- [Alembic](../alembic/README.md)
- [Django](../../frameworks/django/README.md)
