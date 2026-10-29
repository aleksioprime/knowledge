# Линтеры — сценарии использования

Настройка современного стека `ruff + mypy + pre-commit` в Python-проекте.

## Сценарий 1. Поставить инструменты

```bash
# Глобально через pipx
pipx install ruff
pipx install mypy
pipx install pre-commit

# Или в проект (через uv/poetry)
uv add --dev ruff mypy pre-commit
```

## Сценарий 2. Минимальный конфиг ruff в pyproject.toml

::: code-group
```toml [pyproject.toml]
[tool.ruff]
line-length = 100
target-version = "py312"
extend-exclude = ["migrations", "alembic"]

[tool.ruff.lint]
select = [
    "E", "W",   # pycodestyle
    "F",         # pyflakes
    "I",         # isort
    "B",         # bugbear
    "C4",        # comprehensions
    "UP",        # pyupgrade
    "SIM",       # simplify
    "N",         # naming
]
ignore = ["E501"]

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["S101"]
"__init__.py" = ["F401"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```
:::

## Сценарий 3. Прогнать проверку и форматирование

```bash
# Только проверка
ruff check .

# С автофиксами
ruff check --fix .

# Форматирование
ruff format .

# Только проверить (не менять), вернёт ненулевой код если есть отличия
ruff format --check .
```

## Сценарий 4. mypy для проверки типов

::: code-group
```toml [pyproject.toml]
[tool.mypy]
python_version = "3.12"
strict = true
exclude = ["migrations/", "build/", "dist/"]

[[tool.mypy.overrides]]
module = ["external_lib.*"]
ignore_missing_imports = true
```
:::

```bash
# Запуск
mypy src/

# Установить stubs, если жалуется на отсутствие
mypy --install-types
```

## Сценарий 5. pre-commit — авто-запуск перед каждым коммитом

::: code-group
```yaml [.pre-commit-config.yaml]
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.2
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, sqlalchemy]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```
:::

```bash
# Установка хуков в .git/hooks/
pre-commit install

# Прогнать на всём репо вручную (а не только на staged)
pre-commit run --all-files

# Обновить версии хуков
pre-commit autoupdate
```

## Сценарий 6. CI на GitHub Actions

::: code-group
```yaml [.github/workflows/lint.yml]
name: lint
on: [push, pull_request]
jobs:
  ruff:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/ruff-action@v1
        with:
          args: "check --output-format=github"
      - run: pipx run ruff format --check .
```
:::

## Сценарий 7. Миграция legacy-проекта на ruff

Когда подхватываешь проект с flake8 + isort + black:

```bash
# 1. Глянуть, что ruff скажет (без правок)
ruff check . --statistics

# 2. Автоисправить всё, что можно
ruff check --fix --unsafe-fixes .
ruff format .

# 3. Удалить старые конфиги
rm -f .flake8 setup.cfg .isort.cfg
# (и убрать соответствующие секции из pyproject.toml)
```

## Связанные темы

- [Линтеры](README.md)
- [pipx: сценарии](../pipx/scenarios.md)
- [uv: сценарии](../uv/scenarios.md)
- [GitHub Actions](../../cicd/github/README.md)
