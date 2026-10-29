# uv — сценарии использования

uv заменяет pyenv + virtualenv + pip + pip-tools + pipx + (частично) Poetry — в одном бинарнике.

## Сценарий 1. Установка интерпретатора Python

```bash
uv python list
```

```bash
uv python install 3.12
uv python install 3.11 3.12 3.13   # сразу несколько
```

## Сценарий 2. Создать новый проект

```bash
uv init demo-uv-app --python 3.12
cd demo-uv-app
ls -la
```

```bash
# Добавляем зависимости
uv add fastapi sqlalchemy 'pydantic-settings'
uv add --dev pytest ruff mypy
```

```bash
cat pyproject.toml
```

```bash
# Запуск кода — uv сам активирует venv
uv run python -c 'import fastapi; print(fastapi.__version__)'
```

## Сценарий 3. Управление lock-файлом

```bash
uv lock                             # пересоздать uv.lock
uv lock --upgrade                   # обновить версии
uv lock --upgrade-package fastapi   # обновить одну
uv sync                             # подтянуть всё из lock
uv sync --no-dev                    # без dev-зависимостей (для прода)
```

## Сценарий 4. Дерево зависимостей

```bash
uv tree
```

## Сценарий 5. Запустить инструмент глобально (как pipx)

```bash
# Постоянная установка
uv tool install ruff
uv tool list

# Разовый запуск (как pipx run)
uvx ruff --version
```

## Сценарий 6. Inline-зависимости в скрипте (PEP 723)

Зависимости можно описать прямо в скрипте, в специальном комментарии `# /// script` в начале файла. uv сам создаст временный venv, поставит в него пакеты и запустит скрипт.

::: code-group
```python [inline_demo.py]
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx", "rich"]
# ///

import httpx
from rich import print

r = httpx.get("https://httpbin.org/get")
print(r.json())
```
:::

```bash
# uv сам поставит httpx и rich в одноразовый venv
uv run inline_demo.py
```

## Сценарий 7. pip-совместимый режим (без проекта)

```bash
uv venv .venv
source .venv/bin/activate
uv pip install fastapi
uv pip freeze
uv pip compile pyproject.toml -o requirements.txt   # как pip-tools
```

## Сценарий 8. Удалить демо-проект

```bash
cd ..
rm -rf demo-uv-app
```

## Связанные темы

- [uv](README.md)
- [Poetry: сценарии](../poetry/scenarios.md)
- [pipx: сценарии](../pipx/scenarios.md)
- [pyenv: сценарии](../pyenv/scenarios.md)
