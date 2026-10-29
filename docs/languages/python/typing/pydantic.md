# Pydantic

Данные из внешнего мира почти никогда не бывают такими, как ожидает код. В JSON число приходит строкой `"3"`, дата — строкой `"2026-11-01"`, а обязательное поле может просто отсутствовать. Pydantic берёт описание данных на подсказках типов, проверяет входные данные, приводит их к нужным типам и понятно сообщает, что не так.

Именно на Pydantic FastAPI проверяет тело запроса.

```bash
pip install pydantic
```

## Минимальный пример

```python
from datetime import date

from pydantic import BaseModel


class Task(BaseModel):
    title: str
    priority: int = 1
    due_date: date | None = None


task = Task.model_validate({'title': 'Купить хлеб', 'priority': '3', 'due_date': '2026-11-01'})

print(task)           # title='Купить хлеб' priority=3 due_date=datetime.date(2026, 11, 1)
print(task.priority)  # 3 — уже число, а не строка
```

А если данные плохие, Pydantic перечислит все проблемы сразу, а не только первую:

```python
Task.model_validate({'priority': 'высокий', 'due_date': 'завтра'})
```

```text
3 validation errors for Task
title
  Field required [type=missing, ...]
priority
  Input should be a valid integer, unable to parse string as an integer [type=int_parsing, ...]
due_date
  Input should be a valid date or datetime, invalid character in year [type=date_from_datetime_parsing, ...]
```

## Как это работает

Модель — это класс-наследник `BaseModel` с полями и типами. При создании объекта Pydantic проходит по полям и для каждого:

1. проверяет, что значение есть (или берёт значение по умолчанию);
2. пытается привести его к нужному типу: `'3'` → `3`, `'2026-11-01'` → `date`;
3. если не получилось — запоминает ошибку и идёт дальше.

В конце либо возвращает готовый объект, либо выбрасывает `ValidationError` со списком всех ошибок.

В отличие от [dataclasses](dataclasses.md), где аннотации — только подсказка, здесь они правила.

## Основные приёмы

**Из модели — в словарь и JSON:**

```python
task.model_dump()       # {'title': 'Купить хлеб', 'priority': 3, 'due_date': datetime.date(2026, 11, 1)}
task.model_dump_json()  # '{"title":"Купить хлеб","priority":3,"due_date":"2026-11-01"}'

Task.model_validate_json('{"title": "Отчёт"}')  # title='Отчёт' priority=1 due_date=None
```

**Ограничения на значения — `Field`:**

```python
from pydantic import BaseModel, Field


class Task(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    priority: int = Field(default=1, ge=1, le=5)  # от 1 до 5


Task(title='', priority=10)
# title: String should have at least 1 character
# priority: Input should be less than or equal to 5
```

**Своя проверка — `field_validator`:**

```python
from pydantic import BaseModel, field_validator


class User(BaseModel):
    name: str

    @field_validator('name')
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError('имя не может быть пустым')
        return value.title()


User(name='  анна  ')  # name='Анна'
User(name='  ')        # Value error, имя не может быть пустым
```

**Вложенные модели** проверяются целиком, на любой глубине:

```python
class Project(BaseModel):
    name: str
    tasks: list[Task] = []


Project.model_validate({'name': 'Дом', 'tasks': [{'title': 'Помыть окна'}]})
# name='Дом' tasks=[Task(title='Помыть окна', priority=1, due_date=None)]
```

**Отдельные схемы для входа и выхода.** Клиент присылает задачу без `id`, а сервер возвращает с `id`. Так устроен и [«Задачник»](../../../practice/projects/tasker/app/main.py):

```python
class TaskCreate(BaseModel):
    title: str


class TaskRead(TaskCreate):
    id: int
    done: bool
```

**Лишние поля.** По умолчанию Pydantic молча их отбрасывает. Если клиент прислал то, чего не должно быть, иногда лучше сообщить об ошибке:

```python
class TaskCreate(BaseModel):
    model_config = {'extra': 'forbid'}

    title: str


TaskCreate(title='Отчёт', is_admin=True)
# is_admin: Extra inputs are not permitted
```

## Настройки приложения

Отдельный пакет `pydantic-settings` читает настройки из переменных окружения и `.env`-файла и проверяет их так же, как модели:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env')

    database_url: str
    debug: bool = False


settings = Settings()
```

```bash
DATABASE_URL=postgresql://tasker@localhost/tasker DEBUG=1 python app.py
# database_url='postgresql://tasker@localhost/tasker' debug=True
```

Если `DATABASE_URL` не задан, приложение упадёт сразу при старте с `Field required`, а не через час на первом запросе к базе.

## Частые ошибки

- **Код из Pydantic 1.** В старых статьях встречаются `.dict()`, `.json()`, `parse_obj()` и `@validator`. В Pydantic 2 это `model_dump()`, `model_dump_json()`, `model_validate()` и `@field_validator`.
- **Ждать, что `int` не примет строку.** По умолчанию Pydantic приводит `'3'` к `3`. Если нужна строгая проверка, используйте `Field(strict=True)` или `model_config = {'strict': True}`.
- **Модели Pydantic как модели БД.** Схемы API и таблицы базы — разные вещи: в таблице есть пароль, а в ответе API его быть не должно. Держите их отдельно.

## Когда не использовать

Для внутренних структур, которые создаёт сам код и которые не нужно проверять, Pydantic избыточен — хватит [dataclasses](dataclasses.md). Проверка стоит времени, и в горячем цикле на миллионы объектов это заметно.

## Связанные темы

- [Подсказки типов](type_hints.md)
- [dataclasses](dataclasses.md)
- [FastAPI](../../../backend/frameworks/fastapi/README.md)
