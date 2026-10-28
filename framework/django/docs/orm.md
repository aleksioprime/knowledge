# Django ORM

В Django к базе почти никогда не пишут SQL руками. Таблицы описываются классами-моделями, а запросы собираются цепочками методов: `Task.objects.filter(done=False).order_by('-priority')`. Это читается почти как обычная фраза и одинаково работает с SQLite, PostgreSQL и MySQL. Цена удобства — нужно понимать, *когда* ORM на самом деле идёт в базу, иначе один список легко превращается в сотню запросов.

Примеры выполнены в `python manage.py shell` на [учебном проекте](../example/README.md).

## Минимальный пример

```python
# tasks/models.py
from django.conf import settings
from django.db import models


class Task(models.Model):
    title = models.CharField('название', max_length=200)
    done = models.BooleanField('выполнена', default=False)
    priority = models.PositiveSmallIntegerField('приоритет', default=1)
    due_date = models.DateField('срок', null=True, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tasks')
    tags = models.ManyToManyField('Tag', blank=True, related_name='tasks')
    created_at = models.DateTimeField('создана', auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.title
```

```python
anna = User.objects.create_user('anna', password='secret123')
Task.objects.create(title='Сдать отчёт', owner=anna, priority=3)

Task.objects.filter(done=False).values_list('title', flat=True)
# <QuerySet ['Сдать отчёт']>
```

## Как это работает

**Модель** — таблица, **поле** — колонка. `id` Django добавляет сам. `null=True` разрешает `NULL` в базе, а `blank=True` — пустое значение в формах и админке. Обычно их ставят вместе.

**`objects`** — менеджер модели, с него начинается любой запрос. Результат — **QuerySet**: описание запроса, а не данные.

**QuerySet ленивый.** Пока вы строите цепочку, к базе нет ни одного обращения. Запрос уходит, только когда данные действительно нужны: при переборе, `list()`, `len()`, срезе или проверке в `if`:

```python
qs = Task.objects.filter(done=False).order_by('-priority')  # запросов: 0
print(qs.query)  # можно посмотреть SQL, который будет выполнен
# SELECT ... FROM "tasks_task" WHERE NOT "tasks_task"."done" ORDER BY "tasks_task"."priority" DESC

list(qs)
list(qs)  # запросов: 1 — результат первого вычисления закэширован в самом QuerySet
```

## Фильтры

Условия записываются как `поле__оператор=значение`. Двойное подчёркивание также переходит по связям:

```python
Task.objects.filter(title__icontains='отч')         # без учёта регистра
Task.objects.filter(due_date__year=2026)
Task.objects.filter(priority__gte=3)
Task.objects.filter(owner__username='anna')         # JOIN с таблицей пользователей
Task.objects.filter(tags__name='дом')               # JOIN через таблицу связи
Task.objects.exclude(done=True)                     # NOT
```

Несколько аргументов в `filter` — это И. Для ИЛИ и сложных условий есть `Q`:

```python
from django.db.models import Q

Task.objects.filter(Q(priority__gte=3) | Q(done=True))
```

## Получить один объект

```python
Task.objects.get(pk=1)                       # Task: Сдать отчёт
Task.objects.get(pk=999)                     # DoesNotExist: Task matching query does not exist.
Task.objects.get(owner__username='anna')     # MultipleObjectsReturned: get() returned more than one Task -- it returned 3!

Task.objects.filter(pk=999).first()          # None — без исключения
Tag.objects.get_or_create(name='срочно')     # (<Tag: срочно>, True), повторно — (<Tag: срочно>, False)
```

## Связи

```python
task = Task.objects.get(pk=1)
task.owner                 # пользователь через ForeignKey
task.tags.all()            # метки через ManyToMany
task.tags.add(home)        # добавить связь

anna.tasks.count()         # обратная связь по related_name='tasks'
```

`on_delete=models.CASCADE` — при удалении пользователя удаляются и его задачи. Другие варианты: `PROTECT` (запретить удаление), `SET_NULL` (обнулить ссылку, нужен `null=True`).

## Агрегация и выражения

```python
from django.db.models import Count, F

User.objects.annotate(n=Count('tasks')).values_list('username', 'n')
# [('admin', 1), ('anna', 3)] — к каждому пользователю добавлено поле n

Task.objects.aggregate(total=Count('id'), done=Count('id', filter=Q(done=True)))
# {'total': 4, 'done': 2} — одно значение на весь набор

Task.objects.filter(done=False).update(priority=F('priority') + 1)
# 2 — число изменённых строк
```

`F('priority')` ссылается на значение колонки **в базе**. Обновление `priority = priority + 1` выполняется одним SQL-запросом, и параллельные запросы не потеряют изменения — в отличие от «прочитать в Python, прибавить, сохранить».

## Проблема N+1: `select_related` и `prefetch_related`

Обращение к связи у каждого объекта в цикле — отдельный запрос. Посчитаем запросы для 4 задач, у которых мы читаем владельца и метки:

```python
for task in Task.objects.all():
    task.owner.username, [tag.name for tag in task.tags.all()]
```

| QuerySet | Запросов |
|---|---|
| `Task.objects.all()` | 9 — 1 за задачами + 4 за владельцами + 4 за метками |
| `.select_related('owner')` | 5 — владелец приходит через JOIN |
| `.select_related('owner').prefetch_related('tags')` | 2 — метки всех задач одним запросом `WHERE task_id IN (...)` |

- **`select_related`** — для связей «к одному» (`ForeignKey`, `OneToOne`): делает JOIN;
- **`prefetch_related`** — для связей «ко многим» (`ManyToMany`, обратные связи): отдельный запрос и склейка в Python.

На этом спотыкаются даже в маленьких проектах. В [примере](../example/tasks/views.py) сериализатор показывает `owner.username`, и тест с `assertNumQueries` сразу поймал 10 лишних запросов за пользователями. Исправление — одна строка:

```python
Task.objects.filter(owner=self.request.user).select_related('owner').prefetch_related('tags')
```

Защита на будущее — тест, который считает запросы:

```python
with self.assertNumQueries(3):
    self.client.get('/api/tasks/')
```

## Как увидеть SQL-запросы

`print(qs.query)` показывает один запрос. Чтобы найти N+1, нужно видеть все запросы, которые выполнил участок кода или целая страница.

**`connection.queries`** — список запросов текущего соединения. Django ведёт его только при `DEBUG = True`, иначе список всегда пуст:

```python
from django.db import connection, reset_queries

reset_queries()
for task in Task.objects.all():
    task.owner.username
len(connection.queries)    # 3 — для двух задач: 1 за задачами + 2 за владельцами
connection.queries[-1]
# {'sql': 'SELECT "auth_user"."id", ... FROM "auth_user" WHERE "auth_user"."id" = 1 LIMIT 21', 'time': '0.000'}
```

`reset_queries()` очищает список перед замером. В тестах удобнее `assertNumQueries` (выше) или `CaptureQueriesContext` из `django.test.utils`.

**Логгер `django.db.backends`** пишет каждый запрос в лог, удобно смотреть в консоли `runserver`:

```python
# config/settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_true': {'()': 'django.utils.log.RequireDebugTrue'},
    },
    'handlers': {
        'sql': {'class': 'logging.StreamHandler', 'filters': ['require_debug_true']},
    },
    'loggers': {
        'django.db.backends': {'handlers': ['sql'], 'level': 'DEBUG', 'propagate': False},
    },
}
```

```text
(0.001) SELECT COUNT(*) AS "__count" FROM "tasks_task" WHERE (NOT "tasks_task"."done" AND "tasks_task"."priority" >= 3); args=(3,); alias=default
```

В скобках — время запроса в секундах. Фильтр `RequireDebugTrue` выключает этот вывод при `DEBUG = False`. Впрочем, Django и сам пишет запросы в этот логгер только в режиме отладки.

**`django-debug-toolbar`** — панель поверх HTML-страниц, включая админку и страницы DRF в браузере. На вкладке SQL видны все запросы страницы, их время, `EXPLAIN` и пометки о похожих и повторяющихся запросах (similar, duplicated) — так N+1 видно сразу.

```bash
pip install django-debug-toolbar
```

```python
# config/settings.py
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    INTERNAL_IPS = ['127.0.0.1']
```

```python
# config/urls.py
from django.conf import settings

if settings.DEBUG:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns += debug_toolbar_urls()
```

Панель показывается только запросам с адресов из `INTERNAL_IPS`. В Docker запрос приходит не с `127.0.0.1`, а с адреса шлюза сети контейнеров, поэтому панель «молча» не появляется. Для чистого JSON-API без HTML панель бесполезна: там остаются логгер и `assertNumQueries`.

## Частые ошибки

- **Сохранение по чтению.** `task.priority += 1; task.save()` в двух параллельных запросах потеряет одно увеличение. Используйте `F()` или `update()`.
- **`save()` перезаписывает все поля.** Если два запроса меняют разные поля одного объекта, второй `save()` затрёт изменения первого. Указывайте, что сохранять: `task.save(update_fields=['done'])`.
- **`len(qs)` для подсчёта.** Загружает все объекты в память. Для количества — `qs.count()`, для проверки наличия — `qs.exists()`.
- **`update()` и `bulk_create()` не вызывают `save()`.** Логика в `save()` и сигналы `pre_save`/`post_save` при этом не срабатывают.
- **Фильтр по связи «ко многим» дублирует строки.** `Task.objects.filter(tags__name__in=['дом', 'срочно'])` вернёт задачу дважды, если у неё обе метки. Добавьте `.distinct()`.

## Связанные темы

- [Структура проекта](project.md)
- [Миграции](migrations.md)
- [Транзакции, массовые операции и сырой SQL](transactions.md)
- [Django REST Framework](drf.md)
- [SQLAlchemy: связи и N+1](../../../data/sqlalchemy/docs/relationships.md) — та же проблема в другом ORM
- [Потерянные обновления в PostgreSQL](../../../data/postgres/docs/tasks.ipynb)
