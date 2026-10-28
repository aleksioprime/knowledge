# Django: сигналы

Иногда нужно отреагировать на событие, не трогая код, который его порождает. Модель пользователя живёт в `django.contrib.auth`, и править её `save()` нельзя, а при регистрации нужно создать профиль. Приложение уведомлений хочет знать о новых задачах, но приложение задач не должно о нём знать. Сигналы — встроенная в Django шина событий: отправитель сообщает «задача сохранена», а подписчики, если они есть, реагируют.

Примеры выполнены на [учебном проекте](../example/README.md).

## Минимальный пример

```python
# tasks/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Task


@receiver(post_save, sender=Task)
def task_saved(sender, instance, created, **kwargs):
    if created:
        print(f'новая задача: {instance.title}')
```

```python
# tasks/apps.py
from django.apps import AppConfig


class TasksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tasks'
    verbose_name = 'Задачи'

    def ready(self):
        from . import signals  # noqa: F401
```

```python
task = Task.objects.create(title='Сдать отчёт', owner=anna)   # новая задача: Сдать отчёт
task.done = True
task.save()                                                   # ничего: created=False
```

## Как это работает

Сигнал — объект, на который подписываются функции-обработчики (receivers). Когда Django вызывает `post_save.send(...)`, он по очереди вызывает всех подписчиков с подходящим `sender`. `sender=Task` — подписка только на задачи; без него обработчик сработает на сохранение любой модели проекта.

**Аргументы.** Обработчик получает `sender` (класс модели) и именованные аргументы, у каждого сигнала свои: у `post_save` это `instance`, `created`, `update_fields`, `raw`, `using`. Всегда добавляйте `**kwargs`: Django может добавить новые аргументы, и обработчик без `**kwargs` сломается.

**Регистрация.** `@receiver` подключает функцию в момент импорта модуля. Если `signals.py` никто не импортирует, обработчиков просто нет, и ошибки тоже нет. Правильное место для импорта — `AppConfig.ready()`: он вызывается один раз, когда все приложения и модели загружены. Импорт в конце `models.py` встречается в старых проектах, но легко приводит к циклическим импортам. Импорт в `__init__.py` приложения падает с `AppRegistryNotReady: Apps aren't loaded yet.`

**Дубли.** Повторное подключение той же функции Django отбрасывает. Но если при каждом вызове создаётся новый объект функции (обработчик объявлен внутри другой функции, лямбда), подписки копятся:

```python
def connect_log():
    def log(sender, instance, **kwargs):
        print('лог', instance.title)
    post_save.connect(log, sender=Task, weak=False)

connect_log()
connect_log()
Task.objects.create(title='Дубль', owner=anna)
# лог Дубль
# лог Дубль
```

Защита — `dispatch_uid`, уникальная строка подписки. Второе подключение с той же строкой игнорируется:

```python
@receiver(post_save, sender=Task, dispatch_uid='tasks_notify_created')
```

## Основные сигналы

| Сигнал | Когда |
|---|---|
| `pre_save` / `post_save` | до и после `save()`; у `post_save` есть `created` |
| `pre_delete` / `post_delete` | до и после удаления объекта, в том числе каскадного |
| `m2m_changed` | изменение связи «многие ко многим»: `add`, `remove`, `clear` |
| `request_started` / `request_finished` | начало и конец обработки HTTP-запроса |
| `post_migrate` | после `migrate` для каждого приложения |

Модельные сигналы лежат в `django.db.models.signals`, сигналы запроса — в `django.core.signals`.

**`m2m_changed`** срабатывает дважды на каждое действие (`pre_add` и `post_add`), а `sender` у него — промежуточная таблица:

```python
@receiver(m2m_changed, sender=Task.tags.through)
def task_tags_changed(sender, instance, action, pk_set, **kwargs):
    if action == 'post_add':
        print(f'{instance.title}: добавлены метки {sorted(pk_set)}')


task.tags.add(work, urgent)   # Сдать отчёт: добавлены метки [2, 3]
```

**`post_migrate`** удобен для начальных данных, которые должны быть в любой базе. Подключают его прямо в `ready()`, с `sender=self`, чтобы обработчик срабатывал только после миграций своего приложения:

```python
# tasks/signals.py
def create_default_tags(sender, **kwargs):
    for name in ['дом', 'работа', 'срочно']:
        Tag.objects.get_or_create(name=name)


# tasks/apps.py
from django.db.models.signals import post_migrate


class TasksConfig(AppConfig):
    ...

    def ready(self):
        from . import signals

        post_migrate.connect(signals.create_default_tags, sender=self)
```

`migrate` вызывается многократно, поэтому обработчик должен быть идемпотентным: `get_or_create`, а не `create`.

## Сигналы синхронные

Несмотря на слово «сигнал», ничего не происходит в фоне. Обработчики выполняются сразу, в том же потоке и **в той же транзакции**, что и `save()`. Пока они работают, запрос пользователя ждёт.

Ошибка в обработчике — ошибка в `save()`:

```python
def broken(sender, instance, created, **kwargs):
    raise RuntimeError('почта недоступна')

post_save.connect(broken, sender=Task)

Task.objects.create(title='Без транзакции', owner=anna)    # RuntimeError: почта недоступна
with transaction.atomic():
    Task.objects.create(title='В транзакции', owner=anna)  # RuntimeError: почта недоступна

Task.objects.filter(title__in=['Без транзакции', 'В транзакции']).values_list('title', flat=True)
# <QuerySet ['Без транзакции']>
```

Без транзакции задача уже записана, но вызывающий код получил исключение и, скорее всего, вернул пользователю 500. Внутри `atomic` задача откатилась из-за упавшей отправки письма.

Поэтому долгую работу и внешние вызовы (письма, HTTP, очереди) из обработчика не выполняют напрямую. Откладывают до коммита и отдают в очередь:

```python
from django.db import transaction


@receiver(post_save, sender=Task, dispatch_uid='tasks_notify_created')
def notify_task_created(sender, instance, created, **kwargs):
    if created:
        transaction.on_commit(lambda: send_task_created_email.delay(instance.pk))
```

Если вместо Celery подставить функцию, которая печатает `письмо о задаче {pk}`, видно, что она вызывается только после выхода из блока:

```python
with transaction.atomic():
    task = Task.objects.create(title='Сдать отчёт', owner=anna)
    print('коммита ещё не было')
# коммита ещё не было
# письмо о задаче 1
```

Подробнее про `on_commit` — в заметке о [транзакциях](transactions.md#transactionon_commit--действие-после-коммита), про очередь — в [Celery](../../celery/README.md).

## Частые ошибки

- **Обработчик не срабатывает.** Модуль `signals.py` не импортирован в `ready()`, или в `INSTALLED_APPS` указано `'tasks'`, а `ready()` написан в другом классе конфигурации.
- **Рекурсия.** `instance.save()` внутри `post_save` снова отправляет `post_save`, и так до `RecursionError: maximum recursion depth exceeded`. Если нужно обновить поле, используйте `Task.objects.filter(pk=instance.pk).update(...)`: `update()` сигналов не шлёт.
- **Ожидание сигнала от массовых операций.** `QuerySet.update()`, `bulk_create()` и `bulk_update()` не вызывают `save()`, поэтому `pre_save`/`post_save` не приходят. `QuerySet.delete()`, наоборот, отправляет `pre_delete`/`post_delete` для каждого объекта, и ради этого Django сначала загружает их в память.
- **Расчёт на порядок обработчиков.** Обработчики вызываются в порядке подключения, а он зависит от порядка приложений в `INSTALLED_APPS` и импортов. Если обработчику B нужен результат обработчика A, это не два сигнала, а одна функция.
- **Тяжёлая работа в обработчике.** Отправка письма или запрос во внешний API прямо в `post_save` замедляет каждый `save()` и может откатить транзакцию. Только `on_commit` и очередь.

## Когда не использовать

Сигналы делают связь **неявной**. Читая `create_task()`, не видно, что после неё уходит письмо, обновляется счётчик и пишется аудит-лог: это разбросано по `signals.py` разных приложений. Отлаживать такую цепочку тяжело, а тесты внезапно начинают слать письма.

Если и событие, и реакция — в вашем коде, вызовите реакцию явно:

```python
# tasks/services.py
def create_task(owner, title):
    task = Task.objects.create(owner=owner, title=title)
    transaction.on_commit(lambda: send_task_created_email.delay(task.pk))
    return task
```

Сигналы оправданы, когда вы не можете изменить отправителя (модели Django и сторонних пакетов, `post_migrate`) или когда реакция действительно принадлежит другому приложению, и вы не хотите, чтобы приложение задач зависело от приложения уведомлений.

## Связанные темы

- [Транзакции, массовые операции и сырой SQL](transactions.md) — `on_commit`, `bulk_create`
- [ORM](orm.md)
- [Структура проекта](project.md) — приложения и `AppConfig`
- [Celery](../../celery/README.md)
