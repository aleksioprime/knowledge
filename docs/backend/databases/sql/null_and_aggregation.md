# NULL и агрегация

У задачи может не быть исполнителя или оценки по времени, и это нужно отличать от «ноль часов» и «пустая строка». В SQL для этого есть `NULL`, но он живёт по своим правилам: не равен ничему, выпадает из арифметики и по-разному учитывается агрегатами. Здесь — как фильтровать, сортировать и считать данные с пропусками и как `GROUP BY` сворачивает строки в итоги по группам.

## Минимальный пример

```sql run
CREATE TABLE task (id INTEGER PRIMARY KEY, title TEXT, user_id INTEGER, hours NUMERIC);
INSERT INTO task VALUES
    (1, 'Купить хлеб', 1, 0.5),
    (2, 'Написать отчёт', 1, NULL),
    (3, 'Позвонить врачу', NULL, 0.2);

SELECT COUNT(*) AS all_rows, COUNT(hours) AS with_hours, SUM(hours) AS total
FROM task;
-- 3 | 2 | 0.7      (COUNT(hours) и SUM пропускают NULL)

SELECT title FROM task WHERE user_id = NULL;
-- 0 строк: сравнение с NULL даёт UNKNOWN, а не TRUE
SELECT title FROM task WHERE user_id IS NULL;
-- Позвонить врачу

SELECT user_id, COUNT(*) AS task_count
FROM task
GROUP BY user_id
ORDER BY user_id;
-- 1    | 2
-- NULL | 1      (NULL образует свою группу)
```

## Как это работает

### NULL

`NULL` означает «значение неизвестно или отсутствует». Это не ноль и не пустая строка. SQL использует трёхзначную логику: `TRUE`, `FALSE`, `UNKNOWN`.

#### Сравнение и фильтрация

```sql
WHERE manager_id IS NULL
WHERE manager_id IS NOT NULL
```

`manager_id = NULL` и `manager_id <> NULL` не работают как ожидается: результат — `UNKNOWN`. `WHERE` оставляет только строки, для которых условие равно `TRUE`.

В PostgreSQL для null-safe сравнения есть:

```sql
a IS NOT DISTINCT FROM b -- NULL считается равным NULL
a IS DISTINCT FROM b
```

#### Арифметика и строки

Почти любая арифметика с `NULL` даёт `NULL`:

```sql
price * quantity              -- NULL, если один операнд NULL
price * COALESCE(quantity, 0) -- подставить 0
```

`COALESCE(a, b, c)` возвращает первый не-`NULL`. `NULLIF(a, b)` возвращает `NULL`, если значения равны, и помогает, например, избегать деления на ноль:

```sql
revenue / NULLIF(quantity, 0)
```

#### Агрегация с NULL

Большинство агрегатов игнорирует `NULL`:

- `COUNT(*)` считает строки;
- `COUNT(1)` также считает строки, потому что `1` не `NULL`;
- `COUNT(column)` считает только строки, где `column IS NOT NULL`;
- `SUM`, `AVG`, `MIN`, `MAX` игнорируют `NULL` и возвращают `NULL`, если входных значений не осталось;
- `COUNT(...)` для пустого набора возвращает `0`.

`COUNT(*)` и `COUNT(1)` в современных СУБД обычно имеют одинаковый план. `COUNT(primary_key)` логически тоже равен им, если ключ `NOT NULL`, но лучше прямо выражать намерение через `COUNT(*)`.

#### Сортировка NULL

Стандарт не задаёт единый порядок `NULL` по умолчанию. В PostgreSQL `NULL` считается больше не-`NULL`: для `ASC` по умолчанию это `NULLS LAST`, для `DESC` — `NULLS FIRST`.

```sql
ORDER BY finished_at DESC NULLS LAST
```

Указывайте `NULLS FIRST` / `NULLS LAST`, если порядок важен. В MySQL нет такого синтаксиса; применяют выражение вроде `ORDER BY finished_at IS NULL, finished_at`.

#### Как не допускать NULL

Лучший способ — ограничение схемы:

```sql
ALTER TABLE employees
ALTER COLUMN email SET NOT NULL;
```

Сначала нужно найти и исправить существующие `NULL`. Не заменяйте любое отсутствие пустой строкой или нулём: это может исказить предметный смысл. `NOT NULL` следует сочетать с разумным `DEFAULT` только там, где значение действительно известно.

### Агрегация

`GROUP BY` сворачивает строки в одну строку на группу:

```sql
SELECT department_id,
       COUNT(*) AS employee_count,
       AVG(salary) AS avg_salary
FROM employees
WHERE active
GROUP BY department_id
HAVING COUNT(*) >= 5;
```

В стандартном SQL выбранный столбец должен:

- входить в `GROUP BY`;
- быть аргументом агрегатной функции;
- либо быть функционально зависимым от ключа группы, если СУБД умеет это доказывать.

`WHERE` фильтрует **строки до группировки**, `HAVING` — **группы после неё**. Условия, которым не нужны агрегаты, обычно выгоднее держать в `WHERE`.

Полезная условная агрегация:

```sql
SELECT department_id,
       COUNT(*) FILTER (WHERE active) AS active_count, -- PostgreSQL
       SUM(CASE WHEN active THEN 1 ELSE 0 END) AS portable_active_count
FROM employees
GROUP BY department_id;
```

## Частые ошибки

- `WHERE status != 'done'` при `NULL` в `status` → строки с неизвестным статусом пропадают из выборки, хотя они точно «не done» → добавить `OR status IS NULL` или использовать `status IS DISTINCT FROM 'done'`.
- `AVG(hours)` для оценки средней нагрузки → пропущенные оценки просто не учитываются, среднее завышено или занижено → решить явно: `AVG(COALESCE(hours, 0))` или отдельно вывести `COUNT(*) - COUNT(hours)`.
- `SUM(amount)` по пустой группе или `MAX` по всем-`NULL` → в отчёт уходит `NULL` вместо 0 → обернуть в `COALESCE(SUM(amount), 0)`.
- Столбец в `SELECT`, которого нет в `GROUP BY` и в агрегате → ошибка «must appear in the GROUP BY clause» (а в старом MySQL — случайное значение из группы) → добавить столбец в `GROUP BY` или обернуть агрегатом.
- Условие по агрегату в `WHERE` (`WHERE COUNT(*) > 5`) → ошибка «aggregate functions are not allowed in WHERE» → перенести в `HAVING`; условия по исходным строкам, наоборот, держать в `WHERE`.

## Когда не использовать

`NULL` не нужен там, где отсутствие значения имеет точный смысл: для флагов берите `BOOLEAN NOT NULL DEFAULT false`, для счётчиков — `NOT NULL DEFAULT 0`. Каждый `NULL` в схеме — это ветка «а если неизвестно» в каждом запросе; чем их меньше, тем проще код.

`GROUP BY` лишний, когда нужен итог рядом с каждой строкой, а не вместо строк: для «доля задачи в сумме часов пользователя» или «номер задачи внутри группы» берите [оконные функции](windows.md). Если агрегация по большой таблице нужна в каждом запросе, итоги выгоднее посчитать заранее и хранить в отдельной таблице или материализованном представлении.

## Связанные темы

- [Основы SQL](basics.md) — порядок выполнения `SELECT` и ограничения `NOT NULL`
- [JOIN](joins.md) — `NULL` в несовпавших строках `LEFT JOIN`
- [CASE, фильтрация и оконные функции](windows.md) — итоги без схлопывания строк
