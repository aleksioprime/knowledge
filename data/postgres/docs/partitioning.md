# Партицирование таблиц

Каждый вход в «Задачник» записывается в таблицу истории входов: кто, когда, с какого устройства и IP, успешно или нет. Это нужно для раздела «Активные сеансы» и для разбора подозрительных входов. Таблица растёт на сотни тысяч строк в месяц, а хранить нужно только последние полгода. Удаление старых строк через `DELETE` на такой таблице — это долгий запрос, гигабайты журнала, работа для `VACUUM` и файл таблицы, который не уменьшается. Партицирование делит одну логическую таблицу на физические куски по месяцам, и «удалить январь» превращается в удаление одного файла.

Примеры проверены на PostgreSQL 16.15 в Docker на Apple M1, SQLAlchemy 2.1.6, Alembic 1.20.1 и psycopg 3.3.6.

## Минимальный пример

```sql
CREATE TABLE login_history (
    id bigint GENERATED ALWAYS AS IDENTITY,
    user_id bigint NOT NULL,
    logged_at timestamptz NOT NULL,
    ip inet,
    device text NOT NULL,
    success boolean NOT NULL,
    PRIMARY KEY (id, logged_at)
) PARTITION BY RANGE (logged_at);

CREATE TABLE login_history_2026_11 PARTITION OF login_history
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
CREATE TABLE login_history_2026_12 PARTITION OF login_history
    FOR VALUES FROM ('2026-12-01') TO ('2027-01-01');

CREATE INDEX ON login_history (user_id, logged_at);
```

Приложение работает только с `login_history` — вставляет и читает как из обычной таблицы. PostgreSQL сам кладёт строку в нужную партицию и при чтении заглядывает только в те партиции, где могут быть подходящие строки:

```sql
EXPLAIN (COSTS OFF)
SELECT device, count(*) FROM login_history
WHERE logged_at >= '2026-12-01' AND logged_at < '2027-01-01'
GROUP BY device;
```

```text
 HashAggregate
   Group Key: login_history.device
   ->  Seq Scan on login_history_2026_12 login_history
         Filter: ((logged_at >= '2026-12-01 00:00:00+00'::timestamp with time zone) AND ...)
```

Остальные партиции в плане даже не упоминаются. А старые данные удаляются так:

```sql
ALTER TABLE login_history DETACH PARTITION login_history_2026_01;
DROP TABLE login_history_2026_01;   -- 24 мс против 2,3 с у DELETE + VACUUM, замер ниже
```

## Как это работает

Родительская таблица (`PARTITION BY ...`) не хранит строк — у неё 0 байт. Это описание: какие колонки, по какому ключу делить и куда смотреть. Каждая партиция — обычная таблица со своим файлом, своими индексами и своей статистикой, плюс ограничение «сюда попадают только такие значения ключа».

Аналогия — архив документов по годам: вместо одного огромного шкафа — шкаф на каждый год. Найти документ за март 2026 — открыть один шкаф. Выбросить документы старше пяти лет — вынести шкаф целиком, не перебирая папки.

### Способы деления

**RANGE** — по диапазонам. Основной вариант для данных со временем: история, логи, события, платежи. Граница `FROM` включается, `TO` — нет, поэтому месяцы стыкуются без зазоров и пересечений.

**LIST** — по списку значений. Например, по типу устройства:

```sql
CREATE TABLE login_by_device (
    user_id bigint NOT NULL,
    logged_at timestamptz NOT NULL,
    device text NOT NULL
) PARTITION BY LIST (device);
CREATE TABLE login_by_device_mobile PARTITION OF login_by_device FOR VALUES IN ('ios', 'android');
CREATE TABLE login_by_device_web PARTITION OF login_by_device FOR VALUES IN ('web');

INSERT INTO login_by_device VALUES (3, now(), 'tv');
-- ERROR:  no partition of relation "login_by_device" found for row
-- DETAIL:  Partition key of the failing row contains (device) = (tv).
```

Подходит, когда значений мало и по ним действительно разделяется работа: регионы, арендаторы, статусы «активные/архивные».

**HASH** — по остатку от хэша. Строки распределяются примерно поровну:

```sql
CREATE TABLE login_by_user (user_id bigint NOT NULL, logged_at timestamptz NOT NULL)
    PARTITION BY HASH (user_id);
CREATE TABLE login_by_user_0 PARTITION OF login_by_user FOR VALUES WITH (MODULUS 4, REMAINDER 0);
-- ... и ещё три с REMAINDER 1, 2, 3
INSERT INTO login_by_user SELECT id, now() FROM generate_series(1, 10000) AS id;
SELECT tableoid::regclass, count(*) FROM login_by_user GROUP BY 1 ORDER BY 1;
```

```text
    tableoid     | count
-----------------+-------
 login_by_user_0 |  2489
 login_by_user_1 |  2527
 login_by_user_2 |  2530
 login_by_user_3 |  2454
```

Запрос `WHERE user_id = 42` пойдёт в одну партицию. Хэш-партиции не помогают удалять старые данные и нужны редко: когда огромную таблицу без естественного ключа времени хочется разбить на куски поменьше для `VACUUM` и параллельной работы.

Партиции можно делить дальше (партиция по месяцу, внутри — по устройству), но каждый уровень умножает число таблиц.

### DEFAULT-партиция

Без неё строка, для которой нет партиции, вызывает ошибку, как с `'tv'` выше. Для истории входов это значит: забыли создать партицию на следующий месяц — первого числа в полночь входы перестали записываться. `DEFAULT` принимает всё, что не попало в другие партиции:

```sql
CREATE TABLE login_history_default PARTITION OF login_history DEFAULT;
```

Но у неё есть ловушка. Строка за январь 2027 попала в `DEFAULT`, потому что партиции ещё нет. Теперь создать эту партицию нельзя:

```sql
INSERT INTO login_history (user_id, logged_at, device, success)
VALUES (42, '2027-01-05 10:00+00', 'web', true);

CREATE TABLE login_history_2027_01 PARTITION OF login_history
    FOR VALUES FROM ('2027-01-01') TO ('2027-02-01');
-- ERROR:  updated partition constraint for default partition "login_history_default" would be violated by some row
```

Строки нужно сначала перенести, в одной транзакции:

```sql
BEGIN;
CREATE TEMP TABLE moved ON COMMIT DROP AS
WITH d AS (
    DELETE FROM login_history_default
    WHERE logged_at >= '2027-01-01' AND logged_at < '2027-02-01'
    RETURNING *
)
SELECT * FROM d;
CREATE TABLE login_history_2027_01 PARTITION OF login_history
    FOR VALUES FROM ('2027-01-01') TO ('2027-02-01');
INSERT INTO login_history OVERRIDING SYSTEM VALUE SELECT * FROM moved;  -- сохранить старые id
COMMIT;
```

Кроме того, при создании новой партиции PostgreSQL проверяет всю `DEFAULT`-партицию. Если там миллионы строк, это долгий просмотр под блокировкой. Поэтому `DEFAULT` — страховка, а не место хранения: партиции создают заранее, а `DEFAULT` должна оставаться пустой. Непустая `DEFAULT` — повод для алерта.

## Отсечение партиций (partition pruning)

Планировщик сравнивает условие `WHERE` с границами партиций и выбрасывает те, где подходящих строк быть не может. Замеры ниже — на 5 млн строк за 2026 год (около 425 тысяч на месяц, по 28 МБ на партицию), рядом обычная таблица `login_history_plain` с теми же данными и индексами `(user_id, logged_at)` и `(logged_at)`. Параллельные воркеры отключены, чтобы планы было проще читать; время — разброс трёх прогонов с прогретым кэшем.

### Запрос за месяц

```sql
SELECT device, count(*) FROM login_history
WHERE logged_at >= '2026-12-01' AND logged_at < '2027-01-01'
GROUP BY device;
```

```text
-- партицированная
 HashAggregate (actual time=133.995..133.996 rows=3 loops=1)
   Buffers: shared hit=3548
   ->  Seq Scan on login_history_2026_12 login_history (actual time=0.024..67.265 rows=425737 loops=1)

-- обычная
 HashAggregate (actual time=118.990..118.991 rows=3 loops=1)
   Buffers: shared hit=4716
   ->  Index Scan using login_history_plain_logged_at_idx on login_history_plain (actual time=0.022..55.592 rows=425737 loops=1)
```

| Строки вставлены | Партицированная | Обычная |
|---|---|---|
| по порядку времени | 3 548 страниц, 80–230 мс | 4 716 страниц, 85–140 мс |
| вперемешку | 3 550 страниц, 160–620 мс | 43 254 страницы, 1,1–3,4 с |

Результат честный и, возможно, неожиданный: **если строки в обычной таблице лежат в порядке времени и есть индекс по времени, партицирование чтение почти не ускоряет**. Индекс находит диапазон, а нужные строки лежат рядом, на тех же ~3,5 тысячах страниц. Для истории входов так и бывает: строки дописываются в конец по мере поступления.

Вторая строка — те же 5 млн строк, но вставленные в случайном порядке времени (первый прогон замеров). Строки декабря разбросаны по всем 41 667 страницам, и индексу приходится читать почти всю таблицу. Партиция же физически содержит только декабрь, как бы ни вставлялись строки. Такое «перемешивание» в жизни случается: данные приходят с опозданием, строки обновляются, освободившееся после `DELETE` место заполняется новыми строками (это видно в замере удаления ниже).

Квартал (три партиции, 1,26 млн строк, строки по порядку) — то же самое: 10 521 страница и 300–480 мс против 13 973 страниц и 335–530 мс у обычной таблицы с упорядоченными строками.

### Отсечение во время выполнения

Если граница известна только при выполнении — параметр подготовленного запроса, `now()`, — партиции отсекаются при старте выполнения, и в плане появляется `Subplans Removed`:

```sql
PREPARE week(timestamptz) AS
SELECT count(*) FROM login_history WHERE logged_at >= $1 AND logged_at < $1 + interval '7 days';
SET plan_cache_mode = force_generic_plan;
EXPLAIN (ANALYZE, COSTS OFF) EXECUTE week('2026-12-01');
```

```text
 Aggregate (actual time=124.082..124.084 rows=1 loops=1)
   ->  Append (actual time=13.052..113.912 rows=96608 loops=1)
         Subplans Removed: 12
         ->  Index Only Scan using login_history_2026_12_pkey on login_history_2026_12 login_history_1 ...
```

### Когда отсечение не срабатывает

Условие должно быть на сам ключ партицирования, без функций над ним:

```sql
EXPLAIN (COSTS OFF) SELECT count(*) FROM login_history WHERE logged_at::date = '2026-12-05';
```

```text
 Aggregate
   ->  Append
         ->  Seq Scan on login_history_2026_01 login_history_1
               Filter: ((logged_at)::date = '2026-12-05'::date)
         ->  Seq Scan on login_history_2026_02 login_history_2
         ... все 13 партиций
```

Правильно — диапазоном: `logged_at >= '2026-12-05' AND logged_at < '2026-12-06'`.

А запрос вообще без ключа партицирования идёт во все партиции. «Последние 20 входов пользователя 42»:

```sql
SELECT * FROM login_history WHERE user_id = 42 ORDER BY logged_at DESC LIMIT 20;
```

```text
-- партицированная: Merge Append из 13 Index Scan, по одному на партицию
 Buffers: shared hit=72
 Planning Time: 3.902 ms
 Execution Time: 1.337 ms

-- обычная: один Index Scan
 Buffers: shared hit=23
 Planning Time: 0.323 ms
 Execution Time: 0.373 ms
```

Втрое больше страниц и в несколько раз дольше: 13 маленьких индексов вместо одного большого. На 13 партициях это миллисекунды, на сотнях партиций растёт и время планирования. Если такой запрос частый, добавляют в него ограничение по времени («за последние 90 дней») — тогда отсечение снова работает.

## Удаление старых данных: DETACH и DROP против DELETE

Удаляем январь (424 тысячи строк) из обычной таблицы и из партицированной. Объём журнала (WAL) — разница `pg_current_wal_lsn()` до и после:

| Операция | Время | WAL | Размер таблицы после |
|---|---|---|---|
| `DELETE ... WHERE logged_at < '2026-02-01'` | 859 мс | 50 МБ | 744 МБ — не изменился |
| `VACUUM` после `DELETE` | 1 447 мс | 23 МБ | 744 МБ — не изменился |
| `DETACH PARTITION` + `DROP TABLE` | 14 + 10 мс | 108 КБ | минус 57 МБ сразу |

`DELETE` не удаляет строки физически: он помечает каждую версию строки как удалённую и пишет об этом в журнал, а реплики проигрывают тот же журнал. Потом `VACUUM` проходит таблицу и все индексы, чтобы освободить место. Но и после этого файл не уменьшается — место лишь помечается свободным для новых строк. Вернуть его операционной системе может только `VACUUM FULL` или `pg_repack`, а `VACUUM FULL` блокирует таблицу целиком.

Освободившееся место действительно занимается: после вставки 425 тысяч строк за январь 2027 обычная таблица выросла всего на 21 МБ (744 → 765 МБ), потому что новые строки легли на страницы удалённого января — в начало файла. Корреляция порядка строк с `logged_at` в статистике (`pg_stats.correlation`) упала с почти 1 до 0,54. Это и есть то «перемешивание», которое со временем делает обычную таблицу хуже для запросов по диапазону.

`DROP TABLE` партиции просто удаляет её файлы. Здесь 424 тысячи строк, но на 40 миллионах время было бы тем же.

Тонкости:

- обычный `DETACH PARTITION` берёт на родительскую таблицу блокировку `ACCESS EXCLUSIVE`: на эти миллисекунды встают все запросы к `login_history`, и сам `DETACH` ждёт, пока закончатся уже идущие. Под нагрузкой используют `DETACH PARTITION ... CONCURRENTLY` (с PostgreSQL 14): он не блокирует чтение и запись, но не работает внутри транзакции и не работает, если у таблицы есть `DEFAULT`-партиция:

  ```text
  ERROR:  cannot detach partitions concurrently when a default partition exists
  ```

- отсоединённую партицию не обязательно удалять: её можно выгрузить в архив (`pg_dump -t login_history_2026_01`) или перенести в другое табличное пространство.

## Ключи и индексы

**Первичный ключ и уникальные индексы обязаны включать ключ партицирования.** Каждая партиция проверяет уникальность только у себя, и PostgreSQL гарантирует глобальную уникальность, только если одинаковые значения не могут оказаться в разных партициях:

```sql
CREATE TABLE bad (id bigint, logged_at timestamptz NOT NULL, PRIMARY KEY (id))
    PARTITION BY RANGE (logged_at);
-- ERROR:  unique constraint on partitioned table must include all partitioning columns
-- DETAIL:  PRIMARY KEY constraint on table "bad" lacks column "logged_at" which is part of the partition key.
```

Поэтому в примере ключ — `(id, logged_at)`. Глобальной уникальности одного `id` больше нет: формально две строки с одинаковым `id` и разным временем допустимы. На практике `id` из identity-последовательности и так не повторяется, но внешний ключ из другой таблицы теперь должен ссылаться на пару `(id, logged_at)`. Для истории входов это не проблема — на неё обычно никто не ссылается. Для таблиц, на которые много ссылок, это серьёзный аргумент против партицирования.

**Индекс на родительской таблице** создаётся на всех существующих партициях и автоматически — на новых. После `CALL create_login_partitions(4)` из следующего раздела у новой партиции сразу есть `login_history_2027_02_pkey` и `login_history_2027_02_user_id_logged_at_idx`. Индекс на каждую партицию отдельно и меньше: 30 МБ индексов на месяц против 418 МБ на всю обычную таблицу — свежие партиции целиком помещаются в память.

`CREATE INDEX CONCURRENTLY` на родителе не работает:

```text
ERROR:  cannot create index on partitioned table "login_history" concurrently
```

Обходной путь без блокировок: `CREATE INDEX ... ON ONLY login_history` (пустой «нерабочий» индекс на родителе), затем `CREATE INDEX CONCURRENTLY` на каждой партиции и `ALTER INDEX ... ATTACH PARTITION` каждого из них к родительскому индексу. Когда присоединены все, родительский индекс становится рабочим.

## Создание партиций заранее

Партиция на следующий месяц должна существовать до его начала. Процедура создаёт партиции от текущего месяца на `months_ahead` вперёд и пропускает существующие, поэтому её можно запускать хоть каждый день:

```sql
CREATE OR REPLACE PROCEDURE create_login_partitions(months_ahead int DEFAULT 3)
LANGUAGE plpgsql AS $$
DECLARE
    month date;
BEGIN
    FOR month IN
        SELECT generate_series(date_trunc('month', now())::date,
                               (date_trunc('month', now()) + make_interval(months => months_ahead))::date,
                               interval '1 month')
    LOOP
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS login_history_%s PARTITION OF login_history FOR VALUES FROM (%L) TO (%L)',
            to_char(month, 'YYYY_MM'), month, month + interval '1 month'
        );
    END LOOP;
END $$;

CALL create_login_partitions(3);
```

Запускают её по расписанию: cron на сервере (`psql -c 'CALL create_login_partitions(3)'`), расширение `pg_cron`, задача [Celery beat](../../../framework/celery/docs/retries_beat_canvas.md) или [Airflow](../../airflow/README.md). Удаление старых партиций — такая же задача рядом. Запас в несколько месяцев нужен, чтобы упавшая задача не успела привести к ошибкам вставки.

Граница `'2026-12-01'` для `timestamptz` переводится во время по часовому поясу сессии (в примерах — UTC, поэтому `2026-12-01 00:00:00+00`). Если задача запускается с другим `TimeZone`, границы новых партиций сдвинутся на несколько часов и не состыкуются со старыми. Указывайте пояс явно: `'2026-12-01 00:00+00'`.

Готовое решение — расширение **pg_partman**: создаёт партиции заранее, удаляет или отсоединяет старые по правилу хранения, переносит строки из `DEFAULT`. Ставится в собственную базу; в управляемых облачных PostgreSQL обычно есть в списке расширений.

## Из SQLAlchemy

`postgresql_partition_by` в `__table_args__` добавляет `PARTITION BY` к `CREATE TABLE`. Партиции SQLAlchemy не создаёт — их добавляют DDL-событием после создания таблицы:

```python
from datetime import date, datetime

from sqlalchemy import DDL, BigInteger, Identity, String, event
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class LoginHistory(Base):
    __tablename__ = 'login_event'
    __table_args__ = {'postgresql_partition_by': 'RANGE (logged_at)'}

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    logged_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    device: Mapped[str] = mapped_column(String(20))


def month_partition(table: str, month: date) -> DDL:
    end = date(month.year + month.month // 12, month.month % 12 + 1, 1)
    return DDL(
        f'CREATE TABLE IF NOT EXISTS {table}_{month:%Y_%m} PARTITION OF {table} '
        f"FOR VALUES FROM ('{month}') TO ('{end}')"
    )


for month in (date(2026, 11, 1), date(2026, 12, 1)):
    event.listen(LoginHistory.__table__, 'after_create', month_partition('login_event', month))
event.listen(LoginHistory.__table__, 'after_create',
             DDL('CREATE TABLE IF NOT EXISTS login_event_default PARTITION OF login_event DEFAULT'))
```

`Base.metadata.create_all(engine)` выполняет:

```sql
CREATE TABLE login_event (
	id BIGINT GENERATED BY DEFAULT AS IDENTITY,
	logged_at TIMESTAMP WITH TIME ZONE NOT NULL,
	user_id BIGINT NOT NULL,
	device VARCHAR(20) NOT NULL,
	PRIMARY KEY (id, logged_at)
)
 PARTITION BY RANGE (logged_at)

CREATE TABLE IF NOT EXISTS login_event_2026_11 PARTITION OF login_event FOR VALUES FROM ('2026-11-01') TO ('2026-12-01')
-- и так далее
```

Дальше ORM работает с моделью как обычно, строки расходятся по партициям:

```python
with Session(engine) as session:
    session.add_all([
        LoginHistory(user_id=42, logged_at=datetime.fromisoformat('2026-11-03T10:00+00:00'), device='web'),
        LoginHistory(user_id=42, logged_at=datetime.fromisoformat('2026-12-24T18:30+00:00'), device='ios'),
    ])
    session.commit()
    session.execute(text('SELECT tableoid::regclass, id FROM login_event ORDER BY id')).all()
    # [('login_event_2026_11', 1), ('login_event_2026_12', 2)]
```

Первичный ключ составной — `session.get(LoginHistory, (1, logged_at))`.

`create_all` годится для тестов. В рабочем проекте схема меняется миграциями: родительская таблица — через `op.create_table(..., postgresql_partition_by='RANGE (logged_at)')`, партиции — через `op.execute('CREATE TABLE ... PARTITION OF ...')`, а будущие партиции создаёт процедура по расписанию, а не миграции.

Главная ловушка — **автогенерация Alembic**. Партиции видны в базе как обычные таблицы, а в моделях их нет, и `alembic revision --autogenerate` предлагает их удалить:

```text
['remove_table login_event_2026_11', 'remove_table login_event_2026_12', 'remove_table login_event_default', ...]
```

Их нужно исключить в `env.py`:

```python
def include_name(name, type_, parent_names):
    return not (type_ == 'table' and name.startswith('login_event_'))


context.configure(connection=connection, target_metadata=target_metadata, include_name=include_name)
```

С этим фильтром в проверочном прогоне `compare_metadata` предложений удалить партиции не осталось. Как устроены миграции — в заметке [Django: миграции](../../../framework/django/docs/migrations.md) и в документации Alembic.

## Партицирование и шардирование

Партицирование делит таблицу на куски **внутри одного сервера PostgreSQL**: одна база, одни транзакции, `JOIN` и внешние ключи работают как обычно. Оно помогает управлять большой таблицей, но не добавляет ни процессоров, ни дисков.

[Шардирование](../../../design/docs/scaling.md#шардирование) делит данные **между разными серверами**, чтобы распределить нагрузку, которая не помещается в одну машину. Транзакции и `JOIN` между шардами становятся задачей приложения или промежуточного слоя (Citus, Vitess-подобные решения). Эти подходы совмещают: внутри каждого шарда таблица может быть партицирована по времени.

## Частые ошибки

- **Нет партиции на следующий месяц** и нет `DEFAULT` — в полночь первого числа вставки падают. Партиции создают заранее по расписанию, наличие следующей проверяют алертом.
- **Данные копятся в `DEFAULT`** — нужную партицию потом не создать без переноса строк, а каждое создание партиции сканирует `DEFAULT`.
- **Функция над ключом в условии** (`logged_at::date = ...`, `date_trunc(...)`) — отсечения нет, запрос идёт по всем партициям.
- **Частые запросы без ключа партицирования** — каждая партиция просматривается отдельно, станет медленнее, чем на обычной таблице.
- **Слишком мелкие партиции.** Партиция на каждый день при хранении пяти лет — почти 2000 таблиц: растёт время планирования, память на метаданные и число файлов. Ориентир — от сотен мегабайт до десятков гигабайт на партицию и не больше нескольких сотен партиций.
- **Ожидание, что `PRIMARY KEY (id)` останется** — придётся включить ключ партицирования, а внешние ключи на таблицу перестроить.
- **Автогенерация Alembic удаляет партиции** — нужен фильтр `include_name`.
- **Границы в разных часовых поясах** — партиции не стыкуются; задавайте границы с явным поясом.

## Когда не использовать

- Таблица на миллионы, а не на сотни миллионов строк, и старые данные не нужно регулярно удалять. Обычная таблица с правильным индексом справится не хуже — это видно по замерам чтения выше.
- Основные запросы не фильтруют по ключу партицирования — они станут медленнее.
- На таблицу ссылается много внешних ключей, и нужен уникальный `id` без ключа партицирования.
- Цель — выдержать нагрузку, которая не помещается в один сервер. Тогда нужны [реплики или шардирование](../../../design/docs/scaling.md), а партицирование этого не даст.

Хороший кандидат выглядит так: таблица большая и растёт, у данных есть естественный ключ времени, запросы почти всегда идут за период, а старые данные удаляются или архивируются целыми периодами. История входов, логи аудита, события, метрики — классические примеры.

## Связанные темы

- [Проектирование схемы](schema_design.md) — `timestamptz`, ключи, индексы
- [Быстрая загрузка данных](bulk_load.md) — `COPY` и индексы при большой загрузке
- [Масштабирование и шардирование](../../../design/docs/scaling.md)
- [Шпаргалка: индексы, EXPLAIN, MVCC и VACUUM](../README.md#шпаргалка-для-собеседований)
