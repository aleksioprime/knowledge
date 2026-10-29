# Модули, пакеты и импорты

Пока код живёт в одном файле, импорты не вызывают вопросов. Проблемы начинаются, когда файлов становится много: один и тот же `import` работает из одной папки и падает из другой, а `python app/main.py` выдаёт `ModuleNotFoundError`, хотя файл точно на месте. Достаточно понять, где Python ищет модули, — и эти ошибки перестают быть загадкой.

## Минимальный пример

Проект «Задачник» из двух файлов:

```text
tasker/
└── app/
    ├── __init__.py
    ├── main.py
    └── services.py
```

```python
# app/services.py
def count_tasks(tasks: list[str]) -> int:
    return len(tasks)
```

```python
# app/main.py
from app.services import count_tasks

print(count_tasks(['Купить хлеб', 'Позвонить маме']))
```

Запускаем из папки `tasker/`:

```bash
python app/main.py
# ModuleNotFoundError: No module named 'app'

python -m app.main
# 2
```

## Как это работает

**Модуль** — это любой `.py`-файл. **Пакет** — папка с модулями. Файл `__init__.py` помечает папку как обычный пакет и выполняется при первом импорте.

Когда Python встречает `import app.services`, он ищет `app` по очереди в папках из списка `sys.path`. Первая папка в этом списке зависит от способа запуска:

- `python app/main.py` — папка самого скрипта, то есть `tasker/app/`. Внутри неё нет папки `app`, поэтому импорт падает.
- `python -m app.main` — текущая папка, то есть `tasker/`. В ней `app` есть, и всё работает.

Отсюда простое правило: **запускайте код как модуль из корня проекта**. Так же работают uvicorn и pytest: `uvicorn app.main:app` ищет `app` в текущей папке.

Остальные пункты `sys.path` — стандартная библиотека и установленные пакеты (`site-packages`). Посмотреть список можно так:

```python
import sys

print(sys.path)
```

## Виды импорта

```python
import json                        # весь модуль: json.dumps(...)
from datetime import date          # одно имя из модуля
from app.services import count_tasks as count  # под другим именем
from . import services             # относительный: из того же пакета
from .services import count_tasks  # относительный: модуль рядом
from ..core import config          # относительный: на уровень выше
```

**Абсолютные импорты** (`from app.services import …`) читаются однозначно, поэтому в проектах обычно выбирают их. **Относительные** (`from .services import …`) удобны внутри пакета, но работают только при запуске через `-m`:

```bash
python app/main.py
# ImportError: attempted relative import with no known parent package
```

`from module import *` лучше не писать: непонятно, откуда взялось имя, и одно имя может незаметно перекрыть другое.

## `if __name__ == '__main__'`

При импорте Python выполняет весь код модуля. Чтобы файл можно было и импортировать, и запускать как скрипт, код запуска прячут под проверку:

```python
# app/tool.py
def slugify(text: str) -> str:
    return text.lower().replace(' ', '-')


if __name__ == '__main__':
    print(slugify('Купить хлеб'))
```

```bash
python -m app.tool
# купить-хлеб

python -c "from app.tool import slugify"
# (ничего не выводится: при импорте __name__ равен 'app.tool')
```

## Модуль выполняется один раз

После первого импорта модуль сохраняется в `sys.modules`, и повторный `import` берёт его оттуда. Поэтому код верхнего уровня модуля (подключение к базе, чтение настроек) выполнится один раз, сколько бы файлов его ни импортировали. На этом и держится простой способ сделать «одиночку»: объект настроек, созданный в `config.py`, будет общим для всего приложения.

## Частые ошибки

**Циклический импорт.** `users.py` импортирует `tasks.py`, а `tasks.py` — `users.py`:

```text
ImportError: cannot import name 'User' from partially initialized module 'app.users' (most likely due to a circular import)
```

Python начал загружать `users`, дошёл до импорта `tasks`, а тот попросил `User`, который ещё не успел определиться. Решения по порядку предпочтения: вынести общее в третий модуль; импортировать внутри функции, где он нужен; для подсказок типов — импорт под `if TYPE_CHECKING:`.

**Свой файл с именем стандартного модуля.** Файл `random.py` в папке проекта перекроет стандартный `random`:

```python
# game.py
import random

print(random.randint(1, 6))
# AttributeError: module 'random' has no attribute 'randint'
```

Не называйте файлы `random.py`, `json.py`, `email.py`, `test.py` и т. п.

**Правка `sys.path` в коде.** `sys.path.append('..')` чинит импорт здесь и сейчас, но ломается при запуске из другой папки. Лучше запускать через `-m` из корня или установить проект как пакет (`pip install -e .`, [uv](../../../infrastructure/devtools/uv/README.md), [Poetry](../../../infrastructure/devtools/poetry/README.md)).

## Связанные темы

- [Подсказки типов](../typing/type_hints.md) — `TYPE_CHECKING` для импортов только ради типов
- [Управление окружением](../../../infrastructure/devtools/env_management/README.md)
