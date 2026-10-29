# Sentry: ошибки в продакшене

В логах сервиса за час 40 тысяч строк, и где-то среди них — `KeyError`, который сегодня случился 300 раз у 50 пользователей мобильного приложения после вчерашнего релиза. В [централизованных логах](../logging/README.md) это можно найти, если знать, что искать. **Sentry** решает задачу с другой стороны: каждое необработанное исключение отправляется как событие с полным контекстом, а одинаковые события склеиваются в одну **проблему** (issue). Вместо потока строк — список «что сломано»: сколько раз, у скольких пользователей, с какого релиза, с трассировкой стека и значениями переменных.

| | Лог | Sentry |
|---|---|---|
| Что это | поток всех событий подряд | только ошибки, сгруппированные по причине |
| Как узнаём о проблеме | ищем сами или настраиваем алерт на шаблон | новая проблема или рост старой — уведомление |
| Контекст | то, что написали в строку | стек, локальные переменные, запрос, пользователь, теги, предшествующие события |
| Релизы | надо добавлять вручную | «появилась в 1.4.2», «решена в 1.4.3, вернулась в 1.5.0» |

Sentry не заменяет логи и метрики: он про ошибки, а не про нормальный ход работы и не про задержки.

Примеры в [`example/`](examples/) проверены на Python 3.12, sentry-sdk 2.73.0, FastAPI 0.162.0, Flask 3.1.3 — без сервера Sentry: события принимает маленький локальный приёмник, и видно, какой JSON уходит.

## Минимальный пример

```python
import sentry_sdk

sentry_sdk.init(
    dsn='https://<ключ>@o123.ingest.sentry.io/456',  # адрес проекта из настроек Sentry
    environment='production',
    release='tasker@1.4.2',
)
```

Этого достаточно: SDK сам находит установленные библиотеки и включает для них интеграции. В проверочном окружении с FastAPI, Flask и httpx в событии было видно:

```text
"integrations": ["argv", "atexit", "dedupe", "excepthook", "fastapi", "flask", "httpx",
                 "logging", "modules", "starlette", "stdlib", "threading"]
```

Интеграция FastAPI ловит необработанные исключения в эндпоинтах, интеграция `logging` превращает `logger.error(...)` в событие, а записи уровнем ниже — в «хлебные крошки», `excepthook` ловит падение скрипта.

## Проверка без сервера

DSN имеет вид `схема://ключ@хост/проект`. SDK отправляет события POST-запросом на `хост/api/<проект>/envelope/` в формате «конверта» (envelope): строка-заголовок, затем пары «заголовок элемента» + JSON элемента. Если указать DSN на свой адрес, можно посмотреть, что именно уходит. Приёмник [`example/receiver.py`](examples/receiver.py) — полсотни строк на `http.server`: распаковывает gzip, печатает тип и главное поле каждого события и складывает события целиком в `events.jsonl`.

```bash
cd docs/infrastructure/monitoring/sentry/examples
pip install -r requirements.txt
python receiver.py &                         # слушает 127.0.0.1:47001
uvicorn app_fastapi:app --port 47002 &       # DSN: http://public@127.0.0.1:47001/1
```

Тестовое приложение [`example/app_fastapi.py`](examples/app_fastapi.py) — эндпоинты задач с ошибкой в коде, ожидаемыми 404 и 409 и эндпоинт, в который приходят персональные данные.

```bash
curl -H 'X-User-Id: 42' -H 'X-Client: ios' localhost:47002/tasks/13   # × 3, ошибка в коде → 500
curl localhost:47002/tasks/99                                         # 404
curl localhost:47002/tasks/7                                          # 409
curl -X POST localhost:47002/tasks/1/assign -H 'X-User-Id: 42' -H 'Authorization: Bearer abc.def' \
     -H 'Content-Type: application/json' -d '{"email": "anna@example.com", "password": "secret"}'  # 500
```

Приёмник получил четыре события — три `KeyError` и один `RuntimeError`. Ответы 404 и 409 событий не создали:

```text
event       KeyError
event       KeyError
event       KeyError
event       RuntimeError
```

Сокращённое событие `KeyError` (полное — около 45 КБ: ещё версии всех установленных пакетов, рантайм, имя сервера):

```json
{
  "level": "error",
  "environment": "local",
  "release": "tasker@1.4.2",
  "transaction": "/tasks/{task_id}",
  "tags": {"client": "ios"},
  "user": {"id": "42"},
  "exception": {"values": [{
    "type": "KeyError",
    "value": "13",
    "mechanism": {"type": "starlette", "handled": false},
    "stacktrace": {"frames": ["...", {
      "filename": "app_fastapi.py",
      "function": "get_task",
      "lineno": 65,
      "context_line": "        task = TASKS[task_id]['title']  # ошибка в коде: KeyError",
      "in_app": true,
      "vars": {"task_id": "13"}
    }]}
  }]},
  "breadcrumbs": {"values": [
    {"category": "tasker", "level": "info", "message": "Читаем задачу 13"},
    {"category": "uvicorn.access", "level": "info", "message": "127.0.0.1:64463 - \"GET /tasks/13 HTTP/1.1\" 500"}
  ]},
  "request": {
    "method": "GET",
    "url": "http://localhost:47002/tasks/13",
    "headers": {"host": "localhost:47002", "user-agent": "curl/8.7.1", "accept": "*/*", "x-user-id": "42", "x-client": "ios"}
  }
}
```

Что здесь важно:

- `transaction` — шаблон маршрута `/tasks/{task_id}`, а не конкретный URL: по нему ошибки группируются и фильтруются;
- в кадре стека — строка кода и **локальные переменные** (`vars`). Это главная ценность и главный риск: в переменных бывают пароли и email;
- `breadcrumbs` — что происходило в этом запросе до ошибки: записи `logging` уровня INFO и выше;
- `"handled": false` — исключение никто не поймал.

### Группировка

Три `KeyError` — три отдельных события с разными `event_id`, но с одинаковым стеком (проверено сравнением кадров `in_app`). Склеивает их в одну проблему **сервер** Sentry: по умолчанию по типу исключения и стеку вызовов, для сообщений из `logging` — по шаблону сообщения. SDK только присылает материал для группировки, поэтому сам подсчёт «одна проблема, 3 события, 1 пользователь» без сервера не проверить.

Из этого следует правило для логов: передавайте параметры отдельно, а не f-строкой. В событии `logger.error('Не удалось отправить напоминание по задаче %s', 42)` уходят и шаблон, и параметры:

```json
"logentry": {
  "message": "Не удалось отправить напоминание по задаче %s",
  "formatted": "Не удалось отправить напоминание по задаче 42",
  "params": [42]
}
```

С f-строкой каждая задача дала бы своё сообщение и, возможно, свою проблему.

Если правила по умолчанию склеивают лишнее или дробят одно и то же, задают **отпечаток** (fingerprint) — список строк, по которому сервер группирует вместо стека:

```python
with sentry_sdk.new_scope() as scope:
    scope.set_tag('report', 'monthly')
    scope.fingerprint = ['report-failed']  # все сбои отчёта — одна проблема
    sentry_sdk.capture_exception(error)
```

В отправленном событии это поле `"fingerprint": ["report-failed"]`.

## Sentry в FastAPI

Отдельно подключать ничего не нужно: `sentry_sdk.init(...)` до создания приложения, и интеграции Starlette и FastAPI включатся сами. Что отправляется:

- необработанные исключения → 500 → событие;
- `HTTPException(404)` и свои обработчики исключений, возвращающие 4xx, — **не отправляются**: в проверке 404 и 409 событий не дали. По умолчанию интеграция отправляет только ответы с кодами 500–599 (`failed_request_status_codes`).

Если всё же нужно ловить, например, 403, интеграцию указывают явно:

```python
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

sentry_sdk.init(
    dsn=...,
    integrations=[
        StarletteIntegration(failed_request_status_codes={403, *range(500, 600)}),
        FastApiIntegration(failed_request_status_codes={403, *range(500, 600)}),
    ],
)
```

## Sentry во Flask

Так же: `init` до создания приложения, интеграция Flask включается автоматически. [`example/app_flask.py`](examples/app_flask.py):

```python
import sentry_sdk
from flask import Flask, abort, jsonify

sentry_sdk.init(
    dsn='http://public@127.0.0.1:47001/1',
    environment='staging',
    release='tasker@1.4.2',
    traces_sample_rate=1.0,  # для проверки — каждый запрос; в продакшене 0.01–0.1
)

app = Flask(__name__)
TASKS = {1: {'id': 1, 'title': 'Сдать отчёт'}}


@app.get('/tasks/<int:task_id>')
def get_task(task_id: int):
    if task_id not in TASKS:
        abort(404)
    return jsonify(TASKS[task_id])


@app.post('/reports')
def build_report():
    sentry_sdk.add_breadcrumb(category='report', message='Собираем отчёт за октябрь', level='info')
    try:
        1 / 0
    except ZeroDivisionError as error:
        with sentry_sdk.new_scope() as scope:
            scope.set_tag('report', 'monthly')
            scope.fingerprint = ['report-failed']  # все сбои отчёта — одна проблема
            sentry_sdk.capture_exception(error)
    return jsonify(status='queued'), 202
```

```bash
flask --app app_flask run --port 47004
curl localhost:47004/tasks/1; curl localhost:47004/tasks/5; curl -X POST localhost:47004/reports
```

```text
transaction get_task          статус ok
transaction get_task          статус not_found     ← 404 — только транзакция, ошибки нет
event       ZeroDivisionError теги {'report': 'monthly'}, fingerprint ['report-failed'],
                              крошки ['Собираем отчёт за октябрь'], handled: True
transaction build_report      статус ok
```

У события `ZeroDivisionError` и транзакции `build_report` один `trace_id` — в Sentry из ошибки можно перейти к трассе запроса, в котором она случилась. `capture_exception` нужен, когда исключение поймано и обработано, но знать о нём всё равно надо.

## Контекст: пользователь, теги, крошки

```python
sentry_sdk.set_user({'id': user_id})          # кто пострадал — id, а не email
sentry_sdk.set_tag('client', 'ios')           # по тегам фильтруют и строят разбивку
sentry_sdk.set_context('task', {'id': 13, 'project_id': 7})  # произвольные детали, без поиска
sentry_sdk.add_breadcrumb(category='cache', message='промах кэша задачи 13')
```

- **user** — Sentry считает число затронутых пользователей: «100 событий у одного человека» и «100 событий у 100 человек» — разные приоритеты. Достаточно `id`, email и IP не нужны.
- **теги** — короткие значения с небольшим числом вариантов: клиент, регион, тариф, версия API. По ним фильтруют список проблем.
- **context** — подробности, которые смотрят в карточке события, но не ищут по ним.
- **крошки** (breadcrumbs) — что происходило до ошибки. Интеграции добавляют их сами: записи `logging`, исходящие HTTP-запросы httpx, SQL-запросы.

В веб-приложении контекст живёт в **области** (scope) текущего запроса: `set_user` в middleware действует до конца этого запроса и не протекает в соседние. В примере FastAPI пользователь и тег ставятся в middleware из заголовков `X-User-Id` и `X-Client`.

## `before_send`: вырезаем персональные данные

Событие уходит на внешний сервер, и в нём легко оказываются [персональные данные](../../../backend/web/security/personal_data.md): тело запроса, локальные переменные, текст исключения, сообщения логов. Сначала посмотрим, что SDK вырезает сам. Тот же `POST /tasks/1/assign` без своей фильтрации:

```text
"SMTP недоступен, письмо для anna@example.com не отправлено"                ← текст исключения
request.headers: "authorization": "[Filtered]", "cookie": "[Filtered]"
request.data:    {"email": "anna@example.com", "password": "[Filtered]"}
breadcrumb:      "Назначаем задачу 1 на anna@example.com"
vars.payload:    {"email": "'anna@example.com'", "password": "'secret'"}   ← пароль в переменных!
```

SDK по умолчанию (`send_default_pii=False`) убирает заголовки `Authorization` и `Cookie` и поля с именами из своего списка (`password`, `token`, `secret` и др.) в теле запроса. Но email он не трогает нигде, а в локальных переменных не заглянул во вложенный словарь — и **пароль ушёл открытым текстом**.

`before_send(event, hint)` вызывается перед отправкой каждого события: можно изменить событие или вернуть `None`, чтобы не отправлять его вовсе.

```python
EMAIL = re.compile(r'[\w.+-]+@(?:[\w-]+\.)+[a-z]{2,}', re.IGNORECASE)
SECRET_KEYS = {'password', 'token', 'authorization', 'email', 'phone'}


def scrub(value):
    if isinstance(value, dict):
        return {
            key: '[Filtered]' if key.lower() in SECRET_KEYS else scrub(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [scrub(item) for item in value]
    if isinstance(value, str):
        return EMAIL.sub('[email]', value)
    return value


def before_send(event, hint):
    return scrub(event)  # вернуть None — событие не отправится


sentry_sdk.init(dsn=..., before_send=before_send)
```

Результат на том же запросе:

```text
"SMTP недоступен, письмо для [email] не отправлено"
request.data:    {"email": "[Filtered]", "password": "[Filtered]"}
breadcrumb:      "Назначаем задачу 1 на [email]"
vars.payload:    {"email": "[Filtered]", "password": "[Filtered]"}
```

Ошибка, найденная при проверке: первая версия регулярного выражения для email (`[\w.+-]+@[\w-]+\.[\w.]+`) превращала `release: tasker@1.4.2` в `[email]` — релиз выглядит как адрес. Регулярки по всему событию надо проверять на служебных полях. Надёжнее не полагаться только на них: не класть ПД в текст исключений и логов, логировать `user_id`, а не email. Подробнее о маскировании — в заметке [Персональные данные](../../../backend/web/security/personal_data.md#маскирование-в-логах).

Ещё рычаги: `include_local_variables=False` — не отправлять переменные совсем (теряется полезный контекст); `max_request_body_size='never'` — не отправлять тело запроса. Для транзакций есть отдельный хук `before_send_transaction`.

## Трассировка производительности: `traces_sample_rate`

Кроме ошибок, Sentry умеет собирать транзакции — длительность запросов и вложенных шагов, по сути [трассировку](../tracing/README.md). Это включает `traces_sample_rate` — доля запросов, для которых записывается транзакция:

- `0` или параметр не задан — только ошибки;
- `1.0` — каждый запрос, только для разработки и проверки;
- `0.01–0.1` — обычный выбор для продакшена: транзакции — такие же события, и за них платят квотой.

Гибче — функция `traces_sampler`, которая решает для каждого запроса. Проверено во Flask: из трёх запросов к `/health`, `/tasks`, `/health` отправлена одна транзакция — `tasks`.

```python
def traces_sampler(sampling_context):
    if sampling_context.get('wsgi_environ', {}).get('PATH_INFO') == '/health':
        return 0.0  # проверки здоровья не трассируем
    return 0.05
```

Во Flask в контексте есть `wsgi_environ`, в FastAPI — `asgi_scope`.

## `environment` и `release`

- **environment** — `production`, `staging`, `local`. Разделяет события разных окружений: ошибка на стенде разработки не должна будить дежурного.
- **release** — версия кода: `tasker@1.4.2` или хэш коммита. По нему Sentry показывает, в каком релизе проблема появилась, и отмечает регрессии: проблема закрыта как исправленная в 1.4.3, но снова пришла из 1.5.0. Версию передают из CI переменной окружения: SDK сам читает `SENTRY_RELEASE` и `SENTRY_ENVIRONMENT`, если параметры не заданы в `init`.

## Что не отправлять

- **Ожидаемые 4xx**: 404, 401, 409, ошибки валидации. Это не ошибки кода, а нормальная работа. Интеграции FastAPI и Flask по умолчанию их и не отправляют — не стоит ловить их вручную через `capture_exception`.
- **Ожидаемые исключения бизнес-логики** («задача заблокирована») — обрабатывать и возвращать понятный ответ; если всё же долетают до Sentry — отфильтровать в `before_send` по `hint['exc_info']` или параметром `ignore_errors`.
- **Шум от ботов и клиентов**: обрыв соединения клиентом, сканеры уязвимостей.
- **Персональные данные и секреты** — см. выше.

Всё лишнее размывает список проблем: когда в нём тысяча «ошибок», настоящую новую уже никто не заметит.

## Self-hosted Sentry и GlitchTip

Sentry можно использовать как облачный сервис или развернуть у себя: **self-hosted Sentry** распространяется как набор docker compose файлов, но это десятки контейнеров (Kafka, ClickHouse, Redis, PostgreSQL, Snuba, Relay, воркеры) и требования от 16 ГБ памяти — его разворачивают, когда данные нельзя отправлять наружу и есть кому эксплуатировать. Лёгкая альтернатива — **GlitchTip**: открытый сервис, совместимый с протоколом Sentry (тот же `sentry-sdk`, меняется только DSN), из веб-приложения, воркера, PostgreSQL и Redis. Он умеет группировать ошибки, уведомлять и показывать релизы, но беднее по трассировке и интерфейсу. В этой заметке GlitchTip не поднимался: локальный стенд Docker был занят другими проектами, и проверка шла через свой приёмник.

## Частые ошибки

- **Ловить исключение и не сообщать о нём.** `except Exception: return {}` прячет ошибку и от логов, и от Sentry. Либо пробрасывать, либо `logger.exception(...)` / `capture_exception`.
- **`send_default_pii=True` «чтобы было удобнее».** Начнут уходить IP, cookie, данные пользователя. Включать осознанно и вместе с `before_send`.
- **Полагаться на встроенную фильтрацию.** В проверке пароль из вложенной локальной переменной ушёл открытым текстом.
- **Сообщения логов f-строками.** Каждое уникальное сообщение может стать отдельной проблемой.
- **`traces_sample_rate=1.0` в продакшене.** Квота кончается за день, а SDK тратит время на каждую транзакцию.
- **Один DSN на все окружения без `environment`.** Ошибки стенда смешиваются с продакшеном.
- **Нет `release`.** Не видно, какой выпуск сломал, и не работают регрессии.

## Связанные темы

- [Централизованное логирование](../logging/README.md) и [Логи в ELK](../logging/elk.md)
- [Распределённая трассировка](../tracing/README.md)
- [Персональные данные](../../../backend/web/security/personal_data.md)
- [Логирование в Python](../../../languages/python/stdlib/logging.md)
- [Flask](../../../backend/frameworks/flask/README.md) и [FastAPI](../../../backend/frameworks/fastapi/README.md)
