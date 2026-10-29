# NULL и агрегация

## NULL

`NULL` означает «значение неизвестно или отсутствует». Это не ноль и не пустая строка. SQL использует трёхзначную логику: `TRUE`, `FALSE`, `UNKNOWN`.

### Сравнение и фильтрация

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

### Арифметика и строки

Почти любая арифметика с `NULL` даёт `NULL`:

```sql
price * quantity              -- NULL, если один операнд NULL
price * COALESCE(quantity, 0) -- подставить 0
```

`COALESCE(a, b, c)` возвращает первый не-`NULL`. `NULLIF(a, b)` возвращает `NULL`, если значения равны, и помогает, например, избегать деления на ноль:

```sql
revenue / NULLIF(quantity, 0)
```

### Агрегация с NULL

Большинство агрегатов игнорирует `NULL`:

- `COUNT(*)` считает строки;
- `COUNT(1)` также считает строки, потому что `1` не `NULL`;
- `COUNT(column)` считает только строки, где `column IS NOT NULL`;
- `SUM`, `AVG`, `MIN`, `MAX` игнорируют `NULL` и возвращают `NULL`, если входных значений не осталось;
- `COUNT(...)` для пустого набора возвращает `0`.

`COUNT(*)` и `COUNT(1)` в современных СУБД обычно имеют одинаковый план. `COUNT(primary_key)` логически тоже равен им, если ключ `NOT NULL`, но лучше прямо выражать намерение через `COUNT(*)`.

### Сортировка NULL

Стандарт не задаёт единый порядок `NULL` по умолчанию. В PostgreSQL `NULL` считается больше не-`NULL`: для `ASC` по умолчанию это `NULLS LAST`, для `DESC` — `NULLS FIRST`.

```sql
ORDER BY finished_at DESC NULLS LAST
```

Указывайте `NULLS FIRST` / `NULLS LAST`, если порядок важен. В MySQL нет такого синтаксиса; применяют выражение вроде `ORDER BY finished_at IS NULL, finished_at`.

### Как не допускать NULL

Лучший способ — ограничение схемы:

```sql
ALTER TABLE employees
ALTER COLUMN email SET NOT NULL;
```

Сначала нужно найти и исправить существующие `NULL`. Не заменяйте любое отсутствие пустой строкой или нулём: это может исказить предметный смысл. `NOT NULL` следует сочетать с разумным `DEFAULT` только там, где значение действительно известно.

## Агрегация

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
