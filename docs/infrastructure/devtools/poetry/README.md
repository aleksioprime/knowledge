# Poetry

Пока зависимости ставятся через `pip install` по памяти, проект нельзя воспроизвести: у коллеги другие версии, на сервере не хватает пакета, а `requirements.txt` давно разошёлся с реальностью. **Poetry** описывает проект и зависимости в `pyproject.toml`, фиксирует точные версии в `poetry.lock`, сам создаёт виртуальное окружение и одной командой собирает и публикует пакет.

## Содержание

- [Сценарии использования](scenarios.md) — создание проекта, управление зависимостями, экспорт, публикация

## Минимальный пример

Новый проект с одной рабочей и одной dev-зависимостью. Poetry сам создаёт venv и lock-файл.

```bash
pipx install poetry

poetry new tasker --src
cd tasker
ls
# README.md  pyproject.toml  src  tests

poetry add httpx                  # Using version ^0.28.1 for httpx ... Writing lock file
poetry add --group dev pytest     # Using version ^8.3 for pytest

poetry run python -c "import httpx; print(httpx.__version__)"
# 0.28.1

ls
# README.md  poetry.lock  pyproject.toml  src  tests
```

`poetry.lock` коммитится вместе с `pyproject.toml`: `poetry install` на другой машине поставит те же версии.

## Как это работает

`pyproject.toml` — это «что я хочу»: пакеты и допустимые диапазоны версий. `poetry.lock` — «что получилось»: точные версии всех пакетов, включая транзитивные, с хешами. Команды `add`, `remove`, `update` меняют оба файла, `install` читает только lock. Сами пакеты ставятся в отдельный venv проекта, поэтому системный Python не затрагивается.

### Установка

Рекомендуемый способ — через `pipx` (не засоряет системный Python):

```bash
pipx install poetry
```

Альтернатива — официальный установщик:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### Начало работы

Новый проект:

```bash
poetry new my-app           # README, pyproject.toml, пакет и tests/
poetry new my-app --src     # то же, но пакет внутри src/
cd my-app
```

Существующий проект:

```bash
cd my-existing-project
poetry init                 # интерактивно создаст pyproject.toml
```

### Структура pyproject.toml

```toml
[tool.poetry]
name = "my-app"
version = "0.1.0"
description = "My awesome app"
authors = ["Your Name <you@example.com>"]
readme = "README.md"
packages = [{include = "my_app", from = "src"}]

[tool.poetry.dependencies]
python = "^3.12"
fastapi = "^0.115.0"
sqlalchemy = "^2.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
black = "^24.0"
ruff = "^0.5"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

Начиная с Poetry 2 метаданные можно описывать в стандартной секции `[project]` (PEP 621), как в uv; секция `[tool.poetry]` остаётся для специфичных настроек. Оба варианта работают.

### Управление зависимостями

```bash
poetry add fastapi                    # добавить в основные
poetry add --group dev pytest         # добавить в dev-группу
poetry add 'sqlalchemy@^2.0'          # с версией
poetry add --optional redis           # опциональная зависимость

poetry remove fastapi
poetry update                         # обновить все по правилам ^/~
poetry update fastapi                 # одну
poetry lock                           # перегенерировать lock
poetry lock --no-update               # без обновления версий (в Poetry 2 это поведение по умолчанию)

poetry install                        # установить из lock
poetry install --without dev          # без dev-зависимостей (для прода)
poetry install --only main            # только main группа
```

### Виртуальное окружение

```bash
poetry env info                       # инфа про venv
poetry env list                       # список venv проекта
poetry env use python3.12             # выбрать интерпретатор

poetry run python script.py           # выполнить команду в venv
poetry run pytest
poetry env activate                   # Poetry 2: печатает команду активации
poetry shell                          # Poetry 1; в Poetry 2 — отдельный плагин poetry-plugin-shell
```

По умолчанию Poetry создаёт venv в `~/.cache/pypoetry/virtualenvs/`. Чтобы класть его рядом с проектом:

```bash
poetry config virtualenvs.in-project true
```

Тогда появится `.venv/` в корне проекта — его видит IDE и проще удалить вместе с проектом.

### Сборка и публикация

```bash
poetry build                          # собрать wheel и sdist в dist/
poetry publish                        # выложить на PyPI
poetry publish -r testpypi            # на TestPyPI
poetry config pypi-token.pypi <token> # настроить токен
```

### Семвер в Poetry

```
fastapi = "^0.115.0"   →  >=0.115.0, <0.116.0   (caret — фиксирует первую ненулевую часть)
fastapi = "^1.2.0"     →  >=1.2.0, <2.0.0
fastapi = "~0.115.0"   →  >=0.115.0, <0.116.0   (tilde — фиксирует major+minor)
fastapi = "0.115.0"    →  ровно 0.115.0
fastapi = "*"          →  любая
fastapi = ">=0.115,<1"
```

Для версий `0.x` поведение `^` отличается от других пакетных менеджеров: `^0.115` = `>=0.115, <0.116`, а не `<1.0`.

### Экспорт в requirements.txt (для Docker / CI)

Нужен плагин `poetry-plugin-export` (ставится один раз: `poetry self add poetry-plugin-export`).

```bash
poetry export -f requirements.txt --output requirements.txt --without-hashes
poetry export --only main -f requirements.txt -o requirements.txt
```

### Запуск своих CLI-команд

В `pyproject.toml`:

```toml
[tool.poetry.scripts]
my-app = "my_app.main:cli"
```

После `poetry install` команда `my-app` будет доступна в venv.

### Poetry vs альтернативы

| Инструмент | Когда выбрать |
|---|---|
| **Poetry** | Удобный сборщик + менеджер. Зрелый, много адопта. |
| **uv** | Быстрее в 10–100×. Может всё то же + ставит интерпретаторы. |
| **pip + venv + pip-tools** | Минималистичный «школьный» стек. |
| **pipenv** | Старая альтернатива, развитие замедлилось. |

## Частые ошибки

- `poetry.lock` не закоммичен → у коллег и в CI ставятся другие версии, баг «у меня работает» → коммитить lock вместе с `pyproject.toml`, в CI ставить через `poetry install`.
- `fastapi = "^0.115"` воспринимается как «любая до 1.0» → `poetry update` не поднимает версию выше `0.115.x` → помнить про поведение `^` для `0.x`, при необходимости писать диапазон явно: `>=0.115,<1`.
- `poetry install` на проде ставит pytest и ruff → образ тяжелее и дольше собирается → `poetry install --without dev` или `--only main`.
- `poetry shell` в Poetry 2 → `The command "shell" does not exist` → `poetry run <команда>`, `poetry env activate` или плагин `poetry-plugin-shell`.
- `poetry export` → `The command "export" does not exist` → поставить `poetry self add poetry-plugin-export`.
- IDE не находит интерпретатор → venv лежит в `~/.cache/pypoetry/virtualenvs/` под случайным именем → `poetry config virtualenvs.in-project true` и пересоздать окружение, либо взять путь из `poetry env info --path`.
- `poetry lock` после правки `pyproject.toml` в Poetry 1 обновляет все пакеты → неожиданные версии в lock → `poetry lock --no-update`.

## Когда не использовать

Новый проект без привязки к Poetry проще начать на [uv](../uv/README.md): тот же `pyproject.toml` и lock, но в разы быстрее, плюс установка интерпретаторов. Одноразовый скрипт с парой зависимостей не требует проекта вовсе: `uv run script.py` с inline-зависимостями (PEP 723). CLI-утилиту (ruff, black, httpie) ставят не в проект, а через [pipx](../pipx/README.md) или `uv tool install`. В Docker-образе Poetry тоже обычно лишний: экспортируют `requirements.txt` или ставят `uv` и `uv sync --no-dev`.

## Что спрашивают на собеседовании

- Чем `pyproject.toml` отличается от `poetry.lock` и что из них коммитить? *(Первый — диапазоны, второй — точные версии с хешами; коммитить оба.)*
- Что значит `^0.115.0`? *(`>=0.115.0, <0.116.0`: caret фиксирует первую ненулевую часть версии.)*
- Как разделить dev- и прод-зависимости и как это использовать при деплое? *(Группы `[tool.poetry.group.dev]`, `poetry install --without dev`.)*
- Как Poetry работает с виртуальным окружением? *(Создаёт свой venv в кеше или `.venv`, команды запускаются через `poetry run`.)*
- Poetry или uv для нового проекта? *(Формат один — `pyproject.toml` + lock; uv быстрее и умеет ставить Python; Poetry зрелее.)*

## Связанные темы

- [Poetry: сценарии использования](scenarios.md)
- [uv](../uv/README.md)
- [pyenv](../pyenv/README.md)
- [pipx](../pipx/README.md)
- [Линтеры и форматтеры](../linter/README.md)
