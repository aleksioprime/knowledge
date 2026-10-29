# Flask

**Flask** — минималистичный веб-фреймворк: из коробки только маршрутизация, обработка запроса и ответа, шаблоны и тестовый клиент. База данных, миграции, авторизация, валидация — отдельными расширениями или своими руками. За это его и выбирают: маленький сервис на Flask — это один файл без обязательной структуры. И по той же причине Flask часто встречается в старых проектах, которые придётся поддерживать.

Примеры проверены на Python 3.12, Flask 3.1.3, Werkzeug 3.1.9, gunicorn 26.2.0.

## Минимальный пример

```python
# minimal.py
from flask import Flask, jsonify, request

app = Flask(__name__)
app.json.ensure_ascii = False  # иначе кириллица придёт как Сд...
tasks = [{'id': 1, 'title': 'Сдать отчёт', 'done': False}]


@app.get('/tasks')
def list_tasks():
    done = request.args.get('done')
    result = tasks if done is None else [t for t in tasks if t['done'] == (done == 'true')]
    return jsonify(result)


@app.post('/tasks')
def create_task():
    payload = request.get_json()
    task = {'id': len(tasks) + 1, 'title': payload['title'], 'done': False}
    tasks.append(task)
    return task, 201  # словарь Flask сам превращает в JSON
```

```bash
pip install flask==3.1.3
flask --app minimal run --debug     # сервер разработки на http://127.0.0.1:5000
curl -X POST localhost:5000/tasks -H 'Content-Type: application/json' -d '{"title": "Позвонить клиенту"}'
```

```text
{"done":false,"id":2,"title":"Позвонить клиенту"}
```

Ключи в ответе отсортированы: по умолчанию Flask сортирует ключи JSON (`app.json.sort_keys`).

## Как это работает

### Маршруты, запрос и ответ

- `@app.get('/tasks/<int:task_id>')` — маршрут с параметром. Конвертеры: `int`, `float`, `path`, `uuid`, по умолчанию строка. `@app.route('/x', methods=['GET', 'POST'])` — старая запись того же.
- `request` — данные текущего запроса: `request.args` (строка запроса), `request.get_json()` (тело JSON), `request.form`, `request.files`, `request.headers`.
- Ответ — строка, словарь или список (станут JSON), кортеж `(тело, код)` или `(тело, код, заголовки)`, либо объект `Response`. `jsonify(...)` нужен, когда хочется явно, например для списка в старых версиях Flask.
- `abort(404)` прерывает обработку и возвращает ошибку.

Валидации входных данных нет: `payload['title']` упадёт с `KeyError` → 500, если поля нет. Для API к Flask добавляют Pydantic или marshmallow — в отличие от [FastAPI](../fastapi/README.md), где проверка по подсказкам типов встроена.

### Контексты: откуда берутся `request` и `current_app`

`request` импортируется как глобальная переменная, но в каждом запросе она своя. Это работает через **контексты** — Flask кладёт данные текущего запроса в контекстную переменную (`contextvars`), а `request` — прокси, который туда смотрит.

- **Контекст приложения** (application context) — «какое приложение сейчас работает». Даёт `current_app` (настройки, расширения) и `g`.
- **Контекст запроса** (request context) — «какой запрос обрабатываем». Даёт `request` и `session`. При обработке запроса Flask открывает оба контекста.
- **`g`** — хранилище на время одного контекста приложения, то есть на один запрос: сюда кладут текущего пользователя, соединение с базой, `request_id`. Между запросами `g` не живёт.

Вне запроса контекста нет, и обращение к прокси падает:

```python
from flask import current_app

from minimal import app

current_app.name
# RuntimeError: Working outside of application context.

with app.app_context():                         # так делают в скриптах и командах CLI
    print(current_app.name)                     # minimal

with app.test_request_context('/tasks?done=true'):
    from flask import request
    print(request.args)                         # ImmutableMultiDict([('done', 'true')])
```

Именно эту ошибку чаще всего видят в фоновых задачах и скриптах, которые импортируют код приложения: нужно явно открыть `app.app_context()`.

### Фабрика приложения и Blueprints

Глобальный `app = Flask(__name__)` неудобен: в тестах нельзя создать приложение с другими настройками, а расширения цепляются к объекту при импорте. Поэтому в проектах приложение создаёт функция-**фабрика**, а маршруты группируют в **Blueprint** — набор маршрутов, который регистрируют в приложении с префиксом.

```text
tasker/
├── __init__.py    # create_app()
└── tasks.py       # Blueprint с маршрутами задач
```

```python
# tasker/tasks.py
import asyncio
import time

from flask import Blueprint, current_app, g, request

bp = Blueprint('tasks', __name__)
TASKS = {1: {'id': 1, 'title': 'Сдать отчёт'}}


@bp.before_request
def load_user():
    g.user_id = request.headers.get('X-User-Id')


@bp.get('/')
def list_tasks():
    return {'items': list(TASKS.values()), 'page_size': current_app.config['PAGE_SIZE'], 'user': g.user_id}


@bp.get('/<int:task_id>')
def get_task(task_id: int):
    from tasker import TaskNotFound

    if task_id not in TASKS:
        raise TaskNotFound(task_id)
    return TASKS[task_id]


@bp.get('/slow-sync')
def slow_sync():
    time.sleep(1)
    return {'ok': True}


@bp.get('/slow-async')
async def slow_async():
    await asyncio.gather(asyncio.sleep(1), asyncio.sleep(1))  # два ожидания параллельно — внутри запроса
    return {'ok': True}
```

```python
# tasker/__init__.py
from flask import Flask
from werkzeug.exceptions import HTTPException

from tasker.tasks import bp as tasks_bp


class TaskNotFound(Exception):
    pass


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(DATABASE_URL='sqlite:///tasker.db', PAGE_SIZE=20)
    app.config.from_prefixed_env()  # FLASK_PAGE_SIZE=50 → app.config['PAGE_SIZE'] == 50
    if config:
        app.config.update(config)

    app.register_blueprint(tasks_bp, url_prefix='/api/tasks')

    @app.errorhandler(TaskNotFound)
    def task_not_found(error):
        return {'detail': f'Задача {error.args[0]} не найдена'}, 404

    @app.errorhandler(HTTPException)
    def http_error(error):
        return {'detail': error.description}, error.code

    return app
```

Код маршрутов обращается к приложению только через `current_app` — поэтому один и тот же Blueprint работает в любом приложении, созданном фабрикой.

### Конфигурация

`app.config` — словарь с настройками. Источники, от простого к удобному:

- `app.config.from_mapping(...)` или `app.config.update(...)` — значения по умолчанию и переопределения в тестах;
- `app.config.from_prefixed_env()` — переменные окружения с префиксом `FLASK_`, значения разбираются как JSON: `FLASK_PAGE_SIZE=50` станет числом;
- `app.config.from_object('tasker.settings.Production')` — класс с атрибутами в верхнем регистре;
- `app.config.from_file('config.toml', load=tomllib.load, text=False)` — файл; относительный путь считается от папки приложения (`app.root_path`), а не от текущей директории.

Секреты (`SECRET_KEY`, пароль базы) берут из окружения, а не из кода. Часто вместо этого используют pydantic-settings, как в [FastAPI](../fastapi/structure.md), и кладут готовый объект настроек в `app.config`.

### Ошибки

`@app.errorhandler(...)` регистрирует обработчик для исключения или кода ответа. В примере выше:

- своё доменное исключение `TaskNotFound` превращается в 404 с понятным текстом;
- все `HTTPException` из Werkzeug (`abort(404)`, неизвестный URL, неверный метод) отдаются как JSON, а не как HTML-страница по умолчанию.

Необработанное исключение даёт 500. В режиме `--debug` Flask показывает интерактивный отладчик в браузере — в продакшене его включать нельзя: через него можно выполнить произвольный код на сервере. Ошибки в продакшене собирают в [Sentry](../../../infrastructure/monitoring/sentry/README.md), для Flask интеграция включается автоматически.

### Расширения

Всё, чего нет в ядре, добавляют расширениями. Они устроены одинаково: создаются без приложения и подключаются в фабрике через `init_app(app)`. Самые частые: **Flask-SQLAlchemy** — интеграция [SQLAlchemy](../../databases/sqlalchemy/README.md) с сессией на запрос (`db.session`) и моделями `db.Model`; **Flask-Migrate** — [Alembic](../../databases/alembic/README.md) с командами `flask db migrate` и `flask db upgrade`; **Flask-JWT-Extended** — выпуск и проверка JWT с декоратором `@jwt_required()`. Кроме них встречаются Flask-Login (сессии в cookie), Flask-CORS, flask-smorest или Flask-RESTX (схемы и OpenAPI). Перед тем как брать расширение, стоит посмотреть, живо ли оно: у Flask много заброшенных расширений, и в старых проектах они часто мешают обновить сам Flask.

### Синхронность и async view

Flask — **WSGI**-фреймворк: один рабочий поток обрабатывает один запрос от начала до конца. Начиная с Flask 2.0 можно писать `async def` view (нужен пакет `flask[async]`, он ставит `asgiref`). Но это **не делает сервер асинхронным**: Flask запускает для такой функции цикл событий внутри потока, дожидается результата и только потом освобождает поток. `async` помогает выполнить несколько ожиданий параллельно **внутри одного запроса** — в `slow_async` два `sleep(1)` заняли одну секунду. Но обслуживать больше запросов одновременно он не помогает.

Проверка: 4 одновременных запроса к приложению под gunicorn.

```bash
gunicorn -w 1 'tasker:create_app()'               # один процесс, один поток
gunicorn -w 1 --threads 4 'tasker:create_app()'   # один процесс, четыре потока
gunicorn -w 4 'tasker:create_app()'               # четыре процесса
```

| Запуск | 4 запроса к `slow-sync` | 4 запроса к `slow-async` |
|---|---|---|
| `-w 1` | 4,2–4,6 с | 4,2–4,5 с |
| `-w 1 --threads 4` | 1,2–1,3 с | 1,2–1,4 с |
| `-w 4` | 1,2 с | 1,2–1,7 с |

С одним потоком `async` не помог: запросы всё равно шли по очереди. Одновременность во Flask дают процессы и потоки gunicorn, а не `async def`. Если сервису нужны тысячи одновременных долгих соединений (WebSocket, долгие запросы к соседям), берут ASGI-фреймворк — FastAPI, Starlette, Quart (асинхронный Flask с тем же API).

### Запуск в продакшене

`flask run` — сервер разработки: один процесс, отладчик, без защиты от медленных клиентов. В продакшене Flask запускают WSGI-сервером, обычно gunicorn за [nginx](../../web/nginx/README.md):

```bash
gunicorn -w 4 --threads 2 -b 0.0.0.0:8000 'tasker:create_app()'
```

- `-w` — число процессов. Отправная точка — по числу ядер или `2 × ядра + 1`, затем подбирают нагрузочным тестом.
- `--threads` — потоки в процессе. Помогают, когда view ждёт базу или HTTP: GIL отпускается на время ввода-вывода.
- `'tasker:create_app()'` — gunicorn сам вызовет фабрику.
- Настройки удобно держать в `gunicorn.conf.py` — пример с JSON-логами есть в стенде [Логи в ELK](../../../infrastructure/monitoring/logging/elk.md).

### Тесты

`app.test_client()` отправляет запросы в приложение без сервера и сети. С фабрикой каждый тест получает приложение со своими настройками.

```python
# test_tasker.py
import pytest

from tasker import create_app


@pytest.fixture
def client():
    app = create_app({'TESTING': True, 'PAGE_SIZE': 5})
    return app.test_client()


def test_list_tasks(client):
    response = client.get('/api/tasks/', headers={'X-User-Id': '42'})
    assert response.status_code == 200
    assert response.json == {'items': [{'id': 1, 'title': 'Сдать отчёт'}], 'page_size': 5, 'user': '42'}


def test_missing_task(client):
    response = client.get('/api/tasks/99')
    assert response.status_code == 404
    assert response.json == {'detail': 'Задача 99 не найдена'}


def test_unknown_url(client):
    assert client.get('/nope').json['detail'].startswith('The requested URL was not found')
```

```text
3 passed in 1.10s
```

`TESTING=True` заставляет исключения из view пробрасываться в тест, а не превращаться в 500 — так виден настоящий traceback. Подробнее о pytest — в [заметке](../../testing/pytest/README.md).

### Flask, FastAPI или Django

| | Flask | FastAPI | Django |
|---|---|---|---|
| Модель | WSGI, синхронный | ASGI, асинхронный | WSGI (ASGI частично) |
| Что из коробки | маршруты, запрос/ответ, шаблоны | маршруты, валидация Pydantic, OpenAPI, зависимости | ORM, миграции, админка, пользователи, формы |
| Валидация входа | расширения (marshmallow, Pydantic) | встроена, по подсказкам типов | формы, сериализаторы DRF |
| Документация API | расширения | автоматически `/docs` | DRF + drf-spectacular |
| Структура проекта | любая, решает команда | любая, решает команда | задана фреймворком |
| Когда выбирать | маленький сервис, прототип, поддержка существующего кода | API-сервисы, много ввода-вывода, микросервисы | продукт с админкой и сложной моделью данных, CRUD, быстрое начало |

Для нового API-сервиса чаще выбирают FastAPI. Flask оправдан, когда команда его хорошо знает, сервис маленький и синхронный, или он уже есть.

### Как поддерживать legacy-приложение на Flask

Старый Flask-сервис обычно выглядит так: глобальный `app`, версии не зафиксированы, тестов мало, половина расширений больше не развивается. Порядок работы:

1. **Зафиксировать версии.** `pip freeze > requirements.lock` с того окружения, которое сейчас работает в продакшене. Без этого любая пересборка образа может притащить новый Flask или Werkzeug и сломать сервис.
2. **Написать тесты на текущее поведение** (характеризационные тесты) перед любыми изменениями: ключевые эндпоинты, коды ответов, форма JSON. Тесты фиксируют, как работает сейчас, даже если это выглядит странно, — тогда рефакторинг не поменяет поведение незаметно.
3. **Добавить наблюдаемость:** [структурированные логи](../../../infrastructure/monitoring/logging/elk.md), [Sentry](../../../infrastructure/monitoring/sentry/README.md), метрики. Сначала узнаём, какие ошибки уже есть, потом меняем код.
4. **Обновлять маленькими шагами:** одна библиотека за раз, читая список изменений. Flask и Werkzeug обновляют вместе: Flask требует свежий Werkzeug. Предупреждения об устаревании (`python -W error::DeprecationWarning -m pytest`) подсказывают, что сломается в следующей версии.
5. **Переходить к фабрике и Blueprints постепенно**, по одному модулю, под защитой тестов.
6. **Не переписывать всё сразу на FastAPI.** Если переход нужен, новые эндпоинты делают в новом сервисе, а старые переносят по одному за прокси (паттерн «удушающий фикус», strangler fig).

## Частые ошибки

- **`RuntimeError: Working outside of application context`** в скрипте или фоновой задаче → обернуть код в `with app.app_context():`.
- **Хранить состояние в глобальных переменных модуля.** В gunicorn с несколькими процессами у каждого процесса своя копия — данные «теряются» между запросами. Состояние — в базе или Redis; на время запроса — в `g`.
- **`flask run` или `app.run(debug=True)` в продакшене.** Сервер разработки не рассчитан на нагрузку, а отладчик позволяет выполнить код на сервере.
- **Ожидать от `async def` ускорения под нагрузкой.** Поток всё равно занят до конца запроса.
- **Кириллица в ответе как `С...`** → `app.json.ensure_ascii = False`.
- **Незафиксированные версии в старом проекте.** Свежая сборка тянет несовместимый Werkzeug, и приложение падает при старте.

## Когда не использовать

- Новый API со строгими схемами и документацией → [FastAPI](../fastapi/README.md): валидация и OpenAPI без расширений.
- Много одновременных долгих соединений, WebSocket → ASGI-фреймворк.
- Продукт с админкой, пользователями и большой моделью данных → [Django](../django/README.md): всё это уже есть.

## Связанные темы

- [FastAPI](../fastapi/README.md)
- [Django](../django/README.md)
- [Sentry: ошибки в продакшене](../../../infrastructure/monitoring/sentry/README.md)
- [Логи в ELK](../../../infrastructure/monitoring/logging/elk.md) — Flask с JSON-логами и `request_id`
- [Pytest](../../testing/pytest/README.md)
