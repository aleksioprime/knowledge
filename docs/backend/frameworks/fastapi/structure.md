# Структура проекта FastAPI

Пока эндпоинтов пять, всё помещается в `main.py`. Когда их становится тридцать, в одном файле оказываются HTTP-обработчики, SQL-запросы, проверка паролей и настройки, и любое изменение задевает всё сразу. Хорошая структура раскладывает код по ответственности: кто принимает HTTP, кто решает бизнес-задачу, кто хранит данные.

У FastAPI нет обязательной структуры. Ниже — распространённый вариант на примере [«Задачника»](../../../practice/projects/tasker/README.md).

## Минимальный пример

Первый шаг от одного файла: эндпоинты задач уезжают в свой роутер, а `main.py` только собирает приложение.

```python
# app/api/routers/tasks.py
from fastapi import APIRouter

router = APIRouter(prefix='/tasks', tags=['tasks'])


@router.get('')
async def list_tasks() -> list[dict]:
    return [{'id': 1, 'title': 'Купить хлеб', 'done': False}]
```

```python
# app/main.py
from fastapi import FastAPI

from app.api.routers import tasks

app = FastAPI(title='Задачник')
app.include_router(tasks.router)
```

```bash
uvicorn app.main:app --reload    # запускать из корня проекта, рядом с папкой app/
curl localhost:8000/tasks
# [{"id":1,"title":"Купить хлеб","done":false}]
```

## Как это работает

### Как разложен «Задачник»

```text
app/
├── main.py            # сборка приложения: роутеры, обработчики ошибок
├── models.py          # таблицы SQLAlchemy
├── schemas.py         # схемы Pydantic для API
├── core/
│   ├── config.py      # настройки из окружения
│   ├── database.py    # движок БД, сессия
│   └── security.py    # пароли и JWT
├── api/
│   ├── deps.py        # общие зависимости: сессия, текущий пользователь
│   └── routers/
│       ├── auth.py
│       └── tasks.py
└── services/
    ├── users.py
    └── tasks.py
```

### Путь одного запроса

Проследим `PATCH /tasks/1` с телом `{"done": true}`.

**1. Роутер** — только HTTP: какой путь, какие параметры, какой код ответа. Логики здесь нет.

```python
# app/api/routers/tasks.py
router = APIRouter(prefix='/tasks', tags=['tasks'])


@router.patch('/{task_id}')
async def update_task(session: SessionDep, user: CurrentUser, task_id: int, data: TaskUpdate) -> TaskRead:
    return TaskRead.model_validate(await tasks.update_task(session, user, task_id, data))
```

**2. Зависимости** готовят то, что нужно почти всем: сессию БД и пользователя по токену (`SessionDep`, `CurrentUser` из `api/deps.py`).

**3. Сервис** — бизнес-правила: задача должна существовать и принадлежать пользователю, меняются только присланные поля. Сервис ничего не знает про HTTP и выбрасывает свои исключения.

```python
# app/services/tasks.py
async def update_task(session: AsyncSession, owner: User, task_id: int, data: TaskUpdate) -> Task:
    task = await get_task(session, owner, task_id)  # выбросит TaskNotFoundError
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    await session.commit()
    return task
```

**4. Модель и схема.** Сервис меняет объект SQLAlchemy (`models.py`), а роутер превращает его в схему ответа (`schemas.py`). Если задачи нет, обработчик в `main.py` превратит `TaskNotFoundError` в ответ 404.

### Зачем так делить

- **Сервис можно вызвать не только из HTTP.** Ту же `update_task` можно использовать в фоновой задаче Celery или в CLI-команде.
- **Проще тестировать.** Правила «чужую задачу не видно» проверяются в одном месте.
- **Понятно, где искать.** Ошибка в формате ответа — в схемах, ошибка в правах — в сервисе или зависимостях.

### Подключение роутеров и настройки

`APIRouter` — это «мини-приложение» с префиксом и тегом для документации. В `main.py` их просто собирают:

```python
# app/main.py
app = FastAPI(title='Задачник')
app.include_router(auth.router)
app.include_router(tasks.router)
```

Настройки читаются из переменных окружения через [pydantic-settings](../../../languages/python/typing/pydantic.md#настройки-приложения), и в коде нет ни паролей, ни адресов:

```python
# app/core/config.py
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    database_url: str = 'postgresql+asyncpg://tasker:tasker@localhost:5432/tasker'
    secret_key: str = 'change-me'
    access_token_expire_minutes: int = 60


settings = Settings()
```

### Когда добавлять ещё слои

В больших проектах из сервисов выделяют **репозитории**: в них лежат только запросы к БД, а сервисы занимаются правилами. Это помогает, когда запросы сложные и повторяются или когда хочется тестировать правила без базы. В «Задачнике» запросы простые, и отдельный слой был бы лишней церемонией.

Когда сущностей много, файлы `models.py` и `schemas.py` разбивают на пакеты (`models/task.py`, `models/user.py`) или раскладывают код по доменам: `app/tasks/{router,service,models,schemas}.py`.

## Частые ошибки

- SQL в роутерах → через полгода одинаковые запросы оказываются в десяти местах с небольшими отличиями, и правка правила требует обхода всех → переносить запросы и правила в сервисы, роутер оставлять для HTTP.
- `HTTPException` в сервисах → сервис привязан к HTTP, его нельзя вызвать из фоновой задачи или CLI без лишних `try/except` → выбрасывать свои исключения и превращать их в ответы обработчиками в `main.py`.
- Слои ради слоёв → три файла на сущность, где каждый просто вызывает следующий, мешают читать код → добавлять слой, когда появляется настоящая причина: повторяющиеся запросы, тесты без базы.
- Запуск `uvicorn main:app` из папки `app/` → `ModuleNotFoundError: No module named 'app'`, потому что корень проекта не в путях импорта → запускать из корня проекта как `uvicorn app.main:app`.
- Роутер объявлен, но не подключён → эндпоинты отсутствуют в `/docs`, запросы получают 404 → добавить `app.include_router(...)` в `main.py`.

## Когда не использовать

Для прототипа, учебного примера или сервиса из нескольких эндпоинтов без базы папки `services/`, `core/` и `api/` только мешают: один `main.py` на сто строк читается быстрее, чем шесть файлов по десять. Начинайте с [первого приложения](first_app.md) в одном файле и раскладывайте код, когда файл перестаёт помещаться в голове или появляется второй разработчик.

Если проект большой и команда хочет готовый каркас с договорённостями, а не собственную структуру, посмотрите на [Django](../django/project.md): там расположение моделей, настроек и URL задано фреймворком, и любой проект читается одинаково.

## Связанные темы

- [Первое приложение](first_app.md) — с чего начинается проект в одном файле
- [Модули, пакеты и импорты](../../../languages/python/modules/imports.md) — почему запускать нужно из корня проекта
- [Зависимости](dependencies.md)
- [Ошибки и коды ответов](errors.md)
- [Структура проекта Django](../django/project.md) — для сравнения
