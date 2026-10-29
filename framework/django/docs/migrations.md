# Django: миграции

`makemigrations` и `migrate` хватает, пока проект живёт на одном ноутбуке. Потом появляются продакшен-база с миллионом строк, вторая ветка с соседней миграцией и база, созданная до Django SQL-скриптом. Тут уже нужно понимать, что лежит в файле миграции, как Django помнит, что он применил, и какой SQL на самом деле уйдёт в базу.

Основы — создание и применение — описаны в [структуре проекта](project.md#миграции). Примеры выполнены на [учебном проекте](../example/README.md): на SQLite, а то, что зависит от базы, — на PostgreSQL 16.

## Минимальный пример

Добавим задаче статус и сразу дадим миграции понятное имя:

```python
# tasks/models.py
class Task(models.Model):
    ...
    status = models.CharField(
        'статус', max_length=20, default='new',
        choices=[('new', 'Новая'), ('in_progress', 'В работе'), ('done', 'Готова')],
    )
```

```bash
python manage.py makemigrations tasks --name task_status
# Migrations for 'tasks':
#   tasks/migrations/0002_task_status.py
#     + Add field status to task

python manage.py sqlmigrate tasks 0002     # какой SQL будет выполнен (на PostgreSQL)
# BEGIN;
# ALTER TABLE "tasks_task" ADD COLUMN "status" varchar(20) DEFAULT 'new' NOT NULL;
# ALTER TABLE "tasks_task" ALTER COLUMN "status" DROP DEFAULT;
# COMMIT;

python manage.py showmigrations tasks
# tasks
#  [X] 0001_initial
#  [ ] 0002_task_status

python manage.py migrate tasks
```

Без `--name` Django придумает имя сам (`0002_task_status`, `0003_alter_task_priority_and_more`). Через полгода по такому имени не поймёшь, что делает миграция. Своё имя — `--name add_task_status`, `--name fill_status_from_done` — работает как заголовок коммита.

## Как устроен файл миграции

```python
# tasks/migrations/0002_task_status.py
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='status',
            field=models.CharField(choices=[...], default='new', max_length=20, verbose_name='статус'),
        ),
    ]
```

- **`dependencies`** — какие миграции должны быть применены раньше. Обычно это предыдущая миграция приложения, но бывают и чужие: `0001_initial` задач зависит от модели пользователя (`swappable_dependency(settings.AUTH_USER_MODEL)`).
- **`operations`** — список изменений: `CreateModel`, `AddField`, `AlterField`, `RenameField`, `AddIndex`, `RunSQL`, `RunPython` и другие. Это не SQL, а описание изменения схемы: SQL под конкретную базу Django строит при применении.
- **`run_before`** — обратная зависимость: «эта миграция должна выполниться раньше вон той, в другом приложении». Нужна редко, например когда вы не можете править миграцию стороннего пакета, но ей нужна ваша таблица.

Из `dependencies` всех приложений Django строит граф и применяет миграции в порядке, который этот граф допускает.

## Таблица `django_migrations`

Что уже применено, Django хранит в самой базе:

```sql
SELECT app, name FROM django_migrations WHERE app = 'tasks';
-- tasks|0001_initial
-- tasks|0002_task_status
```

`migrate` сравнивает файлы с этой таблицей и выполняет только те, которых в ней нет. Содержимое файла при этом не проверяется. Отсюда главная ловушка: **правка уже применённой миграции в базу не попадёт.** Поменяли в `0002_task_status.py` `max_length=20` на `30` — `migrate` ответит `No migrations to apply`, колонка останется `varchar(20)`. А `makemigrations` ещё и создаст `0003_alter_task_status`, потому что модели и миграции теперь расходятся.

Правило: применённую миграцию (особенно ту, что уже ушла на сервер или к коллегам) не трогают. Нужно изменение — новая миграция.

## Откат

```bash
python manage.py migrate tasks 0001      # откатить всё после 0001
# Unapplying tasks.0002_task_status... OK

python manage.py migrate tasks zero      # откатить все миграции приложения
# Unapplying tasks.0001_initial... OK
```

Откат выполняет обратные операции: для `AddField` — удаление колонки (вместе с данными в ней), для `CreateModel` — удаление таблицы. Посмотреть SQL отката можно заранее: `sqlmigrate tasks 0002 --backwards`.

## `--fake` и существующая база

`--fake` записывает миграцию в `django_migrations`, ничего не выполняя в базе. Это способ сказать Django: «это уже сделано, не трогай».

Типичный случай — база уже существует: её создали SQL-скриптом или раньше вела другая система, а таблицы совпадают с моделями. Обычный `migrate` упадёт на первой же таблице:

```bash
python manage.py migrate tasks
# django.db.utils.ProgrammingError: relation "tasks_tag" already exists

python manage.py migrate tasks --fake-initial
# Applying tasks.0001_initial... FAKED
# Applying tasks.0002_task_status... OK
```

`--fake-initial` помечает начальную миграцию применённой, только если все её таблицы уже есть в базе, а следующие выполняет по-настоящему. `--fake` без условий помечает всё, что вы укажете, — им же можно «откатить» запись без изменения схемы (`migrate tasks 0003 --fake`). Пользуйтесь им, только если точно знаете, что схема совпадает: иначе Django будет считать, что колонка есть, а её нет.

### Чужие таблицы: `inspectdb` и `managed = False`

Если таблицей владеет кто-то другой (другой сервис, DBA, legacy-система), а Django должен её только читать и писать, модель можно сгенерировать:

```bash
python manage.py inspectdb task_archive
```

```python
class TaskArchive(models.Model):
    title = models.CharField(max_length=200)
    closed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'task_archive'
```

`managed = False` значит: миграция для модели создаётся (`+ Create model TaskArchive`), но схему Django не меняет — `sqlmigrate` покажет `-- (no-op)`. Запросы через ORM при этом работают как обычно. Вывод `inspectdb` — черновик: проверьте типы, связи и `on_delete`.

## Свои миграции: `RunPython` и `RunSQL`

Не всё описывается изменением модели. Перенос данных или SQL, которого ORM не умеет, кладут в пустую миграцию:

```bash
python manage.py makemigrations tasks --empty --name fill_status
```

**`RunPython`** — миграция данных. Заполним статус выполненных задач:

```python
from django.db import migrations


def forwards(apps, schema_editor):
    Task = apps.get_model('tasks', 'Task')
    Task.objects.filter(done=True).update(status='done')


def backwards(apps, schema_editor):
    Task = apps.get_model('tasks', 'Task')
    Task.objects.filter(status='done').update(done=True)


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0002_task_status'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
```

Модель берут через `apps.get_model`, а не `from tasks.models import Task`. `apps` — это модели в том виде, в каком они были **на момент этой миграции**. Импорт даёт текущую модель: через год в ней появится поле, которого на шаге `0003` ещё нет в базе, и старая миграция упадёт на чистой базе. По той же причине в миграции недоступны собственные методы модели и логика из `save()`.

Вторая функция нужна для отката. Без неё `migrate tasks 0002` упадёт с `IrreversibleError: Operation <RunPython ...> is not reversible`. Если откатывать нечего, передайте `migrations.RunPython.noop`.

**`RunSQL`** — сырой SQL, тоже с обратным действием:

```python
operations = [
    migrations.RunSQL(
        'CREATE EXTENSION IF NOT EXISTS pg_trgm',
        reverse_sql='DROP EXTENSION IF EXISTS pg_trgm',
    ),
]
```

## Конфликт двух веток

Вы в своей ветке добавили `0005_task_note`, коллега в своей — `0005_tag_color`. Обе зависят от `0004`. После слияния веток в графе две «последние» миграции:

```bash
python manage.py migrate
# CommandError: Conflicting migrations detected; multiple leaf nodes in the migration graph:
# (0005_tag_color, 0005_task_note in tasks).
# To fix them run 'python manage.py makemigrations --merge'

python manage.py makemigrations --merge
# Created new merge migration .../0006_merge_0005_tag_color_0005_task_note.py
```

Миграция слияния пустая: в `dependencies` у неё обе ветки, `operations = []`. Если ветки меняют разные поля, этого достаточно. Если одно и то же поле — `--merge` не поможет, разбирайтесь руками: удалите свою миграцию, подтяните чужую и пересоздайте свою поверх.

## Ловушки

**`choices` не создают ограничение в базе.** В `sqlmigrate` выше нет никакого `CHECK`: статус проверяется только в формах, админке, сериализаторах и `full_clean()`. `Task.objects.create(status='archived')` или `update(status='ghost')` спокойно запишут мусор. То же с `MaxValueValidator`: у `priority` в базе есть только `CHECK ("priority" >= 0)` от `PositiveSmallIntegerField`, а ограничения «не больше 5» нет. Если значение должна гарантировать база, добавьте ограничение явно:

```python
class Meta:
    constraints = [
        models.CheckConstraint(
            condition=models.Q(status__in=['new', 'in_progress', 'done']),
            name='task_status_valid',
        ),
    ]
```

```bash
python manage.py sqlmigrate tasks 0004
# ALTER TABLE "tasks_task" ADD CONSTRAINT "task_status_valid" CHECK ("status" IN ('new', 'in_progress', 'done'));
```

```python
Task.objects.update(status='ghost')
# IntegrityError: new row for relation "tasks_task" violates check constraint "task_status_valid"
```

Параметр называется `condition` с Django 5.1, раньше был `check`.

**Переименование может стать удалением.** Переименуем `due_date` в `deadline`. Если определение поля не изменилось, Django спросит:

```text
Was task.due_date renamed to task.deadline (a DateField)? [y/N]
```

Ответ `y` даёт `RenameField` — колонка переименовывается, данные целы. Но если вы заодно поменяли хоть что-то ещё, например `verbose_name`, вопроса не будет:

```text
- Remove field due_date from task
+ Add field deadline to task
```

Это удаление колонки со всеми сроками и создание пустой. То же произойдёт при `--noinput` в CI. Обратная ситуация — `AlterField`, который тихо меняет смысл колонки (тип, единицы измерения) при сохранении старых значений. Поэтому перед коммитом **читайте `operations`** в созданном файле, а для опасных случаев — `sqlmigrate`. Переименование и другие изменения делайте разными миграциями.

**Создание индекса блокирует запись.** Обычный `CREATE INDEX` в PostgreSQL на время построения запрещает `INSERT`/`UPDATE`/`DELETE` в таблицу. На большой таблице это минуты простоя. Для продакшена индекс строят конкурентно:

```python
from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('tasks', '0004_task_status_check'),
    ]

    operations = [
        AddIndexConcurrently(
            model_name='task',
            index=models.Index(fields=['owner', 'status'], name='task_owner_status_idx'),
        ),
    ]
```

```bash
python manage.py sqlmigrate tasks 0005
# CREATE INDEX CONCURRENTLY "task_owner_status_idx" ON "tasks_task" ("owner_id", "status");
```

`makemigrations` создаст обычный `AddIndex` — замените его руками, индекс в `Meta.indexes` модели оставьте. `CONCURRENTLY` нельзя выполнять внутри транзакции, а Django оборачивает каждую миграцию в транзакцию. `atomic = False` это отключает, без него будет `NotSupportedError: The AddIndexConcurrently operation cannot be executed inside a transaction`. Такую миграцию лучше держать отдельно от остальных операций: при ошибке на середине откатывать будет нечем.

## Частые ошибки

- **Миграции в `.gitignore`.** Каждый разработчик генерирует свои, имена и порядок расходятся, на сервере непонятно, что применено. Миграции — часть кода: коммитят вместе с изменением модели и проходят ревью.
- **Правка или удаление применённой миграции.** Схема в базе и в файлах расходится, следующий `migrate` падает или молча ничего не делает. Делайте новую миграцию.
- **Импорт модели в `RunPython`.** Работает сегодня и ломается через пару изменений модели. Только `apps.get_model`.
- **Нет обратной операции.** `RunPython(forwards)` без второй функции не откатывается, и `migrate app 0003` перед откатом релиза не сработает.
- **Забыли проверить, что миграции созданы.** Модель поменяли, миграцию не сделали — на сервере колонки нет. В CI добавьте `python manage.py makemigrations --check --dry-run`: при несозданных миграциях команда завершится с ошибкой.

## Связанные темы

- [Структура проекта](project.md) — базовые команды `makemigrations` и `migrate`
- [ORM](orm.md)
- [Транзакции, массовые операции и сырой SQL](transactions.md)
- [Alembic](../../../data/alembic/README.md) — миграции для SQLAlchemy
- [PostgreSQL](../../../data/postgres/README.md) — индексы и блокировки; смена типа колонки без простоя — в [практических задачах](../../../data/postgres/docs/tasks.md)
