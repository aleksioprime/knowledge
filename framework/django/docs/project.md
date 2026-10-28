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

Файлы миграций коммитят в репозиторий вместе с изменением модели.

## Частые ошибки

- **Приложение не добавлено в `INSTALLED_APPS`.** `makemigrations` пишет `No changes detected`, хотя модель только что создана.
- **`DEBUG = True` на сервере.** При ошибке Django показывает страницу с настройками, путями и кусками кода. Для продакшена — `DEBUG = False` и заполненный `ALLOWED_HOSTS`.
- **`runserver` в продакшене.** Это сервер для разработки. В продакшене запускают gunicorn или uvicorn: `gunicorn config.wsgi`.
- **Одно огромное приложение `core`.** Через год в нём сотня моделей. Делите проект на приложения по предметным областям.
- **Своя модель пользователя добавлена поздно.** Если понадобится своё поле у пользователя, сменить модель после первых миграций очень трудно. В новых проектах сразу создают `AUTH_USER_MODEL` на основе `AbstractUser`, даже если пока ничего не добавлять.

## Связанные темы

- [ORM](orm.md)
- [Админка](admin.md)
- [Django REST Framework](drf.md)
- [Структура проекта FastAPI](../../fast_api/docs/structure.md) — для сравнения
