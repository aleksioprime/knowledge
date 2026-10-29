# Poetry — сценарии использования

Типичные рабочие процессы в проектах с Poetry.

## Сценарий 1. Создать новый проект с FastAPI

```bash
poetry new my-fastapi-app --src
cd my-fastapi-app
```

```bash
poetry add 'fastapi[standard]' sqlalchemy 'pydantic-settings'
```

```bash
poetry add --group dev pytest pytest-asyncio ruff mypy
```

```bash
cat pyproject.toml
```

## Сценарий 2. Запустить код и тесты

```bash
# Запуск произвольной команды в venv
poetry run python -c 'import fastapi; print(fastapi.__version__)'

# Запуск тестов
poetry run pytest -v

# Запуск приложения
poetry run fastapi dev src/my_fastapi_app/main.py
```

## Сценарий 3. Управление виртуальным окружением

```bash
poetry env info
poetry env list
```

```bash
# Положить venv в проект (.venv в корне) — удобно для IDE
poetry config virtualenvs.in-project true --local

# Выбрать конкретный Python
poetry env use python3.12
```

## Сценарий 4. Управление зависимостями

```bash
# Посмотреть дерево зависимостей
poetry show --tree
```

```bash
# Какие пакеты устарели
poetry show --outdated

# Обновить всё по правилам в pyproject.toml
poetry update

# Обновить только один пакет
poetry update fastapi
```

## Сценарий 5. Экспорт в requirements.txt (для Docker)

В Dockerfile удобнее `pip install -r requirements.txt`, чем тащить Poetry в образ.

```bash
# Сначала нужен плагин (один раз)
poetry self add poetry-plugin-export

# Только основные зависимости
poetry export --only main -f requirements.txt -o requirements.txt --without-hashes

# Включая dev
poetry export --with dev -f requirements.txt -o requirements-dev.txt
```

## Сценарий 6. Сборка и публикация в PyPI

```bash
poetry build   # создаст dist/*.whl и dist/*.tar.gz
poetry config pypi-token.pypi <token>
poetry publish

# Сначала на TestPyPI
poetry config repositories.testpypi https://test.pypi.org/legacy/
poetry publish -r testpypi
```

## Сценарий 7. Собственная CLI-команда

Добавь в `pyproject.toml`:

```toml
[tool.poetry.scripts]
my-app = "my_fastapi_app.cli:main"
```
После `poetry install` команда `my-app` будет доступна внутри venv.

## Сценарий 8. Удалить демо-проект

```bash
cd ..
rm -rf my-fastapi-app
```

## Связанные темы

- [Poetry](README.md)
- [uv: сценарии](../uv/scenarios.md)
- [Линтеры: сценарии](../linter/scenarios.md)
