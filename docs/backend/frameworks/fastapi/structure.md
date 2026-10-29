# Структура проекта FastAPI

Пока эндпоинтов пять, всё помещается в `main.py`. Когда их становится тридцать, в одном файле оказываются HTTP-обработчики, SQL-запросы, проверка паролей и настройки, и любое изменение задевает всё сразу. Хорошая структура раскладывает код по ответственности: кто принимает HTTP, кто решает бизнес-задачу, кто хранит данные.

У FastAPI нет обязательной структуры. Ниже — распространённый вариант на примере [«Задачника»](../../../practice/projects/tasker/README.md).

## Как разложен «Задачник»

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

## Путь одного запроса

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

## Зачем так делить

- **Сервис можно вызвать не только из HTTP.** Ту же `update_task` можно использовать в фоновой задаче Celery или в CLI-команде.
- **Проще тестировать.** Правила «чужую задачу не видно» проверяются в одном месте.
- **Понятно, где искать.** Ошибка в формате ответа — в схемах, ошибка в правах — в сервисе или зависимостях.

## Подключение роутеров и настройки

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

## Когда добавлять ещё слои

В больших проектах из сервисов выделяют **репозитории**: в них лежат только запросы к БД, а сервисы занимаются правилами. Это помогает, когда запросы сложные и повторяются или когда хочется тестировать правила без базы. В «Задачнике» запросы простые, и отдельный слой был бы лишней церемонией.

Когда сущностей много, файлы `models.py` и `schemas.py` разбивают на пакеты (`models/task.py`, `models/user.py`) или раскладывают код по доменам: `app/tasks/{router,service,models,schemas}.py`.

## Частые ошибки

- **SQL в роутерах.** Через полгода одинаковые запросы оказываются в десяти местах с небольшими отличиями.
- **`HTTPException` в сервисах.** Сервис становится привязан к HTTP. Выбрасывайте свои исключения и превращайте их в ответы обработчиками.
- **Слои ради слоёв.** Три файла на сущность, где каждый просто вызывает следующий, мешают читать код. Добавляйте слой, когда появляется настоящая причина.

## Связанные темы

- [Модули, пакеты и импорты](../../../languages/python/modules/imports.md) — почему запускать нужно из корня проекта
- [Зависимости](dependencies.md)
- [Ошибки и коды ответов](errors.md)
