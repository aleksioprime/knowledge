# Выполнение запроса, индексы и EXPLAIN

Запрос к таблице на сто тысяч строк работает то мгновенно, то заметно дольше — хотя текст почти одинаковый. Чтобы понять почему, нужно знать, что PostgreSQL делает с запросом, как он выбирает способ чтения данных и чем ему помогают индексы. А проверять свои догадки — командой `EXPLAIN`.

## Путь запроса

1. **Приём запроса.** Клиент отправляет строку SQL по сетевому протоколу, её получает серверный процесс (backend), обслуживающий это соединение.
2. **Разбор (parser).** Проверяется синтаксис и существование таблиц и столбцов, строится дерево разбора (parse tree).
3. **Переписывание (rewriter).** Вместо представлений (VIEW) подставляются их запросы, применяются правила (RULE).
4. **Планирование (planner/optimizer).** По статистике из `pg_statistic` планировщик выбирает:
   - способ доступа к таблице: последовательное чтение (Seq Scan), индекс (Index Scan), битовая карта (Bitmap Scan);
   - порядок соединения таблиц и алгоритм соединения (Nested Loop, Hash Join, Merge Join);
   - где применять фильтры.

   Результат — физический план выполнения.
5. **Исполнение (executor).** Узлы плана работают как итераторы: чтение → фильтр → соединение → сортировка → агрегация.
6. **MVCC.** Для каждой строки выбирается версия, видимая текущей транзакции: по служебным полям `xmin`, `xmax` и снимку данных (snapshot).
7. **Блокировки.** `SELECT` читает без блокировок строк, `UPDATE` и `DELETE` блокируют изменяемые строки. При конфликте транзакция ждёт, получает ошибку по таймауту или одна из транзакций прерывается при взаимоблокировке (deadlock).
8. **Чтение и запись данных.** Страницы читаются из общего буферного кеша (shared buffers) или с диска. `UPDATE` и `DELETE` создают новые версии строк, индексы обновляются вместе с таблицей.
9. **Журнал предзаписи (WAL).** Изменения сначала записываются в WAL — это и обеспечивает долговечность (durability).
10. **Ответ клиенту.** Клиент получает строки результата или статус команды (`INSERT 0 1`, `UPDATE 3`).
11. **Завершение транзакции.** После `COMMIT` или `ROLLBACK` изменения фиксируются или отменяются, блокировки освобождаются, снимок данных больше не нужен.

## Как читать план: EXPLAIN

План выполнения — последовательность операций, которыми СУБД получает результат запроса. Его выбирает оптимизатор: перебирает возможные планы и оценивает их стоимость по статистике.

- `EXPLAIN запрос` показывает план, но сам запрос не выполняет.
- `EXPLAIN ANALYZE запрос` выполняет запрос и показывает план с реальными цифрами. Осторожно с `UPDATE` и `DELETE`: изменения действительно произойдут, поэтому такие запросы анализируют внутри `BEGIN ... ROLLBACK`.

В каждом узле `EXPLAIN` есть:

- `cost=0.00..1887.00` — оценка стоимости в условных единицах: до первой строки и до последней;
- `rows` — сколько строк планировщик ожидает получить;
- `width` — средний размер строки в байтах;
- `Filter`, `Index Cond` — какое условие и где применяется.

`EXPLAIN ANALYZE` добавляет:

- `actual time` — время до первой строки и до последней, в миллисекундах;
- `rows` в скобках `actual` — сколько строк получено на самом деле;
- `loops` — сколько раз выполнялся узел;
- `Rows Removed by Filter` — сколько строк прочитано и отброшено;
- `Planning Time` и `Execution Time` — время планирования и выполнения.

Если оценка `rows` сильно расходится с реальной, планировщик ошибается в статистике — обычно помогает `ANALYZE таблица`.

### Таблица для опытов

Все примеры ниже работают с таблицей заказов на 100 000 строк. Данные строятся формулами от номера строки, поэтому при каждом запуске одинаковы. После массовой вставки обязательно выполняется `ANALYZE`: без свежей статистики планировщик гадает о размере таблицы и распределении значений.

```sql run setup=orders
CREATE TABLE orders (
    id serial PRIMARY KEY,
    name text,
    description text,
    order_number text,
    customer_id int,
    status text,
    total int,
    data jsonb,
    tags text[],
    coordinates point,
    created_at timestamp
);

INSERT INTO orders (name, description, order_number, customer_id, status,
                    total, data, tags, coordinates, created_at)
SELECT
    'Order ' || i,
    (ARRAY['Доставка курьером', 'Самовывоз из пункта выдачи',
           'Срочная доставка до двери', 'Доставка почтой'])[i % 4 + 1]
        || CASE WHEN i % 1000 = 0 THEN ', хрупкий груз' ELSE '' END,
    'A' || i,
    i % 2000 + 1,
    CASE WHEN i % 100 = 0 THEN 'new' WHEN i % 10 = 0 THEN 'cancelled' ELSE 'done' END,
    i * 7919 % 10000,                       -- суммы «вразброс» от 0 до 9999
    jsonb_build_object(
        'city', (ARRAY['Москва', 'Казань', 'Пермь', 'Томск', 'Сочи'])[i % 5 + 1],
        'payment', CASE WHEN i % 3 = 0 THEN 'cash' ELSE 'card' END
    ) || CASE WHEN i % 500 = 0 THEN '{"promo": "AUTUMN"}'::jsonb ELSE '{}' END,
    ARRAY['tag' || i % 10] || CASE WHEN i % 1000 = 0 THEN ARRAY['gift'] ELSE '{}' END,
    point(i % 1000 / 10.0, i / 1000),       -- сетка 100 × 100
    timestamp '2025-01-01' + i * interval '5 minutes'
FROM generate_series(1, 100000) AS i;

ANALYZE orders;

SELECT count(*) FROM orders;
```

Индексов, кроме первичного ключа, пока нет — поиск по сумме читает всю таблицу:

```sql run uses=orders
EXPLAIN SELECT * FROM orders WHERE total BETWEEN 100 AND 120;

EXPLAIN ANALYZE SELECT * FROM orders WHERE total BETWEEN 100 AND 120;
```

`Seq Scan` — последовательное чтение всех страниц таблицы. `Rows Removed by Filter` показывает, что ради двух сотен строк прочитано и отброшено почти сто тысяч.

## Индексы

Индекс (index) — отдельная структура данных, которая хранит значения столбцов в удобном для поиска виде и ссылки на строки таблицы. Он работает как алфавитный указатель в книге: вместо того чтобы листать всю книгу, сразу открываешь нужную страницу.

У индекса есть цена: он занимает место на диске, и при каждой вставке или изменении строки PostgreSQL обновляет сначала таблицу, а затем все её индексы. Поэтому индексы создают под конкретные запросы, а не «на всякий случай».

Каждый пример ниже создаёт свой индекс, показывает план и в конце удаляет индекс, чтобы следующий пример начинался с той же таблицы без лишних индексов.

### B-tree

B-дерево (B-tree) — тип индекса по умолчанию. Значения хранятся отсортированными в сбалансированном дереве. Поиск спускается от корневой страницы к листовой, на каждом уровне выбирая ветку по диапазону значений. Глубина дерева обычно 2–4 уровня даже для миллионов строк, поэтому быстро работают:

- поиск по равенству (`=`);
- диапазоны (`<`, `>`, `BETWEEN`) и `LIKE 'abc%'` (для текста — при подходящей сортировке или с классом операторов `text_pattern_ops`);
- `ORDER BY` и `min`/`max` — данные в индексе уже отсортированы.

```sql run uses=orders
EXPLAIN SELECT * FROM orders WHERE order_number = 'A100';

CREATE INDEX idx_orders_number ON orders (order_number);

-- тот же запрос: теперь одна строка находится по индексу
EXPLAIN SELECT * FROM orders WHERE order_number = 'A100';

CREATE INDEX idx_orders_total ON orders (total);

-- диапазон: индекс отбирает строки, затем они читаются из таблицы
EXPLAIN SELECT * FROM orders WHERE total BETWEEN 100 AND 120;

-- сортировка не нужна: строки берутся из индекса уже по порядку
EXPLAIN SELECT * FROM orders ORDER BY total DESC LIMIT 5;

DROP INDEX idx_orders_number, idx_orders_total;
```

В планах встречаются три способа чтения через индекс:

- **Index Scan** — идём по индексу и для каждой найденной записи читаем строку из таблицы. Хорош, когда строк мало или нужен порядок индекса.
- **Bitmap Index Scan + Bitmap Heap Scan** — сначала по индексу собирается битовая карта подходящих страниц, затем страницы читаются по порядку. Выгоден, когда строк от сотен до десятков тысяч: каждая страница таблицы читается один раз.
- **Index Only Scan** — все нужные столбцы есть в индексе, в таблицу заходить не нужно (почти: проверяется карта видимости).

### Когда индекс не помогает

Индекс не используется, если запрос отбирает большую часть таблицы: прыгать по индексу и читать строки вразнобой дороже, чем прочитать таблицу подряд.

```sql run uses=orders
CREATE INDEX idx_orders_total ON orders (total);

-- почти все строки: Seq Scan, хотя индекс есть
EXPLAIN ANALYZE SELECT * FROM orders WHERE total > 50;

-- полпроцента строк: индекс
EXPLAIN ANALYZE SELECT * FROM orders WHERE total < 50;

DROP INDEX idx_orders_total;
```

На маленькой таблице индекс тоже не нужен: все строки лежат на одной-двух страницах, и прочитать их целиком дешевле, чем обращаться к индексу. Поэтому проверять индексы на десятке тестовых строк бессмысленно — план будет `Seq Scan` при любом индексе:

```sql run
CREATE TABLE small_orders (id serial PRIMARY KEY, order_number text);
INSERT INTO small_orders (order_number) SELECT 'A' || i FROM generate_series(1, 100) AS i;
CREATE INDEX ON small_orders (order_number);
ANALYZE small_orders;

EXPLAIN SELECT * FROM small_orders WHERE order_number = 'A100';
```

Ещё индекс не используется, когда столбец в условии обёрнут в функцию или выражение (`lower(name) = ...`, `total + 0 > 100`), — для этого нужен функциональный индекс, о нём ниже.

### Hash

Hash-индекс хранит не сами значения, а их хеш-коды. Хеш указывает на «корзину» со ссылками на строки, поэтому поиск занимает почти постоянное время, O(1). Порядка значений в индексе нет, и он подходит только для точного равенства (`=`): ни диапазонов, ни сортировки.

```sql run uses=orders
CREATE INDEX idx_orders_number_hash ON orders USING hash (order_number);

-- равенство: индекс используется
EXPLAIN SELECT * FROM orders WHERE order_number = 'A100';

-- диапазон: hash-индекс бесполезен, Seq Scan
EXPLAIN SELECT * FROM orders WHERE order_number > 'A99990';

DROP INDEX idx_orders_number_hash;
```

На практике B-tree обычно не уступает hash-индексу по скорости равенства и умеет больше, поэтому hash выбирают редко — например, для длинных значений, где хеш компактнее самой строки.

### GIN

GIN (Generalized Inverted Index) — инвертированный индекс, как в поисковых движках. Значение не индексируется целиком: PostgreSQL раскладывает его на элементы — ключи и значения JSONB, элементы массива, слова текста — и хранит для каждого элемента список строк, где он встречается. При поиске нужные элементы находятся в индексе, а списки строк объединяются или пересекаются по логике запроса.

```sql run uses=orders
-- JSONB: поиск по содержимому документа (оператор @>)
CREATE INDEX idx_orders_data_gin ON orders USING gin (data);
EXPLAIN SELECT * FROM orders WHERE data @> '{"promo": "AUTUMN"}';

-- массивы: заказы с тегом gift
CREATE INDEX idx_orders_tags_gin ON orders USING gin (tags);
EXPLAIN SELECT * FROM orders WHERE tags @> ARRAY['gift'];

-- полнотекстовый поиск: индекс по выражению to_tsvector
CREATE INDEX idx_orders_fts ON orders USING gin (to_tsvector('russian', description));
EXPLAIN SELECT * FROM orders
WHERE to_tsvector('russian', description) @@ to_tsquery('russian', 'хрупкий');

SELECT id, description FROM orders
WHERE to_tsvector('russian', description) @@ to_tsquery('russian', 'хрупкий')
LIMIT 3;

DROP INDEX idx_orders_data_gin, idx_orders_tags_gin, idx_orders_fts;
```

В полнотекстовом запросе выражение в `WHERE` должно совпадать с выражением индекса, включая конфигурацию `'russian'`, иначе индекс не подойдёт. Словарь приводит слова к основе, поэтому «хрупкий» находит и «хрупкий груз», и «хрупкие товары».

GIN быстро ищет, но медленнее обновляется, чем B-tree: одна строка порождает много элементов индекса.

### GiST

GiST (Generalized Search Tree) — обобщённое дерево поиска для сложных объектов: геометрических фигур, точек, диапазонов, интервалов времени. Каждый узел дерева хранит «область» (например, ограничивающий прямоугольник, bounding box), внутри которой лежат значения дочерних узлов. Поиск спускается только в те ветви, чьи области могут содержать искомое.

```sql run uses=orders
CREATE INDEX idx_orders_coord_gist ON orders USING gist (coordinates);

-- точки внутри прямоугольника
EXPLAIN SELECT * FROM orders WHERE coordinates <@ box '((10,10),(11,11))';

-- пять ближайших к точке заказов: поиск ближайших соседей (KNN) прямо по индексу
EXPLAIN SELECT id, coordinates FROM orders
ORDER BY coordinates <-> point '(50,50)'
LIMIT 5;

SELECT id, coordinates FROM orders
ORDER BY coordinates <-> point '(50,50)'
LIMIT 5;

DROP INDEX idx_orders_coord_gist;
```

GiST лежит в основе ограничений-исключений (`EXCLUDE`), например «бронирования одной комнаты не пересекаются по времени», и геоданных в расширении PostGIS.

### BRIN

BRIN (Block Range Index) хранит для каждого диапазона страниц таблицы (по умолчанию 128 страниц) только минимум и максимум значений. Поиск отбрасывает диапазоны, в которые значение заведомо не попадает, и читает остальные целиком.

Индекс получается крошечным, но работает, только если значения коррелируют с физическим порядком строк: время создания в журнале событий, автоинкрементный номер. В нашей таблице `created_at` растёт вместе с номером строки:

```sql run uses=orders
CREATE INDEX idx_orders_created_brin ON orders USING brin (created_at);
CREATE INDEX idx_orders_created_btree ON orders (created_at);

SELECT relname AS index_name, pg_size_pretty(pg_relation_size(oid)) AS size
FROM pg_class
WHERE relname IN ('idx_orders_created_brin', 'idx_orders_created_btree');

DROP INDEX idx_orders_created_btree;

-- один день заказов: Bitmap Heap Scan по BRIN-индексу
EXPLAIN ANALYZE SELECT count(*) FROM orders
WHERE created_at >= '2025-03-01' AND created_at < '2025-03-02';

DROP INDEX idx_orders_created_brin;
```

`Rows Removed by Index Recheck` — строки из прочитанных диапазонов страниц, которые не подошли под условие: BRIN неточен и всегда перепроверяет строки.

### Другие типы

- **SP-GiST** (space-partitioned GiST) — деревья с неравными разбиениями: префиксные деревья для текста, quad-деревья для точек, IP-адреса.
- **Bloom** — сигнатурный индекс из расширения `bloom` для проверки равенства по любому сочетанию многих столбцов.

## Индексы по способу применения

### Простой и составной

Простой индекс строится по одному столбцу — как все индексы выше. Составной (multicolumn) — по нескольким, он нужен, когда запрос фильтрует по нескольким полям одновременно.

Порядок столбцов важен. Индекс `(customer_id, created_at)` отсортирован сначала по клиенту, а внутри клиента — по дате. Поэтому он подходит для условий по `customer_id` и по `customer_id` вместе с `created_at`, а также отдаёт заказы клиента уже упорядоченными по дате. По одному `created_at` такой индекс работает плохо: до PostgreSQL 17 включительно он не использовался вовсе, а с версии 18 планировщик может применить пропуск по индексу (skip scan) — перебрать все значения `customer_id` и в каждом искать дату. Это лучше полного чтения таблицы, но примерно в сто раз дороже поиска по первому столбцу (сравните `cost` в планах).

```sql run uses=orders
CREATE INDEX idx_orders_customer_created ON orders (customer_id, created_at);

-- последние заказы клиента: без сортировки, сразу из индекса
EXPLAIN SELECT * FROM orders
WHERE customer_id = 42
ORDER BY created_at DESC
LIMIT 5;

-- условие только по второму столбцу: skip scan по всем customer_id
EXPLAIN SELECT * FROM orders WHERE created_at = '2025-03-01 12:00';

DROP INDEX idx_orders_customer_created;
```

### Частичный

Частичный индекс (partial index) строится только по строкам, подходящим под условие `WHERE`. Он меньше полного и быстрее обновляется. Типичный случай — небольшая «горячая» часть таблицы: новые заказы среди миллионов выполненных.

```sql run uses=orders
CREATE INDEX idx_orders_new ON orders (created_at) WHERE status = 'new';

-- условие запроса совпадает с условием индекса: индекс используется
EXPLAIN SELECT * FROM orders WHERE status = 'new' ORDER BY created_at LIMIT 10;

DROP INDEX idx_orders_new;
```

### Функциональный

Функциональный индекс (индекс по выражению, expression index) хранит результат функции от столбца. Он нужен, когда в условии столбец обёрнут в функцию: обычный индекс по `name` для `lower(name) = ...` не подойдёт.

```sql run uses=orders
CREATE INDEX idx_orders_name ON orders (name);

-- индекс по name не помогает: в условии lower(name)
EXPLAIN SELECT * FROM orders WHERE lower(name) = 'order 42';

CREATE INDEX idx_orders_lower_name ON orders (lower(name));
-- ANALYZE собирает статистику и по выражению индекса
ANALYZE orders;

EXPLAIN SELECT * FROM orders WHERE lower(name) = 'order 42';

DROP INDEX idx_orders_name, idx_orders_lower_name;
```

### Уникальный

Уникальный индекс гарантирует, что в столбце или сочетании столбцов нет повторов. Его автоматически создают `PRIMARY KEY` и ограничение `UNIQUE`. Вставка дубликата завершается ошибкой — так и задумано:

```sql run
CREATE TABLE orders (id serial PRIMARY KEY, order_number text);
CREATE UNIQUE INDEX idx_orders_unique_number ON orders (order_number);

INSERT INTO orders (order_number) VALUES ('A1'), ('A2');
INSERT INTO orders (order_number) VALUES ('A1');
```

Уникальность лучше объявлять ограничением `UNIQUE` в таблице: так она видна в описании схемы, а индекс PostgreSQL создаст сам.

## Связанные темы

- [Проектирование схемы](schema_design.md)
- [Секционирование таблиц](partitioning.md)
- [Транзакции](transaction.md)
- [PostgreSQL](README.md)
