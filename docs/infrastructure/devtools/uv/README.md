# uv

**uv** — сверхбыстрый менеджер пакетов и проектов для Python от Astral (авторов Ruff). Написан на Rust, в 10–100× быстрее `pip` и `poetry`.

Один инструмент заменяет: `pip`, `pip-tools`, `pipx`, `virtualenv`, `pyenv` и частично `poetry`.

## Содержание

- [Сценарии использования](scenarios.md) — установка Python, создание проекта, lock-файл, tool-режим, PEP 723

## Установка

```sh
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# через Homebrew
brew install uv

# через pipx
pipx install uv
```

## Управление интерпретаторами Python

```sh
uv python install 3.12                # скачать готовый бинарник
uv python install 3.11 3.12 3.13      # сразу несколько
uv python list                        # установленные + доступные
uv python pin 3.12                    # зафиксировать для проекта (.python-version)
uv python find 3.12                   # путь к интерпретатору
```

Качает готовые сборки (быстрее, чем `pyenv`, который компилирует).

## Проектный режим (замена Poetry)

### Новый проект
```sh
uv init my-app
cd my-app
```

Создаст структуру с `pyproject.toml`, `.python-version`, `README.md`, `main.py`.

### Управление зависимостями
```sh
uv add fastapi                        # добавить пакет
uv add --dev pytest                   # в dev-группу
uv add 'sqlalchemy>=2.0'              # с версией
uv add --optional redis-extra redis   # опциональная

uv remove fastapi

uv sync                               # установить всё из lock-файла
uv sync --no-dev                      # без dev-зависимостей (для прода)
uv lock                               # перегенерировать uv.lock
uv lock --upgrade                     # обновить версии

uv tree                               # дерево зависимостей
```

### Запуск кода
```sh
uv run python main.py                 # запустить в venv проекта
uv run pytest
uv run fastapi dev                    # запустить установленный пакет
```

`uv run` сам создаёт/обновляет venv, ставит зависимости — без отдельного `activate`.

## pip-совместимый режим

Если нужно работать как с обычным pip:
```sh
uv venv                               # создать .venv
source .venv/bin/activate

uv pip install fastapi
uv pip install -r requirements.txt
uv pip freeze
uv pip list
uv pip uninstall fastapi
uv pip compile pyproject.toml -o requirements.txt   # как pip-tools
```

## Запуск инструментов (как pipx)

```sh
uv tool install ruff                  # глобально установить CLI
uv tool list
uv tool run ruff check                # = uvx
uvx black --check .                   # alias для uv tool run
uv tool upgrade ruff
uv tool uninstall ruff
```

## pyproject.toml в uv-проекте

```toml
[project]
name = "my-app"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "sqlalchemy>=2.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "ruff>=0.5",
]

[tool.uv]
package = true
```

В отличие от Poetry, uv использует **стандартный PEP 621**-формат — без `[tool.poetry]`.

## Запуск скриптов с inline-зависимостями (PEP 723)

uv умеет читать заголовок прямо в скрипте:
```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx",
#     "rich",
# ]
# ///

import httpx
from rich import print
print(httpx.get("https://httpbin.org/get").json())
```

```sh
uv run script.py
```

uv сам создаст временный venv с указанными зависимостями. Удобно для одноразовых скриптов.

## Производительность

| Операция | pip | poetry | uv |
|---|---|---|---|
| Установка Django + deps | ~10 с | ~30 с | ~0.5 с |
| Resolve большого проекта | ~30 с | ~60 с | ~1 с |

Секрет — параллельная загрузка, кеш на диске и быстрый resolver на Rust.

## Когда брать uv

- Новый проект → бери uv.
- Большой репозиторий с долгим pip install → бери uv.
- Стабильный проект на Poetry → можно не мигрировать, но мигрировать тоже легко (`uv init --package` + `uv add` зависимостей).
