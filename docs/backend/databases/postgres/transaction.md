# Транзакции, изоляция и блокировки в PostgreSQL

Перевод денег между счетами — это два запроса: списать с одного счёта и зачислить на другой. Если между ними упадёт приложение или сеть, деньги исчезнут. Нужно, чтобы оба изменения применились вместе или не применились вовсе, и чтобы параллельные переводы не мешали друг другу. Эти задачи решают транзакции.

## Транзакция

Транзакция (transaction) — набор операций с базой, объединённых в одну атомарную единицу: либо фиксируются все изменения (`COMMIT`), либо ни одного (`ROLLBACK`).

Без явного `BEGIN` PostgreSQL работает в режиме автофиксации (autocommit): каждый запрос — отдельная транзакция, которая фиксируется сразу после выполнения.

Таблица для примеров:

```sql run session=items
CREATE TABLE items (
    id    serial PRIMARY KEY,
    name  text    NOT NULL,
    price numeric NOT NULL
);

INSERT INTO items (name, price)
SELECT 'Item ' || i, i * 10
FROM generate_series(1, 3) AS i;

SELECT * FROM items ORDER BY id;
```

Несколько изменений в одной транзакции. Внутри транзакции свои изменения видны сразу, остальным сессиям — только после `COMMIT`:

```sql run session=items
BEGIN;
INSERT INTO items (name, price) VALUES ('Transactional Item 1', 150);
UPDATE items SET price = price + 10 WHERE name = 'Item 2';
DELETE FROM items WHERE name = 'Item 3';
COMMIT;

SELECT * FROM items ORDER BY id;
```

Новая строка получила `id = 4`: значения последовательности (sequence) не откатываются и не переиспользуются, поэтому в `serial`-столбцах бывают пропуски.

`ROLLBACK` отменяет всё, что сделано после `BEGIN`:

```sql run session=items
BEGIN;
DELETE FROM items;
SELECT count(*) AS inside_tx FROM items;
ROLLBACK;

SELECT count(*) AS after_rollback FROM items;
```

Из приложения то же самое делают через драйвер. В asyncpg транзакция — объект соединения: при выходе из блока `async with` без исключения выполняется `COMMIT`, при исключении — `ROLLBACK`.

```python
import asyncpg

conn = await asyncpg.connect('postgresql://postgres:postgres@localhost:5432/test_db')
try:
    async with conn.transaction():
        await conn.execute(
            'INSERT INTO items (name, price) VALUES ($1, $2)', 'Transactional Item 1', 150
        )
        await conn.execute('UPDATE items SET price = price + 10 WHERE name = $1', 'Item 2')
        await conn.execute('DELETE FROM items WHERE name = $1', 'Item 3')
finally:
    await conn.close()
```

Ручной вариант — `tx = conn.transaction()`, затем `await tx.start()`, `await tx.commit()` или `await tx.rollback()` в `except`.

### Незавершённые транзакции

Транзакция, которую не зафиксировали и не откатили, продолжает держать блокировки и мешает очистке старых версий строк (см. [MVCC](#mvcc)): таблицы разрастаются, другие запросы ждут. Сессию, которая слишком долго простаивает внутри транзакции, PostgreSQL может закрыть сам — для этого задают `idle_in_transaction_session_timeout` (по умолчанию выключено). При обрыве соединения незавершённая транзакция откатывается.

### Точки сохранения

Точка сохранения (SAVEPOINT) позволяет откатить часть транзакции, не теряя то, что было сделано до неё:

```sql run session=items
BEGIN;
UPDATE items SET price = 100 WHERE name = 'Item 1';
SAVEPOINT before_delete;
DELETE FROM items WHERE name = 'Item 2';
SELECT name, price FROM items ORDER BY id;   -- Item 2 удалён
ROLLBACK TO SAVEPOINT before_delete;
COMMIT;

SELECT name, price FROM items ORDER BY id;   -- Item 2 на месте, цена Item 1 изменена
```

Если запрос внутри транзакции падает с ошибкой, вся транзакция переходит в состояние «прервана»: следующие команды отклоняются (`current transaction is aborted`), а `COMMIT` превращается в `ROLLBACK`. Продолжить работу можно, только откатившись к точке сохранения, созданной до ошибки. Так, например, работают вложенные `async with conn.transaction()` в asyncpg.

## ACID

ACID — четыре требования, которые транзакционная СУБД выполняет ради сохранности данных:

- **Атомарность** (Atomicity) — транзакция выполняется целиком или не выполняется совсем, промежуточных состояний не бывает.
- **Согласованность** (Consistency) — успешная транзакция переводит базу из одного допустимого состояния в другое: соблюдаются типы, ограничения `CHECK`, `NOT NULL`, `UNIQUE`, внешние ключи.
- **Изолированность** (Isolation) — параллельные транзакции не влияют на результат друг друга (или влияют в пределах выбранного уровня изоляции). Обеспечивается версиями строк и блокировками.
- **Надёжность** (Durability) — если пользователь получил подтверждение `COMMIT`, изменения не пропадут даже при сбое сервера.

Таблица счетов с ограничением «баланс не может быть отрицательным»:

```sql run session=acid
CREATE TABLE accounts (
    id      serial PRIMARY KEY,
    balance int NOT NULL
);

INSERT INTO accounts (balance) VALUES (100), (50);

ALTER TABLE accounts
    ADD CONSTRAINT balance_non_negative CHECK (balance >= 0);

SELECT * FROM accounts ORDER BY id;
```

### Атомарность

Деньги списаны с первого счёта, и тут приложение получает ошибку — до зачисления на второй счёт дело не доходит. Приложение откатывает транзакцию:

```sql run session=acid
BEGIN;
UPDATE accounts SET balance = balance - 30 WHERE id = 1;
SELECT * FROM accounts ORDER BY id;   -- внутри транзакции: 70 и 50
-- здесь в приложении произошла ошибка, второй UPDATE не выполнен
ROLLBACK;

SELECT * FROM accounts ORDER BY id;   -- снова 100 и 50
```

Списание не сохранилось: деньги не потерялись «посередине» перевода.

### Согласованность

Попытка увести баланс в минус нарушает `CHECK`, и база отклоняет изменение (ошибка в этом примере — ожидаемая):

```sql run session=acid
BEGIN;
UPDATE accounts SET balance = balance - 1000 WHERE id = 1;
COMMIT;
```

`UPDATE` получает ошибку `violates check constraint "balance_non_negative"`. Транзакция прервана, и `COMMIT` после ошибки выполнит откат — баланс останется 100.

### Изолированность

Одна транзакция изменила строку, но ещё не зафиксировала изменения. Что видит и что может сделать другая?

::: warning Этот пример запускайте локально
Нужны два одновременных соединения, а в браузере база одна.
:::

| Шаг | Сессия 1 | Сессия 2 | Результат |
|---|---|---|---|
| 1 | `BEGIN;` | | |
| 2 | `UPDATE accounts SET balance = balance - 10 WHERE id = 1;` | | строка 1 заблокирована |
| 3 | `SELECT balance FROM accounts WHERE id = 1;` | | 90 — своё изменение видно |
| 4 | | `SELECT balance FROM accounts WHERE id = 1;` | 100 — чужое незафиксированное изменение не видно, чтение не ждёт |
| 5 | | `SET lock_timeout = '1s';` `UPDATE accounts SET balance = balance + 10 WHERE id = 1;` | ждёт блокировку, через секунду: `canceling statement due to lock timeout` |
| 6 | `COMMIT;` | | |
| 7 | | `SELECT balance FROM accounts WHERE id = 1;` | 90 |

`lock_timeout` здесь только для демонстрации: без него сессия 2 ждала бы до `COMMIT` сессии 1, а потом выполнила бы своё обновление.

### Надёжность

Перед тем как ответить на `COMMIT`, PostgreSQL записывает изменения в журнал предзаписи (WAL, write-ahead log) и сбрасывает его на диск. После аварии сервер восстанавливает зафиксированные транзакции из журнала. Проверка в ноутбуке: прибавили 5 к балансу второго счёта, зафиксировали, закрыли соединение («авария»), подключились заново:

```text
Баланс до изменения: 50
Баланс после переподключения: 55
```

Закрытие соединения, конечно, не настоящий сбой, но смысл тот же: подтверждённый `COMMIT` не отменяется.

## Уровни изоляции

Уровень изоляции (isolation level) определяет, насколько параллельные транзакции могут влиять друг на друга. Стандарт SQL описывает его через аномалии — эффекты, которые на этом уровне допустимы.

### Аномалии параллельных транзакций

- **Грязное чтение** (dirty read) — транзакция читает данные, которые другая транзакция ещё не зафиксировала и может откатить.
- **Неповторяющееся чтение** (non-repeatable read) — повторное чтение той же строки в рамках транзакции даёт другой результат, потому что другая транзакция изменила или удалила её и зафиксировалась.
- **Фантомное чтение** (phantom read) — повторный запрос с тем же условием возвращает другой набор строк: другая транзакция добавила или удалила подходящие строки.
- **Потерянное обновление** (lost update) — две транзакции читают одно значение, вычисляют новое и записывают; одно из изменений затирается другим.
- **Аномалия сериализации** (serialization anomaly) — результат параллельного выполнения транзакций не совпадает ни с одним порядком их последовательного выполнения. Например, два врача одновременно проверяют, что на дежурстве есть кто-то ещё, и оба уходят с дежурства (write skew).

### Уровни в PostgreSQL

- **READ UNCOMMITTED** — по стандарту допускает грязное чтение. В PostgreSQL его нет: этот уровень работает как READ COMMITTED.
- **READ COMMITTED** — уровень по умолчанию. Каждый запрос видит данные, зафиксированные к моменту его начала. Два одинаковых `SELECT` в одной транзакции могут вернуть разное.
- **REPEATABLE READ** — снимок данных фиксируется при первом запросе транзакции и не меняется до её конца. Если транзакция пытается изменить строку, которую после начала снимка изменил кто-то другой, она падает с ошибкой `could not serialize access due to concurrent update`.
- **SERIALIZABLE** — REPEATABLE READ плюс отслеживание зависимостей между транзакциями (SSI, Serializable Snapshot Isolation). Транзакции не выстраиваются в очередь и не блокируют друг друга: если результат мог бы отличаться от последовательного выполнения, одна из них падает с ошибкой сериализации, и приложение должно её повторить.

| Уровень | Грязное чтение | Неповторяющееся чтение | Фантомы | Потерянное обновление | Аномалия сериализации |
|---|---|---|---|---|---|
| READ UNCOMMITTED | нет | возможно | возможно | возможно | возможно |
| READ COMMITTED | нет | возможно | возможно | возможно | возможно |
| REPEATABLE READ | нет | нет | нет | нет (ошибка) | возможно |
| SERIALIZABLE | нет | нет | нет | нет (ошибка) | нет (ошибка) |

По стандарту SQL на REPEATABLE READ фантомы допустимы, но в PostgreSQL снимок данных исключает и их.

Уровень задают при начале транзакции:

```sql run
BEGIN ISOLATION LEVEL REPEATABLE READ;
SHOW transaction_isolation;
COMMIT;

BEGIN;
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;   -- до первого запроса транзакции
SHOW transaction_isolation;
COMMIT;

SHOW default_transaction_isolation;             -- уровень по умолчанию
```

В asyncpg — параметром: `conn.transaction(isolation='repeatable_read')`.

### Пример: READ COMMITTED и REPEATABLE READ

::: warning Этот пример запускайте локально
Нужны два одновременных соединения, а в браузере база одна.
:::

```sql
CREATE TABLE accounts (
    id      serial PRIMARY KEY,
    name    text,
    balance int NOT NULL
);
INSERT INTO accounts (name, balance) VALUES ('initial', 1000);
```

| Шаг | Сессия 1 (READ COMMITTED) | Сессия 2 | Результат в сессии 1 |
|---|---|---|---|
| 1 | `BEGIN;` `SELECT balance FROM accounts;` | | 1000 |
| 2 | | `BEGIN;` `UPDATE accounts SET balance = 2000 WHERE name = 'initial';` | |
| 3 | `SELECT balance FROM accounts;` | | 1000 — грязного чтения нет |
| 4 | | `COMMIT;` | |
| 5 | `SELECT balance FROM accounts;` | | 2000 — неповторяющееся чтение |
| 6 | `COMMIT;` | | |

Если сессию 1 начать с `BEGIN ISOLATION LEVEL REPEATABLE READ`, на шаге 5 она по-прежнему увидит 1000: снимок данных зафиксирован на шаге 1. Новое значение станет видно только в следующей транзакции.

## MVCC

Многоверсионное управление конкурентным доступом (MVCC, multiversion concurrency control) — способ, которым PostgreSQL позволяет транзакциям работать с данными одновременно, почти не мешая друг другу.

- **Версии строк.** `UPDATE` не перезаписывает строку на месте, а создаёт её новую версию; старая помечается как удалённая. `DELETE` только помечает версию. В каждой версии записано, какая транзакция её создала и какая удалила.
- **Снимки.** Транзакция видит версии, зафиксированные к моменту её снимка: на READ COMMITTED снимок берётся в начале каждого запроса, на REPEATABLE READ и SERIALIZABLE — в начале транзакции.
- **Чтение не блокирует запись, а запись — чтение.** Читатель просто берёт подходящую ему версию. Блокировки нужны только писателям одной и той же строки.
- **Конфликты.** Две записи одной строки упорядочиваются блокировкой; на REPEATABLE READ и SERIALIZABLE проигравшая транзакция получает ошибку сериализации и откатывается.
- **Очистка.** Версии, которые не нужны ни одной активной транзакции, убирает `VACUUM` (обычно autovacuum). Долгие транзакции мешают ему, и таблицы «распухают».

### Системные столбцы

У каждой строки есть скрытые столбцы:

- `ctid` — физический адрес версии строки: номер страницы в файле таблицы и номер записи на странице;
- `xmin` — номер транзакции, которая создала эту версию;
- `xmax` — номер транзакции, которая удалила эту версию или заблокировала строку; `0` — никто.

Номер текущей транзакции возвращает `pg_current_xact_id()` (старое имя — `txid_current()`).

```sql run session=mvcc
CREATE TABLE demo (
    id    serial PRIMARY KEY,
    value text
);
INSERT INTO demo (value) VALUES ('initial');

SELECT ctid, xmin, xmax, value FROM demo;
```

`UPDATE` создаёт новую версию по новому адресу, и её `xmin` — номер нашей транзакции:

```sql run session=mvcc
BEGIN;
SELECT pg_current_xact_id() AS my_xid;
UPDATE demo SET value = 'updated';
SELECT ctid, xmin, xmax, value FROM demo;
COMMIT;
```

Старая версия `(0,1)` физически осталась в таблице, но запросы её больше не видят; позже её уберёт `VACUUM`.

`xmax` не равен нулю — ещё не значит, что строка удалена. Он заполняется и при блокировке строки, и при откаченном обновлении:

```sql run session=mvcc
BEGIN;
SELECT pg_current_xact_id() AS my_xid;
SELECT ctid, xmin, xmax, value FROM demo FOR UPDATE;   -- блокируем строку
SELECT ctid, xmin, xmax, value FROM demo;              -- xmax = наша транзакция
COMMIT;

BEGIN;
UPDATE demo SET value = 'rolled back';
ROLLBACK;
SELECT ctid, xmin, xmax, value FROM demo;              -- xmax = откаченная транзакция, строка видна
```

Видимость решается не только по `xmin`/`xmax`, но и по статусу этих транзакций: удаление откаченной транзакцией не считается.

### Две сессии и снимок данных

::: warning Этот пример запускайте локально
Нужны два одновременных соединения, а в браузере база одна.
:::

| Шаг | Сессия 1 (REPEATABLE READ) | Сессия 2 | Результат в сессии 1 |
|---|---|---|---|
| 1 | `BEGIN ISOLATION LEVEL REPEATABLE READ;` `SELECT ctid, xmin, xmax, value FROM demo;` | | `(0,1)`, xmin=2043, xmax=0, `initial` |
| 2 | | `UPDATE demo SET value = 'updated';` (автофиксация) | |
| 3 | `SELECT ctid, xmin, xmax, value FROM demo;` | | `(0,1)`, xmin=2043, xmax=2044, `initial` |
| 4 | `COMMIT;` `SELECT ctid, xmin, xmax, value FROM demo;` | | `(0,2)`, xmin=2044, xmax=0, `updated` |

На шаге 3 сессия 1 по-прежнему видит старую версию — она входит в её снимок. Но у этой версии уже стоит `xmax = 2044`: транзакция сессии 2 её «удалила», создав новую версию `(0,2)`. После `COMMIT` новый запрос берёт свежий снимок и видит новую версию.

### HOT-обновление

HOT-обновление (Heap-Only Tuple update) — оптимизация `UPDATE`. Новая версия строки всё равно создаётся, но если не меняются индексированные столбцы и на той же странице есть место, она кладётся на ту же страницу, а индексы не обновляются: старая версия ссылается на новую цепочкой внутри страницы. Это экономит запись в индексы и упрощает очистку. Чтобы HOT срабатывал чаще, таблицам с частыми обновлениями задают `fillfactor` меньше 100 — оставляют на страницах свободное место.

## Блокировки

Блокировки (locks) защищают данные от одновременной несовместимой записи.

- **Блокировки строк** (row-level locks) накладываются на отдельные строки: `UPDATE`, `DELETE`, `SELECT ... FOR UPDATE` / `FOR SHARE`. Обычный `SELECT` строки не блокирует.
- **Блокировки таблиц** (table-level locks) берут все команды. Обычные запросы — слабые режимы, совместимые между собой: `SELECT` — `ACCESS SHARE`, `INSERT`/`UPDATE`/`DELETE` — `ROW EXCLUSIVE`. Изменения структуры (`ALTER TABLE`, `DROP TABLE`, `TRUNCATE`) берут `ACCESS EXCLUSIVE`, который конфликтует со всем, даже с чтением.
- **Взаимная блокировка** (deadlock) — две или больше транзакций ждут друг друга по кругу: каждая держит то, что нужно другой.

Таблица для примеров:

```sql run session=locks
CREATE TABLE accounts (
    id      serial PRIMARY KEY,
    balance int NOT NULL
);
INSERT INTO accounts (balance) VALUES (100), (50);
```

### Блокировка строк

Типичная задача: прочитать баланс, проверить в приложении, хватает ли денег, и записать новый. Если две транзакции сделают это одновременно, одно из списаний потеряется (потерянное обновление). `SELECT ... FOR UPDATE` блокирует строку при чтении, и вторая транзакция будет ждать первую:

```sql run session=locks
BEGIN;
SELECT balance FROM accounts WHERE id = 1 FOR UPDATE;

-- какие блокировки держит наша транзакция
SELECT locktype, relation::regclass, mode
FROM pg_locks
WHERE pid = pg_backend_pid()
  AND (relation = 'accounts'::regclass OR locktype = 'transactionid');

UPDATE accounts SET balance = balance - 10 WHERE id = 1;
COMMIT;

SELECT * FROM accounts ORDER BY id;
```

Сами блокировки строк хранятся не в `pg_locks`, а в строке (в `xmax`, см. [MVCC](#системные-столбцы)). В `pg_locks` видна блокировка таблицы в режиме `RowShareLock` и номер нашей транзакции (`transactionid`) — именно его ждут те, кто натыкается на заблокированную строку.

Что происходит со второй сессией:

::: warning Этот пример запускайте локально
Нужны два одновременных соединения, а в браузере база одна.
:::

| Шаг | Сессия 1 | Сессия 2 | Результат |
|---|---|---|---|
| 1 | `BEGIN;` `UPDATE accounts SET balance = balance - 10 WHERE id = 1;` | | |
| 2 | `SELECT balance FROM accounts WHERE id = 1;` | | 90 |
| 3 | | `SELECT balance FROM accounts WHERE id = 1;` | 100 — чтение не блокируется |
| 4 | | `SET lock_timeout = '1s';` `UPDATE accounts SET balance = balance + 10 WHERE id = 1;` | `canceling statement due to lock timeout` |
| 5 | `COMMIT;` | | итоговый баланс 90 |

### Блокировка таблицы

Явно таблицу блокируют командой `LOCK TABLE` (только внутри транзакции); блокировка снимается при её завершении:

```sql run session=locks
BEGIN;
LOCK TABLE accounts IN ACCESS EXCLUSIVE MODE;

SELECT relation::regclass, mode, granted
FROM pg_locks
WHERE pid = pg_backend_pid() AND relation = 'accounts'::regclass;

COMMIT;
```

`ACCESS EXCLUSIVE` не пускает даже читателей:

::: warning Этот пример запускайте локально
Нужны два одновременных соединения, а в браузере база одна.
:::

| Шаг | Сессия 1 | Сессия 2 | Результат |
|---|---|---|---|
| 1 | `BEGIN;` `LOCK TABLE accounts IN ACCESS EXCLUSIVE MODE;` | | таблица заблокирована полностью |
| 2 | | `SET lock_timeout = '1s';` `SELECT * FROM accounts;` | `canceling statement due to lock timeout` |
| 3 | `COMMIT;` | | |
| 4 | | `SELECT * FROM accounts;` | строки читаются |

Поэтому `ALTER TABLE` на нагруженной таблице опасен: пока он ждёт свою блокировку, за ним в очередь встают и все обычные запросы. Для миграций задают небольшой `lock_timeout` и повторяют попытку.

### Взаимная блокировка

::: warning Этот пример запускайте локально
Нужны два одновременных соединения, а в браузере база одна.
:::

Исходные балансы: счёт 1 — 90, счёт 2 — 50.

| Шаг | Сессия 1 (T1) | Сессия 2 (T2) | Результат |
|---|---|---|---|
| 1 | `BEGIN;` `UPDATE accounts SET balance = balance - 1 WHERE id = 1;` | | T1 держит строку 1 |
| 2 | | `BEGIN;` `UPDATE accounts SET balance = balance - 1 WHERE id = 2;` | T2 держит строку 2 |
| 3 | `UPDATE accounts SET balance = balance + 1 WHERE id = 2;` | | T1 ждёт T2 |
| 4 | | `UPDATE accounts SET balance = balance + 1 WHERE id = 1;` | T2 ждёт T1 — цикл |
| 5 | | | через `deadlock_timeout` (1 с) PostgreSQL находит цикл в графе ожиданий и прерывает одну транзакцию: T2 получает `deadlock detected` |
| 6 | `UPDATE 1`, `COMMIT;` | `ROLLBACK;` | |

Вывод ноутбука:

```text
Результаты: ['UPDATE 1', DeadlockDetectedError('deadlock detected')]
Строки после завершения транзакций: [<Record id=1 balance=89>, <Record id=2 balance=51>]
```

Изменения T1 (−1 со счёта 1, +1 на счёт 2) зафиксированы, T2 откатилась целиком.

Как избежать взаимных блокировок:

- блокировать строки в одном и том же порядке во всех транзакциях, например `SELECT ... WHERE id IN (1, 2) ORDER BY id FOR UPDATE`;
- делать транзакции короткими и не ждать внутри них ответа пользователя или внешних сервисов;
- в приложении ловить ошибки `deadlock_detected` и `serialization_failure` и повторять транзакцию целиком.

## Связанные темы

- [Подключение к PostgreSQL](connect.md)
- [Запросы](query.md)
- [Быстрая загрузка данных](bulk_load.md)
- [PostgreSQL](README.md)
