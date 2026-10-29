# uv

Чтобы поднять Python-проект, обычно нужно четыре инструмента: pyenv для интерпретатора, venv для изоляции, pip или Poetry для зависимостей, pipx для утилит, и каждый из них работает медленно. **uv** от Astral (авторов Ruff) заменяет их все: ставит интерпретаторы, создаёт окружения, разрешает и фиксирует зависимости, запускает скрипты и утилиты, причём в 10–100 раз быстрее `pip` и `poetry` за счёт реализации на Rust.

## Содержание

- [Сценарии использования](scenarios.md) — установка Python, создание проекта, lock-файл, tool-режим, PEP 723

## Минимальный пример

Новый проект с нуля: интерпретатор, venv, зависимости и lock-файл появляются сами.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh    # или brew install uv

uv init tasker --python 3.12
# Initialized project `tasker` at `/Users/me/projects/tasker`
cd tasker
ls -A
# .git  .gitignore  .python-version  README.md  pyproject.toml  src

uv add httpx                      # Resolved 8 packages ... + httpx==0.28.1
uv add --dev pytest               # + pytest==9.2.0

uv run python -c "import httpx; print(httpx.__version__)"
# 0.28.1

uv tree --depth 1
# tasker v0.1.0
# ├── httpx v0.28.1
# └── pytest v9.2.0 (group: dev)
```

Отдельного `source .venv/bin/activate` не нужно: `uv run` сам создаёт `.venv`, синхронизирует его с `uv.lock` и запускает команду внутри.

## Как это работает

uv хранит скачанные пакеты в общем кеше (`~/.cache/uv`) и в каждый `.venv` не копирует файлы, а делает жёсткие ссылки, поэтому повторная установка почти мгновенная. Зависимости разрешает свой резолвер на Rust, результат записывается в `uv.lock` — кроссплатформенный lock с точными версиями и хешами. Перед каждым `uv run` и `uv sync` uv проверяет, что `.venv` соответствует lock-файлу, и при расхождении доустанавливает или удаляет пакеты.

### Установка

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# через Homebrew
brew install uv

# через pipx
pipx install uv
```

### Управление интерпретаторами Python

```bash
uv python install 3.12                # скачать готовый бинарник
uv python install 3.11 3.12 3.13      # сразу несколько
uv python list                        # установленные + доступные
uv python pin 3.12                    # зафиксировать для проекта (.python-version)
uv python find 3.12                   # путь к интерпретатору
```

Качает готовые сборки (быстрее, чем `pyenv`, который компилирует).

### Проектный режим (замена Poetry)

Новый проект:

```bash
uv init my-app
cd my-app
```

Создаст `pyproject.toml`, `.python-version`, `README.md`, `.gitignore` и пакет с точкой входа (в новых версиях — в `src/`, в старых — `main.py` в корне). Флаги `--app`, `--lib`, `--package` меняют заготовку.

Управление зависимостями:

```bash
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

Запуск кода:

```bash
uv run python main.py                 # запустить в venv проекта
uv run pytest
uv run fastapi dev                    # запустить установленный пакет
```

`uv run` сам создаёт/обновляет venv, ставит зависимости — без отдельного `activate`.

### pip-совместимый режим

Если нужно работать как с обычным pip:

```bash
uv venv                               # создать .venv
source .venv/bin/activate

uv pip install fastapi
uv pip install -r requirements.txt
uv pip freeze
uv pip list
uv pip uninstall fastapi
uv pip compile pyproject.toml -o requirements.txt   # как pip-tools
```

### Запуск инструментов (как pipx)

```bash
uv tool install ruff                  # глобально установить CLI
uv tool list
uv tool run ruff check                # = uvx
uvx black --check .                   # alias для uv tool run
uv tool upgrade ruff
uv tool uninstall ruff
```

### pyproject.toml в uv-проекте

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

В отличие от классического Poetry, uv использует стандартный формат PEP 621 (`[project]`) и PEP 735 (`[dependency-groups]`) — без секции `[tool.poetry]`.

### Запуск скриптов с inline-зависимостями (PEP 723)

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

```bash
uv run script.py
```

uv сам создаст временный venv с указанными зависимостями. Удобно для одноразовых скриптов.

### Производительность

| Операция | pip | poetry | uv |
|---|---|---|---|
| Установка Django + deps | ~10 с | ~30 с | ~0.5 с |
| Resolve большого проекта | ~30 с | ~60 с | ~1 с |

Секрет — параллельная загрузка, кеш на диске с жёсткими ссылками и быстрый резолвер на Rust.

## Частые ошибки

- Активировали `.venv` вручную и поставили пакет через `pip install` → при следующем `uv run` или `uv sync` пакет исчезает, потому что его нет в `uv.lock` → добавлять через `uv add`, а разовые эксперименты делать через `uv pip install` с пониманием, что sync их откатит.
- `uv.lock` не закоммичен → в CI и у коллег другие версии → коммитить lock; в CI использовать `uv sync --locked`, чтобы сборка падала, если lock устарел.
- `uv sync` на проде ставит pytest и ruff → лишние пакеты в образе → `uv sync --no-dev` (или `--only-group main`).
- Поставили утилиту в проект (`uv add ruff`) вместо `uv tool install ruff` → она тянется как зависимость приложения → для CLI-инструментов использовать `uv tool install` или `uvx`.
- `uv run` в Docker пересобирает окружение на каждом запуске → слой с зависимостями не кешируется → сначала копировать `pyproject.toml` и `uv.lock`, выполнить `uv sync --frozen --no-dev --no-install-project`, и только потом копировать код.
- Проект на Poetry с `[tool.poetry.dependencies]` → `uv sync` не видит зависимостей → перенести их в `[project].dependencies` (`uv init` в существующей папке подскажет структуру) или временно работать через `uv pip`.

## Когда не использовать

Если проект стабильно живёт на Poetry и команда к нему привыкла, миграция ради скорости не обязательна: формат совместим, переехать можно позже. Для data science со сложными бинарными зависимостями (CUDA, MKL) по-прежнему удобнее conda, а чисто системный Python в контейнере с одним `requirements.txt` можно ставить и `pip`'ом. Ограничение uv — он не управляет версиями других языков: для Python + Node в одном проекте смотрите [mise](../env_management/README.md).

## Что спрашивают на собеседовании

- Чем uv отличается от pip и Poetry? *(Один инструмент вместо pip, venv, pip-tools, pipx и pyenv; стандартный `pyproject.toml`; скорость за счёт Rust, кеша и жёстких ссылок.)*
- Зачем нужен `uv.lock` и чем он отличается от `requirements.txt`? *(Точные версии всех пакетов для всех платформ с хешами; `requirements.txt` — плоский список без транзитивных гарантий.)*
- Как uv запускает код без `activate`? *(`uv run` находит `.venv` проекта, синхронизирует его с lock и запускает команду внутри.)*
- Что такое PEP 723 и как uv его использует? *(Зависимости в заголовке скрипта; `uv run script.py` ставит их во временное окружение.)*
- Почему `uv sync` удалил пакет, который я поставил pip'ом? *(sync приводит окружение в точное соответствие с lock-файлом.)*

## Связанные темы

- [uv: сценарии использования](scenarios.md)
- [Poetry](../poetry/README.md)
- [pyenv](../pyenv/README.md)
- [pipx](../pipx/README.md)
- [Task Runners](../task_runners/README.md)
