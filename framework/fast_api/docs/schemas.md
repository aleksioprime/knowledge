# Схемы запросов и ответов

Когда клиент создаёт задачу, он присылает JSON. В нём может не оказаться названия, приоритет может прийти строкой `"3"`, а дата может быть в неправильном формате. Ответ тоже требует внимания: если отдавать объект пользователя целиком, вместе с ним уйдёт хэш пароля. В FastAPI обе задачи решают схемы — модели [Pydantic](../../../python/typing/pydantic.md), которые описывают, что API принимает и что отдаёт.

## Минимальный пример

```python
from datetime import date

from fastapi import FastAPI, status
from pydantic import BaseModel, Field

app = FastAPI()


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    priority: int = Field(default=1, ge=1, le=5)
    due_date: date | None = None


class TaskRead(TaskCreate):
    id: int
    done: bool


@app.post('/tasks', status_code=status.HTTP_201_CREATED)
def create_task(data: TaskCreate) -> TaskRead:
    return TaskRead(id=1, done=False, **data.model_dump())
```

```bash
curl -X POST localhost:8000/tasks -H 'Content-Type: application/json' \
  -d '{"title": "Сдать отчёт", "priority": "3", "due_date": "2026-11-01"}'
# 201 {"title":"Сдать отчёт","priority":3,"due_date":"2026-11-01","id":1,"done":false}
```

Если данные плохие, FastAPI ответит 422, а функция даже не будет вызвана:

```bash
curl -X POST localhost:8000/tasks -H 'Content-Type: application/json' -d '{"title": "", "priority": 9}'
```

```json
{
  "detail": [
    {"type": "string_too_short", "loc": ["body", "title"], "msg": "String should have at least 1 character", "input": ""},
    {"type": "less_than_equal", "loc": ["body", "priority"], "msg": "Input should be less than or equal to 5", "input": 9}
  ]
}
```

## Как это работает

**Аргумент-модель — это тело запроса.** Раз тип аргумента `data` — модель Pydantic, FastAPI читает JSON из тела, проверяет его по модели и передаёт в функцию уже готовый объект. Внутри функции можно не сомневаться, что `title` не пустой, а `priority` — число от 1 до 5.

**Тип результата — это схема ответа.** `-> TaskRead` делает три вещи:

1. ответ проверяется по схеме: если код случайно вернёт что-то не то, ошибка будет видна сразу;
2. **лишние поля отбрасываются**;
3. схема ответа попадает в документацию `/docs`.

Второй пункт защищает от утечек:

```python
class UserRead(BaseModel):
    id: int
    email: str


@app.get('/users/{user_id}')
def get_user(user_id: int) -> UserRead:
    user = {'id': user_id, 'email': 'anna@example.com', 'hashed_password': '$argon2id$...'}
    return user
# {"id":1,"email":"anna@example.com"} — хэша пароля в ответе нет
```

Без `-> UserRead` тот же код отдал бы клиенту и `hashed_password`.

Если функция возвращает не саму схему (как здесь — словарь), mypy будет ругаться на несовпадение типов. Тогда схему указывают в декораторе: `@app.get('/users/{user_id}', response_model=UserRead)`.

**`status_code`** задаёт код успешного ответа. Для создания принято `201 Created`, для удаления без тела — `204 No Content`.

## Несколько схем на одну сущность

Обычно у сущности несколько схем, потому что на разных этапах у неё разный набор полей:

| Схема | Зачем | Чем отличается |
|---|---|---|
| `TaskCreate` | Тело `POST` | Нет `id` и служебных полей — их задаёт сервер |
| `TaskUpdate` | Тело `PATCH` | Все поля необязательные |
| `TaskRead` | Ответ | Есть `id`, `done`, `created_at`; нет секретов |

Для частичного обновления важен `exclude_unset=True`: он оставляет только те поля, которые клиент действительно прислал:

```python
class TaskUpdate(BaseModel):
    title: str | None = None
    done: bool | None = None


# PATCH /tasks/1 с телом {"done": true}
data.model_dump()                    # {'title': None, 'done': True} — затрёт название!
data.model_dump(exclude_unset=True)  # {'done': True}
```

**Ответ из объекта SQLAlchemy.** Чтобы Pydantic умел читать атрибуты объекта, а не только ключи словаря, в схеме ответа включают `from_attributes`:

```python
from pydantic import ConfigDict


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
```

Так сделано в [«Задачнике»](../../../pet/tasker/app/schemas.py).

## Параметры запроса с ограничениями

Ограничения можно задавать не только полям тела, но и параметрам строки запроса — через `Query`:

```python
from typing import Annotated

from fastapi import Query


@app.get('/tasks')
def list_tasks(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
): ...

# GET /tasks?limit=500 → 422: Input should be less than or equal to 100
```

## Частые ошибки

- **Одна модель на всё.** Если `id` есть в схеме создания, клиент сможет задать его сам. Разделяйте схемы для входа и выхода.
- **`model_dump()` в `PATCH`.** Без `exclude_unset=True` непереданные поля превратятся в `None` и затрут данные.
- **Отдавать модель БД без схемы ответа.** Наружу уйдут все колонки, включая служебные и секретные.
- **Неверный `Content-Type`.** С заголовком вроде `text/plain` FastAPI не станет читать тело как JSON и вернёт 422 `Input should be a valid dictionary`. В новых версиях FastAPI так же будет и вовсе без заголовка, поэтому всегда отправляйте `Content-Type: application/json`.

## Связанные темы

- [Pydantic](../../../python/typing/pydantic.md)
- [Зависимости](dependencies.md)
- [Ошибки и коды ответов](errors.md)
