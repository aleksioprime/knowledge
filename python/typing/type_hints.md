# Подсказки типов (type hints)

Python не требует указывать типы, и в маленьком скрипте это удобно. Но в проекте на сотни функций быстро забываешь, что возвращает `find_user()`: пользователя, его имя или `None`. Подсказки типов записывают это прямо в коде, а проверяльщик вроде `mypy` находит ошибку до запуска.

## Минимальный пример

```python
users = {1: 'Анна', 2: 'Борис'}


def find_user(user_id: int) -> str | None:
    return users.get(user_id)


name = find_user(3)
print(name.upper())
```

Python запустит этот код и упадёт только на последней строке: `AttributeError: 'NoneType' object has no attribute 'upper'`. А `mypy` найдёт ошибку сразу, ничего не запуская:

```bash
pip install mypy
mypy app.py
# app.py:9: error: Item "None" of "str | None" has no attribute "upper"  [union-attr]
```

Исправление — явно обработать случай, когда пользователя нет:

```python
name = find_user(3)
if name is not None:
    print(name.upper())
```

## Как это работает

Подсказка — это пометка для людей и инструментов. Сам Python её **не проверяет**:

```python
def add(a: int, b: int) -> int:
    return a + b


print(add('2', '3'))  # 23 — Python не возражает
```

Проверяют типы внешние инструменты: `mypy`, `pyright`, встроенный анализатор в VS Code и PyCharm. Ещё подсказки читают библиотеки: FastAPI и Pydantic по ним валидируют данные из запроса.

## Основной синтаксис

```python
count: int = 0
title: str = 'Купить хлеб'
tags: list[str] = ['дом', 'покупки']
scores: dict[str, int] = {'Анна': 5}
point: tuple[int, int] = (10, 20)
ids: set[int] = {1, 2, 3}


def greet(name: str, times: int = 1) -> str:
    return f'Привет, {name}! ' * times


def log(message: str) -> None:  # функция ничего не возвращает
    print(message)
```

Синтаксис `list[str]` и `str | None` работает с Python 3.9 и 3.10 соответственно. В старом коде встретятся `List[str]` и `Optional[str]` из модуля `typing` — это то же самое.

## Полезные типы из `typing`

**`Literal`** — допустимы только перечисленные значения:

```python
from typing import Literal

Priority = Literal['low', 'normal', 'high']


def set_priority(priority: Priority) -> None: ...


set_priority('urgent')
# error: Argument 1 has incompatible type "Literal['urgent']"; expected "Literal['low', 'normal', 'high']"
```

**`TypedDict`** — словарь с известными ключами. Удобен для JSON, который не хочется превращать в класс:

```python
from typing import TypedDict


class TaskDict(TypedDict):
    title: str
    done: bool


task: TaskDict = {'title': 'Купить хлеб', 'done': False}
```

**`Callable`** — функция как аргумент:

```python
from collections.abc import Callable


def apply(value: int, func: Callable[[int], int]) -> int:
    return func(value)


apply(5, lambda x: x * 2)  # 10
```

**`Protocol`** — «утиная типизация» с проверкой. Важно не наследование, а наличие нужных методов:

```python
from typing import Protocol


class Notifier(Protocol):
    def send(self, text: str) -> None: ...


class EmailNotifier:
    def send(self, text: str) -> None:
        print('Письмо:', text)


class TelegramNotifier:
    def post(self, text: str) -> None:
        print('Telegram:', text)


def remind(notifier: Notifier) -> None:
    notifier.send('Срок задачи истекает завтра')


remind(EmailNotifier())     # подходит: есть метод send
remind(TelegramNotifier())  # error: incompatible type "TelegramNotifier"; expected "Notifier"
```

**Обобщённые функции (generics)** — тип результата зависит от типа аргумента. В Python 3.12 параметр типа пишут в квадратных скобках:

```python
def first[T](items: list[T]) -> T:
    return items[0]


first([1, 2, 3])     # mypy знает, что это int
first(['a', 'b'])    # а здесь — str
```

До 3.12 то же самое записывали через `T = TypeVar('T')`.

## Частые ошибки

- **Ждать, что Python проверит типы сам.** Без `mypy` или IDE подсказки — просто комментарии. Добавьте `mypy` в линтеры или CI.
- **`Any` везде, где лень думать.** `Any` выключает проверку, и ошибки снова видны только при запуске. Если тип действительно неизвестен, лучше `object`: с ним `mypy` заставит проверить тип перед использованием.
- **Изменяемое значение по умолчанию.** `def add(tags: list[str] = [])` — один и тот же список на все вызовы. Пишите `tags: list[str] | None = None` и создавайте список внутри.
- **Забытый `None` в результате.** Если функция может ничего не найти, честно пишите `-> User | None` — тогда `mypy` напомнит про проверку везде, где её забыли.

## Когда не использовать

В коротких скриптах и ноутбуках для экспериментов подсказки можно не писать. А в коде, который читают другие люди и который живёт дольше недели, они окупаются почти сразу.

## Связанные темы

- [dataclasses](dataclasses.md) — классы данных, построенные на подсказках типов
- [Pydantic](pydantic.md) — проверка типов во время выполнения
- [Линтеры](../../devtools/linter/README.md)
