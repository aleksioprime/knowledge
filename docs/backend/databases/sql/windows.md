# CASE, фильтрация и оконные функции

Нужно вывести каждую задачу вместе с её номером внутри списка пользователя, накопленной суммой часов и пометкой «долгая / короткая», не сворачивая строки в итоги. `GROUP BY` здесь не подходит — он схлопывает строки, а оконные функции считают по группе и оставляют каждую строку на месте. Здесь — `CASE` как выражение, разница между `WHERE`, `HAVING` и `QUALIFY`, и устройство окна: секции, порядок и frame.

## Минимальный пример

```sql run
CREATE TABLE task (id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT, hours NUMERIC);
INSERT INTO task VALUES
    (1, 1, 'Купить хлеб', 0.5), (2, 1, 'Написать отчёт', 3),
    (3, 2, 'Позвонить врачу', 0.2), (4, 2, 'Собрать стенд', 4);

SELECT user_id, title, hours,
       ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY hours DESC) AS rn,
       SUM(hours) OVER (PARTITION BY user_id ORDER BY hours DESC) AS running_hours,
       CASE WHEN hours >= 1 THEN 'long' ELSE 'short' END AS kind
FROM task
ORDER BY user_id, rn;
-- 1 | Написать отчёт  | 3   | 1 | 3   | long
-- 1 | Купить хлеб     | 0.5 | 2 | 3.5 | short
-- 2 | Собрать стенд   | 4   | 1 | 4   | long
-- 2 | Позвонить врачу | 0.2 | 2 | 4.2 | short
```

## Как это работает

### CASE и фильтрация

#### CASE

`CASE` — выражение, а не управляющая инструкция; его можно применять в `SELECT`, `ORDER BY`, агрегатах, `WHERE`, `JOIN ... ON`, `UPDATE` и других выражениях.

```sql
SELECT salary,
       CASE
           WHEN salary >= 300000 THEN 'high'
           WHEN salary >= 150000 THEN 'middle'
           ELSE 'base'
       END AS salary_band
FROM employees;
```

Простая форма сравнивает одно выражение на равенство:

```sql
CASE status
    WHEN 'new' THEN 'Новый'
    WHEN 'done' THEN 'Готов'
    ELSE 'Другой'
END
```

Проверки идут сверху вниз, возвращается первая совпавшая ветка. Результаты веток должны приводиться к совместимому типу. Без `ELSE` возвращается `NULL`.

#### WHERE, HAVING и QUALIFY

| Оператор | Что фильтрует | Когда логически |
|---|---|---|
| `WHERE` | Исходные строки | До группировки и окон |
| `HAVING` | Сгруппированные результаты | После `GROUP BY` и агрегатов |
| `QUALIFY` | Результаты оконных функций | После вычисления окон |

`QUALIFY` есть, например, в BigQuery, Snowflake, ClickHouse и новых версиях некоторых СУБД, но **не поддерживается PostgreSQL**. Переносимый вариант — подзапрос:

```sql
SELECT *
FROM (
    SELECT e.*,
           ROW_NUMBER() OVER (
               PARTITION BY department_id
               ORDER BY salary DESC, id
           ) AS rn
    FROM employees e
) ranked
WHERE rn <= 3;
```

### Оконные функции

Оконная функция узнаётся по обязательному `OVER (...)`. В отличие от обычной агрегации, она **не схлопывает строки**: каждая исходная строка остаётся в результате.

```sql
SELECT id,
       department_id,
       salary,
       AVG(salary) OVER (PARTITION BY department_id) AS department_avg,
       ROW_NUMBER() OVER (
           PARTITION BY department_id
           ORDER BY salary DESC, id
       ) AS position
FROM employees;
```

Окно состоит из:

- `PARTITION BY` — делит результат на независимые секции;
- `ORDER BY` внутри `OVER` — задаёт порядок вычисления;
- frame — ограничивает строки относительно текущей строки.

#### Виды оконных функций

- ранжирование: `ROW_NUMBER`, `RANK`, `DENSE_RANK`, `NTILE`;
- доступ к соседним строкам: `LAG`, `LEAD`;
- доступ к значениям frame: `FIRST_VALUE`, `LAST_VALUE`, `NTH_VALUE`;
- агрегаты как окна: `SUM`, `AVG`, `COUNT`, `MIN`, `MAX`;
- распределения: `PERCENT_RANK`, `CUME_DIST`.

#### ROW_NUMBER, RANK и DENSE_RANK

Для значений `100, 100, 90`:

| Значение | `ROW_NUMBER` | `RANK` | `DENSE_RANK` |
|---:|---:|---:|---:|
| 100 | 1 | 1 | 1 |
| 100 | 2 | 1 | 1 |
| 90 | 3 | 3 | 2 |

- `ROW_NUMBER` всегда уникален; при равенстве порядок недетерминирован без дополнительного tie-breaker.
- `RANK` одинаков для peers и оставляет пропуски.
- `DENSE_RANK` одинаков для peers, но пропусков не оставляет.

#### Frame: ROWS, RANGE и GROUPS

```sql
SUM(amount) OVER (
    PARTITION BY account_id
    ORDER BY occurred_at, id
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
)
```

- `ROWS` считает физические позиции строк;
- `RANGE` работает со значением ключа сортировки и включает peers/диапазон значений;
- `GROUPS` считает группы равных ключей сортировки.

Границы: `UNBOUNDED PRECEDING`, `n PRECEDING`, `CURRENT ROW`, `n FOLLOWING`, `UNBOUNDED FOLLOWING`.

С `ORDER BY` frame по умолчанию обычно идёт от начала секции до текущей peer group. Поэтому `LAST_VALUE` нередко возвращает значение текущей строки, а не последней строки секции. Для всей секции задайте frame явно:

```sql
LAST_VALUE(salary) OVER (
    PARTITION BY department_id
    ORDER BY salary, id
    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
)
```

#### Практические применения

- top-N в каждой группе;
- накопительный итог и скользящее среднее;
- сравнение с предыдущей строкой через `LAG`;
- дедупликация с выбором самой свежей версии;
- доля строки в сумме группы;
- поиск последовательностей, разрывов и сессий.

## Частые ошибки

- Фильтр по оконной функции в `WHERE` (`WHERE ROW_NUMBER() OVER (...) = 1`) → ошибка «window functions are not allowed in WHERE» → вынести запрос в подзапрос или CTE и фильтровать по alias снаружи (в PostgreSQL нет `QUALIFY`).
- `ROW_NUMBER() OVER (ORDER BY hours DESC)` при равных `hours` → разные запуски дают разный «первый», тесты нестабильны → добавить уникальный tie-breaker: `ORDER BY hours DESC, id`.
- `LAST_VALUE(...) OVER (PARTITION BY ... ORDER BY ...)` без frame → возвращает значение текущей строки, а не последней в секции → указать `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING`.
- Накопительный итог через `SUM(...) OVER (ORDER BY occurred_at)` с повторяющимися датами → frame `RANGE` по умолчанию включает всех peers, итог «прыгает» на равных значениях → задать `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` и уникальный `ORDER BY`.
- `CASE` без `ELSE` в условии `WHERE` или в `SUM` → неучтённые ветки дают `NULL`, строки пропадают, суммы занижены → всегда писать `ELSE` или проверять, что `NULL` здесь ожидаем.

## Когда не использовать

Если нужен один итог на группу, а не итог рядом с каждой строкой, берите [`GROUP BY`](null_and_aggregation.md): результат меньше, план проще, и нет лишней сортировки всего набора. Для «есть ли у пользователя задачи» достаточно `EXISTS`, окно здесь не нужно.

Оконные функции по большим таблицам требуют сортировки и часто уходят в spill на диск; если тот же top-N или накопительный итог нужен в каждом запросе, его выгоднее считать заранее и хранить. `CASE` с десятком веток, повторяющийся в нескольких запросах, — повод вынести соответствие в справочную таблицу и присоединить её через `JOIN`.

## Связанные темы

- [NULL и агрегация](null_and_aggregation.md) — `GROUP BY`, `HAVING` и условная агрегация
- [Подзапросы, CTE и операции множеств](subqueries_and_sets.md) — подзапрос вместо `QUALIFY`
- [Основы SQL](basics.md) — порядок выполнения `SELECT`: почему окно считается после `WHERE`
