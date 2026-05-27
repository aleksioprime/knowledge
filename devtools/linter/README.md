# Линтеры и форматтеры

**Линтер** — анализирует код и сообщает о потенциальных ошибках, нарушениях стиля.
**Форматтер** — автоматически приводит код к единому стилю.

---

## Обзор инструментов

### Линтеры (статический анализ)

#### Ruff ⭐ (рекомендуется)
Сверхбыстрый линтер на Rust от Astral. Заменяет flake8 + isort + pyupgrade + частично pylint. В 50–100× быстрее flake8.
```sh
pipx install ruff
ruff check .
ruff check --fix .
```

#### Pylint
Самый строгий и глубокий из классических. Медленный, по умолчанию очень шумный.
```sh
pipx run pylint my_script.py
```

#### Flake8
Комбинирует PyFlakes, pycodestyle и McCabe (cyclomatic complexity). Долго был стандартом, сегодня вытесняется Ruff.
```sh
pipx run flake8 my_script.py
```

#### Pycodestyle
Простая проверка соответствия **PEP8** (стиль написания). До 2016 года назывался `pep8`. Входит в состав Flake8.

#### Bandit
Специализированный линтер для **поиска уязвимостей безопасности** (hardcoded passwords, использование `eval`, небезопасные YAML-загрузки и т.д.).
```sh
pipx install bandit
bandit -r src/
```

#### Vulture
Ищет **«мёртвый» код** — функции, переменные, импорты, которые объявлены, но не используются. Полезно при чистке легаси.
```sh
pipx install vulture
vulture src/
```

### Проверка типов

#### mypy
Самый известный тип-чекер для Python. Использует подсказки типов (`PEP 484`).
```sh
pipx install mypy
mypy src/
```

#### pyright
Альтернатива от Microsoft (на TypeScript, входит в Pylance в VS Code). Быстрее mypy, лучше на дженериках.
```sh
pipx install pyright
pyright
```

### Форматтеры

#### Black
Автоматический форматтер «без вариантов» — навязывает один стиль, без настроек.
```sh
pipx install black
black my_script.py
black --check .         # только проверка
```

#### isort
Сортирует и группирует импорты по PEP 8. Сегодня заменяется правилом `I` в Ruff.
```sh
pipx install isort
isort .
```

#### ruff format
Форматтер от Astral, совместимый с Black (тот же стиль), но в 30× быстрее.
```sh
ruff format .
```

### Сравнительная таблица

| Инструмент | Тип | Скорость | Статус |
|---|---|---|---|
| **Ruff** | Линтер + форматтер | ⚡⚡⚡ | Современный стандарт |
| Pylint | Линтер (глубокий) | 🐢 | Зрелый, но медленный |
| Flake8 | Линтер | 🐢 | Уступает Ruff |
| Pycodestyle | Линтер (PEP8) | 🚶 | Внутри Flake8 |
| Mypy | Тип-чекер | 🚶 | Стандарт |
| Pyright | Тип-чекер | 🏃 | Хорош для IDE |
| Black | Форматтер | 🚶 | Стандарт стиля |
| isort | Форматтер импортов | 🏃 | Заменяется Ruff |
| Bandit | Безопасность | 🏃 | Узкоспециализирован |
| Vulture | Мёртвый код | 🏃 | Точечное применение |

---

## Рекомендуемый стек (2024+)

«Минимальный стек, который покрывает 95% потребностей»:

```
ruff       — линтер + форматтер (заменяет 5 инструментов)
mypy       — типы
bandit     — безопасность (если важна)
pre-commit — автозапуск перед коммитом
```

---

## Настройка Ruff

Конфиг в `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py312"
extend-exclude = ["migrations", "alembic"]

[tool.ruff.lint]
# Полный список правил: https://docs.astral.sh/ruff/rules/
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort (сортировка импортов)
    "B",    # flake8-bugbear (типичные баги)
    "C4",   # flake8-comprehensions
    "UP",   # pyupgrade (модернизация синтаксиса)
    "SIM",  # flake8-simplify
    "N",    # pep8-naming
]
ignore = ["E501"]    # длина строки — пусть форматтер сам режет

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["S101"]      # asserts в тестах разрешены
"__init__.py" = ["F401"]  # неиспользуемые импорты — это re-exports

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

Команды:
```sh
ruff check .                    # проверка
ruff check --fix .              # авто-фиксы
ruff format .                   # форматирование
ruff check --watch              # следить за изменениями
```

## Настройка mypy

```toml
[tool.mypy]
python_version = "3.12"
strict = true                          # включить все строгие проверки
exclude = ["migrations/", "build/"]

[[tool.mypy.overrides]]
module = ["external_lib.*"]
ignore_missing_imports = true
```

Запуск:
```sh
mypy src/
mypy --install-types                   # установить недостающие stubs
```

## pre-commit

Запускает линтеры перед каждым коммитом. Конфиг — `.pre-commit-config.yaml`:

```yaml
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

Установка:
```sh
pipx install pre-commit
pre-commit install                 # добавит .git/hooks/pre-commit
pre-commit run --all-files         # прогнать на всём репо
pre-commit autoupdate              # обновить версии хуков
```

После этого `git commit` будет блокироваться, если линтер недоволен.

## Интеграция с CI (GitHub Actions)

```yaml
name: lint
on: [push, pull_request]
jobs:
  ruff:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/ruff-action@v1
        with:
          args: 'check --output-format=github'
      - run: ruff format --check .
```

## С чего начинать

1. **Начни с `ruff`**: один конфиг, ноль настроек, моментальные проверки.
2. **Добавь `mypy`** хотя бы для основных модулей (`strict = false`, потом постепенно ужесточай).
3. **Поставь `pre-commit`**: автоматизация бьёт ручные проверки.
4. **Включи в CI**: чтобы плохой код физически не попадал в `main`.

## Содержание

- [Сценарии: миграция legacy → ruff, конфиги](scenarios.ipynb)
