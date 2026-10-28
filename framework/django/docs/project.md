# Django: структура проекта

В FastAPI структуру проекта придумываете вы сами. Django, наоборот, сразу даёт готовый каркас и договорённости: где лежат модели, где настройки, как подключаются URL. Новичку поначалу кажется, что файлов слишком много, но через неделю любой Django-проект читается одинаково — и это главное достоинство подхода «всё включено».

Пример — в папке [example](../example/README.md).

## Минимальный пример

```bash
pip install "django==5.2.*"
django-admin startproject config .
python manage.py startapp tasks
python manage.py migrate
python manage.py runserver
```

```text
.
├── manage.py            # точка входа для всех команд
├── config/              # проект: настройки и корневые URL
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
└── tasks/               # приложение: одна область предметной логики
    ├── admin.py
    ├── apps.py
    ├── migrations/
    ├── models.py
    ├── tests.py
    └── views.py
```

Точка в конце `startproject config .` важна: без неё Django создаст ещё одну вложенную папку `config/config/`.

## Проект и приложения

**Проект** (`config/`) — это настройки и корневой список URL. Обычно его называют `config` или по имени продукта.

**Приложение** (`tasks/`) — модуль с моделями, представлениями, админкой и тестами для одной части предметной области: задачи, пользователи, платежи. Приложение нужно добавить в настройки, иначе Django не увидит его модели:

```python
# config/settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    ...,
    'rest_framework',
    'tasks',
]
```

Встроенные `django.contrib.*` — это тоже приложения: админка, пользователи и права, сессии.

## Как Django обрабатывает запрос

1. **URL** — `config/urls.py` сопоставляет путь с представлением. Части путей можно делегировать приложениям через `include`:

   ```python
   urlpatterns = [
       path('admin/', admin.site.urls),
       path('api/', include('tasks.urls')),
   ]
   ```

2. **Middleware** — цепочка обработчиков вокруг каждого запроса: сессии, CSRF, аутентификация (список `MIDDLEWARE` в настройках).
3. **Представление** (view) — функция или класс, который получает запрос и возвращает ответ.
4. **Модель** — представление обращается к базе через ORM.

Django называет свою схему **MTV** (Model — Template — View): шаблоны (Template) нужны, если сервер сам отдаёт HTML. Для API шаблоны не нужны, а вместо них ответ формирует [Django REST Framework](drf.md).

## Настройки

```python
# config/settings.py
import os

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-only-insecure-key')
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'

LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
```

`startproject` вписывает в `settings.py` случайный `SECRET_KEY` и `DEBUG = True`. Для учебного проекта это удобно, но в репозиторий такие значения попадать не должны. Выносите их в переменные окружения. `LANGUAGE_CODE = 'ru-ru'` переводит на русский админку и сообщения об ошибках:

```json
{"title": ["Это поле не может быть пустым."], "priority": ["Убедитесь, что это значение меньше либо равно 5."]}
```

### `DEBUG` и `ALLOWED_HOSTS`

Переменные окружения — всегда строки. Частая ошибка:

```python
DEBUG = os.environ.get('DEBUG', False)
# DEBUG=False в окружении → 'False' → непустая строка → истина
```

Сервер запущен с `DEBUG=False`, а Django работает в отладочном режиме и показывает трассировки посетителям. Сравнивайте строку явно, как в примере выше: `os.environ.get('DJANGO_DEBUG', '1') == '1'`.

`ALLOWED_HOSTS` — список доменов, на которые сервер готов отвечать (проверяется заголовок `Host`). При `DEBUG = True` и пустом списке разрешены только `localhost`, `127.0.0.1` и `[::1]`. При `DEBUG = False` пустой список ничего не разрешает: `runserver` не запустится (`CommandError: You must set settings.ALLOWED_HOSTS if DEBUG is False.`), а запрос с чужим `Host` получит `400 Bad Request`. Значение тоже берут из окружения: `ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')`.

## Настройки в нескольких файлах

Один `settings.py` к середине проекта вырастает до сотен строк: база, DRF, логирование, Celery, кэш. А разработке, тестам и продакшену нужны разные значения. Есть два распространённых подхода.

**Пакет `settings/` с наследованием.** Общие настройки — в `base.py`, окружения импортируют их и переопределяют нужное:

```text
config/settings/
├── __init__.py
├── base.py
├── dev.py      # from .base import *  и  DEBUG = True
└── prod.py     # from .base import *  и  DEBUG = False, ALLOWED_HOSTS = [...]
```

Нужный файл выбирают переменной `DJANGO_SETTINGS_MODULE=config.settings.prod`. Подход простой, но звёздочный импорт прячет, откуда взялась настройка, и разнести по файлам *темы* (база отдельно, DRF отдельно) так неудобно.

**`django-split-settings`.** Настройки делят по темам, а `__init__.py` склеивает их, как если бы это был один файл:

```python
# config/settings/__init__.py
from pathlib import Path

from dotenv import load_dotenv
from split_settings.tools import include, optional

load_dotenv(Path(__file__).resolve().parents[2] / '.env')

include(
    'components/base.py',
    'components/database.py',
    'components/drf.py',
    'components/logging.py',
    optional('local.py'),
)
```

```python
# config/settings/components/database.py
import os

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'tasks'),
        'USER': os.environ.get('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}
```

- Файлы выполняются по порядку в общем пространстве имён: компонент может читать и дополнять то, что объявлено выше (`if DEBUG: INSTALLED_APPS += [...]`).
- `.env` загружают **до** `include`, иначе компоненты прочитают пустое окружение и возьмут значения по умолчанию.
- `optional('local.py')` подключает файл, только если он есть: личные настройки разработчика, которые не попадают в git.
- `__file__` внутри компонента указывает на `settings/__init__.py`, а не на сам компонент. Поэтому `BASE_DIR = Path(__file__).resolve().parents[2]` в `components/base.py` даёт корень проекта.
- Пути в `include` считаются от папки `__init__.py`.

## Команды `manage.py`

```bash
python manage.py runserver            # сервер для разработки на :8000
python manage.py makemigrations       # создать миграции по изменениям моделей
python manage.py migrate              # применить миграции
python manage.py createsuperuser      # создать администратора
python manage.py shell                # Python-консоль с настроенным Django
python manage.py test                 # запустить тесты
python manage.py check --deploy       # проверить настройки перед продакшеном
```

В Django 5.2 `shell` сразу импортирует все модели: `8 objects imported automatically`. Можно сразу писать `Task.objects.all()`.

Свои команды кладут в `tasks/management/commands/имя.py` — например, для ежедневной рассылки по cron.

## Миграции

Миграции в Django встроены, отдельный инструмент вроде [Alembic](../../../data/alembic/README.md) не нужен:

```bash
python manage.py makemigrations tasks
# Migrations for 'tasks':
#   tasks/migrations/0001_initial.py
#     + Create model Tag
#     + Create model Task
python manage.py migrate
```

Файлы миграций коммитят в репозиторий вместе с изменением модели. Как устроен файл миграции, откат, миграции данных и ловушки — в отдельной заметке о [миграциях](migrations.md).

## Переводы

`LANGUAGE_CODE = 'ru-ru'` переводит то, что уже переведено в самом Django: админку, сообщения валидации. Свои строки — названия полей, моделей, приложения — нужно пометить и перевести самим. Если интерфейс только русский, достаточно писать строки сразу по-русски, как в [примере](../example/tasks/models.py). Переводы нужны, когда языков несколько.

Строки помечают функцией `_`:

```python
# tasks/models.py
from django.utils.translation import gettext_lazy as _


class Tag(models.Model):
    name = models.CharField(_('name'), max_length=50, unique=True)

    class Meta:
        verbose_name = _('tag')
        verbose_name_plural = _('tags')
```

```python
# tasks/apps.py
from django.utils.translation import gettext_lazy as _


class TasksConfig(AppConfig):
    name = 'tasks'
    verbose_name = _('Tasks')    # заголовок раздела в админке
```

В моделях, формах и настройках нужен именно `gettext_lazy`. Эти строки вычисляются при импорте модуля, когда язык запроса ещё неизвестен. Ленивая версия возвращает объект-обещание, который переведётся в момент вывода — уже на языке конкретного пользователя. Обычный `gettext` годится внутри функций и представлений.

Дальше — три шага:

```python
# config/settings.py
LOCALE_PATHS = [BASE_DIR / 'locale']
```

```bash
mkdir locale
python manage.py makemessages -l ru       # собрать строки в locale/ru/LC_MESSAGES/django.po
```

```text
#: tasks/models.py:12
msgid "tags"
msgstr "метки"
```

`msgid` — исходная строка из кода, `msgstr` — перевод, его заполняют руками или в редакторе вроде Poedit.

```bash
python manage.py compilemessages --ignore=.venv    # .po → .mo
```

Django читает только скомпилированные `.mo`: пока их нет, переводы из `.po` не работают. Обе команды вызывают утилиты GNU gettext, которые ставят отдельно (`brew install gettext`, `apt install gettext`). Без них `compilemessages` падает с `CommandError: Can't find msgfmt`.

Проверка:

```python
from django.utils import translation

with translation.override('ru'):
    str(Tag._meta.verbose_name_plural)    # 'метки'
with translation.override('en'):
    str(Tag._meta.verbose_name_plural)    # 'tags'
```

Две неочевидные вещи. `compilemessages` без `--ignore` обходит все папки от текущей, включая `.venv`, и перекомпилирует `.po` всех установленных пакетов. А строка без своего перевода может получить перевод из каталога самого Django: до компиляции `_('name')` уже показывался как `'имя'`, потому что такая строка есть в переводах Django.

## Частые ошибки

- **Приложение не добавлено в `INSTALLED_APPS`.** `makemigrations` пишет `No changes detected`, хотя модель только что создана.
- **`DEBUG = True` на сервере.** При ошибке Django показывает страницу с настройками, путями и кусками кода. Для продакшена — `DEBUG = False` и заполненный `ALLOWED_HOSTS`.
- **`runserver` в продакшене.** Это сервер для разработки. В продакшене запускают gunicorn или uvicorn: `gunicorn config.wsgi`.
- **Одно огромное приложение `core`.** Через год в нём сотня моделей. Делите проект на приложения по предметным областям.
- **Своя модель пользователя добавлена поздно.** Если понадобится своё поле у пользователя, сменить модель после первых миграций очень трудно. В новых проектах сразу создают `AUTH_USER_MODEL` на основе `AbstractUser`, даже если пока ничего не добавлять.

## Связанные темы

- [ORM](orm.md)
- [Миграции](migrations.md)
- [Админка](admin.md)
- [Django REST Framework](drf.md)
- [Структура проекта FastAPI](../../fast_api/docs/structure.md) — для сравнения
