# Django: транзакции, массовые операции и сырой SQL

По умолчанию Django работает в режиме автокоммита: каждый `save()` или `create()` фиксируется в базе сразу. Пока действие — одна строка, этого хватает. Но «создать задачу и навесить на неё метки» — уже несколько запросов, и если третий упадёт, в базе останется задача без меток. Для таких случаев есть транзакции. А когда строк тысячи, а ORM выражает запрос неудобно, пригодятся массовые операции и сырой SQL.

Примеры выполнены в `python manage.py shell` на [учебном проекте](examples/README.md) (SQLite). То, что работает только на PostgreSQL, отмечено отдельно.

## Минимальный пример

```python
from django.db import transaction

from tasks.models import Tag, Task


@transaction.atomic
def create_task_with_tags(owner, title, tag_names):
    task = Task.objects.create(title=title, owner=owner)
    for name in tag_names:
        tag, _ = Tag.objects.get_or_create(name=name)
        task.tags.add(tag)
    if not tag_names:
        raise ValueError('нужна хотя бы одна метка')
    return task


create_task_with_tags(anna, 'Без меток', [])     # ValueError: нужна хотя бы одна метка
Task.objects.filter(title='Без меток').count()   # 0 — задача создалась, но откатилась
```

## `transaction.atomic`

`atomic` открывает транзакцию: если блок завершился нормально — `COMMIT`, если вылетело исключение — `ROLLBACK`, и исключение летит дальше. Работает как декоратор (вся функция — одна транзакция) и как контекстный менеджер:

```python
with transaction.atomic():
    task = Task.objects.create(title='Сдать отчёт', owner=anna)
    task.tags.add(home)
```

Откат касается только базы. Python-объекты остаются как были: у `task` после отката по-прежнему есть `pk`, хотя строки в базе уже нет.

Ловить исключение нужно **снаружи** блока `atomic`, а не внутри. Если поймать ошибку базы внутри блока и продолжить запросы, следующий упадёт: `TransactionManagementError: An error occurred in the current transaction. You can't execute queries until the end of the 'atomic' block.` Транзакция уже сломана, и Django не даёт делать вид, что всё в порядке.

### Вложенный `atomic` — точка сохранения

Внутренний `atomic` не открывает новую транзакцию, а создаёт точку сохранения (savepoint). Ошибка во внутреннем блоке откатывает только его:

```python
with transaction.atomic():
    Task.objects.create(title='Сдать отчёт', owner=anna)
    try:
        with transaction.atomic():
            Task.objects.create(title='Черновик', owner=anna)
            raise ValueError
    except ValueError:
        pass

Task.objects.values_list('title', flat=True)    # <QuerySet ['Сдать отчёт']>
```

SQL, который ушёл в базу:

```text
BEGIN
INSERT INTO "tasks_task" ...                  -- Сдать отчёт
SAVEPOINT "s8357822336_x1"
INSERT INTO "tasks_task" ...                  -- Черновик
ROLLBACK TO SAVEPOINT "s8357822336_x1"
RELEASE SAVEPOINT "s8357822336_x1"
COMMIT
```

Так удобно делать «попробовать и при неудаче продолжить»: например, импорт, где одна битая строка не должна отменять весь файл.

## `select_for_update` — блокировка строк

Две вкладки одновременно меняют одну задачу: обе прочитали, обе изменили, вторая затёрла первую. `F()` и `update()` из [ORM](orm.md#агрегация-и-выражения) решают это для простой арифметики. Если же решение принимается в Python (проверить статус, посчитать, записать), строку блокируют на время транзакции:

```python
with transaction.atomic():
    task = Task.objects.select_for_update().get(pk=task_id)   # SELECT ... FOR UPDATE
    if not task.done:
        task.priority = 5
        task.save(update_fields=['priority'])
```

Второй такой же запрос будет ждать, пока первая транзакция не закончится, и прочитает уже новое значение. Проверено на PostgreSQL: поток держал блокировку 2 секунды, второй запрос ждал `2.0 с` и увидел `priority = 5`.

Тонкости:

- **Только внутри `atomic`.** Вне транзакции — `TransactionManagementError: select_for_update cannot be used outside of a transaction.` (на PostgreSQL). SQLite не умеет `FOR UPDATE` и просто игнорирует вызов, поэтому на SQLite ни ошибки, ни блокировки не будет.
- **С `select_related` блокируются все таблицы JOIN.** `select_for_update().select_related('owner')` заблокирует и задачу, и строку пользователя. Чтобы заблокировать только задачу, укажите `of`:

  ```python
  Task.objects.select_for_update(of=('self',)).select_related('owner').get(pk=task_id)
  # ... FOR UPDATE OF "tasks_task"
  ```

- **`nowait=True`** — не ждать, а сразу упасть: `OperationalError: could not obtain lock on row in relation "tasks_task"`.
- **`skip_locked=True`** — пропустить занятые строки. Если строка занята, вернётся пустой список. Так строят очередь задач в базе: несколько воркеров берут разные строки и не мешают друг другу.

## `transaction.on_commit` — действие после коммита

Письмо «задача создана» нельзя отправлять внутри транзакции: если она откатится, письмо уже ушло, а задачи нет. Ещё коварнее задача Celery: воркер может взять её раньше, чем транзакция закоммитится, и не найти задачу в базе. `on_commit` откладывает вызов до успешного коммита:

```python
with transaction.atomic():
    task = Task.objects.create(title='Позвонить', owner=anna)
    transaction.on_commit(lambda: print('письмо о задаче', task.pk))
    print('ещё в транзакции')
print('после блока')
# ещё в транзакции
# письмо о задаче 2
# после блока
```

При откате функция не вызывается вовсе. Вне транзакции (в режиме автокоммита) — вызывается сразу. В реальном коде вместо `print` — постановка задачи в очередь:

```python
transaction.on_commit(lambda: send_task_created_email.delay(task.pk))
```

В очередь передают `pk`, а не объект: воркер сам прочитает свежую версию из базы.

## Массовые операции

Создавать тысячу задач циклом с `create()` — тысяча `INSERT`. `bulk_create` вставляет их пачками:

```python
tasks = Task.objects.bulk_create(
    [Task(title=f'Задача {i}', owner=anna) for i in range(1000)],
    batch_size=500,
)
```

На PostgreSQL это 2 запроса `INSERT` по 500 строк. На SQLite — 7: у SQLite ограничение на число параметров в запросе, и Django сам дробит пачки мельче. `batch_size` нужен, чтобы один запрос не вырос до гигантских размеров. `pk` у созданных объектов заполнен на PostgreSQL и на современных SQLite, а на MySQL — нет.

`bulk_update` обновляет уже загруженные объекты одним запросом с `CASE WHEN`:

```python
for task in tasks[:3]:
    task.priority = 5
    task.done = True

Task.objects.bulk_update(tasks[:3], fields=['priority', 'done'])   # 3 — число строк
# UPDATE "tasks_task" SET "priority" = CASE WHEN ("tasks_task"."id" = 2) THEN 5 ... END, "done" = CASE ...
```

Если новое значение одинаковое для всех, проще `Task.objects.filter(...).update(priority=5)` — запрос короче.

**`bulk_create`, `bulk_update` и `update` не вызывают `save()` и не отправляют сигналы** `pre_save`/`post_save`. После `bulk_create` на тысячу задач обработчик `post_save` не вызвался ни разу. Если в `save()` или в [сигналах](signals.md) есть логика (заполнение полей, уведомления), при массовых операциях её нужно выполнить самому.

## Сырой SQL

ORM покрывает большинство запросов, но иногда SQL проще написать руками: отчёт с оконными функциями, специфичная для базы конструкция.

### `Model.objects.raw()`

Выполняет SQL и превращает строки в объекты модели:

```python
for task in Task.objects.raw('SELECT id, title FROM tasks_task WHERE priority >= %s', [5]):
    print(task.title, task.done)
# Задача 0 True
# Задача 1 True
# Задача 2 True
```

- **Первичный ключ обязателен.** Без `id` в `SELECT` — `FieldDoesNotExist: Raw query must include the primary key`.
- **Невыбранные поля загружаются отдельно.** В запросе нет `done`, поэтому каждое обращение к `task.done` — ещё один запрос. Выше вышло 4 запроса вместо одного. Выбирайте в `SELECT` всё, что будете читать.

### `connection.cursor()`

Когда результат не ложится на модель (агрегаты, произвольные колонки):

```python
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute(
        'SELECT owner_id, COUNT(*) FROM tasks_task WHERE done = %s GROUP BY owner_id',
        [False],
    )
    cursor.fetchall()    # [(1, 997)]
```

Значения передают **только через параметры `%s`**, драйвер сам их экранирует. Плейсхолдер `%s` одинаковый для всех баз, даже для SQLite, у которой в обычном Python-драйвере `?`. Кавычки вокруг `%s` не ставят.

Подставлять значения f-строкой — SQL-инъекция:

```python
title = "x' OR '1'='1"

Task.objects.raw('SELECT id, title FROM tasks_task WHERE title = %s', [title])     # 0 строк
cursor.execute(f"SELECT COUNT(*) FROM tasks_task WHERE title = '{title}'")         # (1000,) — все задачи
```

### Своя SQL-функция через `Func`

Часто сырой SQL не нужен целиком: не хватает одной функции базы. Её можно подключить к ORM и пользоваться в `annotate`, `filter` и `update`.

Задачи пришли из импорта с маркерами в начале: `'— Сдать отчёт'`, `'* * Купить хлеб'`. Встроенный `LTrim` убирает только пробелы, а SQL-функция `LTRIM(строка, символы)` умеет убирать заданные символы. Она есть и в SQLite, и в PostgreSQL:

```python
from django.db.models import F, Func, Value


class LTrimChars(Func):
    function = 'LTRIM'


qs = Task.objects.filter(title__regex=r'^[-—* ]')
qs.annotate(clean=LTrimChars(F('title'), Value('-—* '))).values_list('clean', flat=True)
# <QuerySet ['Сдать отчёт', 'Купить хлеб']>

qs.update(title=LTrimChars(F('title'), Value('-—* ')))   # 2
```

`Func` подставляет аргументы через запятую: `LTRIM("tasks_task"."title", %s)`. Значения оборачивают в `Value`, чтобы они ушли параметром, а не именем колонки.

Функции, которых нет в SQLite, работают только на своей базе. Например, `regexp_replace` в PostgreSQL сжимает повторяющиеся пробелы:

```python
class RegexpReplace(Func):
    function = 'REGEXP_REPLACE'


Task.objects.annotate(clean=RegexpReplace(F('title'), Value(r'\s+'), Value(' '), Value('g')))
# 'Сдать   отчёт  до   пятницы' → 'Сдать отчёт до пятницы'
# на SQLite: OperationalError: no such function: REGEXP_REPLACE
```

## Частые ошибки

- **Внешний вызов внутри транзакции.** HTTP-запрос, письмо или постановка задачи в Celery внутри `atomic` держат транзакцию открытой и не откатываются вместе с ней. Выносите их в `on_commit`.
- **`select_for_update` проверили только на SQLite.** Тесты зелёные, а блокировки нет: SQLite её игнорирует. Конкурентный код проверяйте на той же базе, что в продакшене.
- **Длинная транзакция с блокировкой.** Пока строка заблокирована, все желающие её изменить ждут. Внутри `atomic` с `select_for_update` — только работа с базой, без сети и тяжёлых вычислений.
- **`try/except` вокруг запроса внутри `atomic`.** Ошибка базы поймана, но транзакция уже сломана, и следующий запрос падает с `TransactionManagementError`. Оборачивайте рискованную часть во вложенный `atomic` или ловите исключение снаружи.
- **Ожидание сигналов от `bulk_create`.** Обработчик `post_save` не вызовется. Это не баг, а цена скорости.
- **f-строка в SQL.** Только параметры `%s`, даже если «значение же наше, а не от пользователя».

## Связанные темы

- [ORM](orm.md) — `F()`, `update()` и проблема N+1
- [Сигналы](signals.md)
- [Миграции](migrations.md) — `RunSQL` и `RunPython`
- [Транзакции и уровни изоляции в PostgreSQL](../../databases/postgres/transaction.md); очередь на `SKIP LOCKED` — в [практических задачах](../../databases/postgres/tasks.md)
- [Celery](../celery/README.md) — фоновые задачи, которые ставят из `on_commit`
- [Быстрая загрузка данных в PostgreSQL](../../databases/postgres/bulk_load.md) — когда `bulk_create` мало: `COPY` и замеры
- [Распределённые транзакции: Saga и Outbox](../../design/transactions.md) — когда одной базы мало
