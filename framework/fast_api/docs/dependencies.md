# Зависимости (`Depends`)

Почти каждому эндпоинту «Задачника» нужно одно и то же: открыть сессию базы данных и закрыть её после запроса, узнать текущего пользователя по токену, прочитать параметры пагинации. Если писать это в каждой функции, код повторяется, а забыть закрыть соединение очень легко. В FastAPI общее выносят в **зависимости**: функция объявляет, что ей нужно, и FastAPI готовит это перед вызовом.

## Минимальный пример

```python
from typing import Annotated

from fastapi import Depends, FastAPI, Query

app = FastAPI()


def pagination(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    return {'limit': limit, 'offset': offset}


Pagination = Annotated[dict, Depends(pagination)]


@app.get('/tasks')
def list_tasks(page: Pagination):
    return page


@app.get('/users')
def list_users(page: Pagination):
    return page
```

```bash
curl 'localhost:8000/tasks?limit=5'  # {"limit":5,"offset":0}
curl localhost:8000/users            # {"limit":20,"offset":0}
curl 'localhost:8000/tasks?limit=0'  # 422 — проверки работают и внутри зависимости
```

Пагинация описана один раз, а пользуются ею оба эндпоинта. В документации `/docs` параметры `limit` и `offset` появятся у обоих.

## Как это работает

`Depends(func)` говорит FastAPI: «перед вызовом эндпоинта вызови `func` и подставь результат сюда». У самой зависимости тоже могут быть параметры: строка запроса, заголовки, тело и даже другие зависимости. FastAPI разбирает их так же, как параметры эндпоинта.

Запись `Annotated[тип, Depends(...)]` удобно сохранить в переменную (`Pagination`, `SessionDep`, `CurrentUser`), чтобы не повторять её в каждой функции.

В пределах одного запроса каждая зависимость вызывается один раз, даже если её запросили несколько других зависимостей.

## Ресурс с очисткой: `yield`

Если зависимость открывает ресурс, его нужно закрыть, даже когда эндпоинт упал. Для этого зависимость пишут с `yield`: код до `yield` выполняется перед запросом, код после — по его завершении:

```python
def get_db():
    print('открыли соединение')
    try:
        yield 'db-connection'
    finally:
        print('закрыли соединение')


@app.get('/ping-db')
def ping(db: Annotated[str, Depends(get_db)]):
    print('обрабатываем запрос')
    return {'db': db}

# открыли соединение
# обрабатываем запрос
# закрыли соединение
```

Так в «Задачнике» устроена сессия базы данных — [`get_session`](../../../pet/tasker/app/core/database.py):

```python
async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
```

## Цепочки зависимостей: пользователь и права

Зависимость может зависеть от другой. Так строят проверки доступа: сначала узнаём пользователя, затем проверяем его права:

```python
from fastapi import Header, HTTPException

USERS = {'token-anna': 'Анна'}


def current_user(x_token: Annotated[str, Header()]) -> str:
    if x_token not in USERS:
        raise HTTPException(status_code=401, detail='Неверный токен')
    return USERS[x_token]


def admin_only(user: Annotated[str, Depends(current_user)]) -> str:
    if user != 'Админ':
        raise HTTPException(status_code=403, detail='Нужны права администратора')
    return user


@app.get('/me')
def me(user: Annotated[str, Depends(current_user)]):
    return {'user': user}


@app.delete('/tasks')
def clear_tasks(user: Annotated[str, Depends(admin_only)]):
    return {'ok': True}
```

```bash
curl localhost:8000/me -H 'X-Token: token-anna'              # {"user":"Анна"}
curl localhost:8000/me -H 'X-Token: bad'                     # 401 {"detail":"Неверный токен"}
curl -X DELETE localhost:8000/tasks -H 'X-Token: token-anna' # 403 {"detail":"Нужны права администратора"}
```

Если зависимость выбросила `HTTPException`, эндпоинт не вызывается. Поэтому проверку прав достаточно написать один раз.

## Подмена зависимостей в тестах

Тесты не должны ходить в рабочую базу. FastAPI позволяет подменить любую зависимость:

```python
app.dependency_overrides[get_session] = get_test_session
```

Все эндпоинты, которым нужна `get_session`, получат тестовую сессию. Так устроены [тесты «Задачника»](../../../pet/tasker/tests/conftest.py).

## Частые ошибки

- **Вызвать зависимость вместо передачи.** `Depends(get_session())` — ошибка: нужно передать саму функцию, `Depends(get_session)`.
- **Забыть `try/finally` в зависимости с `yield`.** Тогда код очистки не выполнится, если эндпоинт выбросил исключение. `async with` и `with` делают это за вас.
- **Тяжёлая логика в зависимостях.** Зависимость должна подготовить ресурс или проверить доступ. Бизнес-логику лучше держать в сервисах — см. [структуру проекта](structure.md).

## Связанные темы

- [Авторизация по JWT](auth_jwt.md) — `CurrentUser` на настоящих токенах
- [Структура проекта](structure.md)
- [Менеджеры контекста](../../../python/function/function.ipynb)
