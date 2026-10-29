# Poetry

**Poetry** — менеджер зависимостей и сборщик пакетов для Python. Описывает проект и зависимости в `pyproject.toml`, фиксирует точные версии в `poetry.lock`.

Зачем нужен:
- одна команда для install, build, publish;
- разделение dev- и prod-зависимостей;
- lock-файл для воспроизводимых сборок;
- автоматическое создание venv.

## Установка

Рекомендуемый способ — через `pipx` (не засоряет системный Python):
```sh
pipx install poetry
```

Альтернатива — официальный установщик:
```sh
curl -sSL https://install.python-poetry.org | python3 -
```

## Начало работы

### Новый проект
```sh
poetry new my-app           # с структурой src/, tests/, README
cd my-app
```

### Существующий проект
```sh
cd my-existing-project
poetry init                 # интерактивно создаст pyproject.toml
```

## Структура pyproject.toml

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

## Управление зависимостями

```sh
poetry add fastapi                    # добавить в основные
poetry add --group dev pytest         # добавить в dev-группу
poetry add 'sqlalchemy@^2.0'          # с версией
poetry add --optional redis           # опциональная зависимость

poetry remove fastapi
poetry update                         # обновить все по правилам ^/~
poetry update fastapi                 # одну
poetry lock                           # перегенерировать lock
poetry lock --no-update               # без обновления версий

poetry install                        # установить из lock
poetry install --without dev          # без dev-зависимостей (для прода)
poetry install --only main            # только main группа
```

## Виртуальное окружение

```sh
poetry env info                       # инфа про venv
poetry env list                       # список venv проекта
poetry env use python3.12             # выбрать интерпретатор

poetry shell                          # войти в venv (в новых версиях — отдельный плагин)
poetry run python script.py           # выполнить команду в venv
poetry run pytest
```

По умолчанию Poetry создаёт venv в `~/.cache/pypoetry/virtualenvs/`. Чтобы класть его рядом с проектом:
```sh
poetry config virtualenvs.in-project true
```

Тогда появится `.venv/` в корне проекта.

## Сборка и публикация

```sh
poetry build                          # собрать wheel и sdist в dist/
poetry publish                        # выложить на PyPI
poetry publish -r testpypi            # на TestPyPI
poetry config pypi-token.pypi <token> # настроить токен
```

## Семвер в Poetry

```
fastapi = "^0.115.0"   →  >=0.115.0, <0.116.0   (caret — фиксирует major)
fastapi = "~0.115.0"   →  >=0.115.0, <0.116.0   (tilde — фиксирует major+minor)
fastapi = "0.115.0"    →  ровно 0.115.0
fastapi = "*"          →  любая
fastapi = ">=0.115,<1"
```

⚠️ Внимание: для версий `0.x` поведение `^` отличается от других пакетных менеджеров. `^0.115` = `>=0.115, <0.116`, а не `<1.0`.

## Полезные сценарии

### Экспорт в requirements.txt (для Docker / CI)
```sh
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

## Poetry vs альтернативы

| Инструмент | Когда выбрать |
|---|---|
| **Poetry** | Удобный сборщик + менеджер. Зрелый, много адопта. |
| **uv** | Быстрее в 10–100×. Может всё то же + ставит интерпретаторы. Будущее. |
| **pip + venv + pip-tools** | Минималистичный «школьный» стек. |
| **pipenv** | Старая альтернатива, развитие замедлилось. |

## Содержание

- [Сценарии использования](scenarios.md) — создание проекта, управление зависимостями, экспорт, публикация
