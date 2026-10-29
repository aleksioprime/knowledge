# Линтеры и форматтеры

Линтер и форматтер нужны, когда ревью превращается в спор о пробелах и кавычках, а в код уезжают неиспользуемые импорты, забытые переменные и сравнение с `None` через `==`. Линтер (linter) находит такие места и ошибки до запуска, форматтер (formatter) приводит код к единому виду без обсуждений. Здесь обзор инструментов для Python и настройка стека ruff, mypy и pre-commit.

## Содержание

- [Сценарии: миграция legacy → ruff, конфиги](scenarios.md)

## Минимальный пример

В `tasks.py` «Задачника» неиспользуемый импорт и сравнение с `None` через `==`. Ruff находит обе проблемы, первую чинит сам, а форматтер выравнивает кавычки.

```python
import os
from datetime import date

def is_overdue(task, today = None):
    if today == None:
        today = date.today()
    return task['deadline'] < today
```

```bash
pipx install ruff
ruff check tasks.py
# tasks.py:1:8: F401 [*] `os` imported but unused
# tasks.py:5:17: E711 Comparison to `None` should be `cond is None`
# Found 2 errors.
# [*] 1 fixable with the `--fix` option (1 hidden fix can be enabled with the `--unsafe-fixes` option).

ruff check --fix tasks.py
# Found 2 errors (1 fixed, 1 remaining).
# No fixes available (1 hidden fix can be enabled with the `--unsafe-fixes` option).

ruff format tasks.py
# 1 file reformatted
```

После этого `today = None` в сигнатуре записан без пробелов вокруг `=`, кавычки двойные, между импортами и функцией две пустые строки. Сравнение с `None` ruff по умолчанию не трогает: замена `==` на `is` может изменить поведение, поэтому такие правки включаются флагом `--unsafe-fixes` или делаются руками.

## Как это работает

Линтер разбирает код в синтаксическое дерево и прогоняет по нему правила: «импорт есть, а использования нет», «`except:` без типа». Каждое правило имеет код (`F401`, `E711`), и в конфиге выбирают, какие из них включить. Форматтер работает иначе: он не ищет ошибки, а печатает дерево заново по единым правилам, поэтому результат не зависит от того, как код был записан.

### Обзор инструментов

#### Линтеры (статический анализ)

**Ruff** (рекомендуется) — сверхбыстрый линтер на Rust от Astral. Заменяет flake8 + isort + pyupgrade + частично pylint. В 50–100× быстрее flake8.
```sh
pipx install ruff
ruff check .
ruff check --fix .
```

**Pylint** — самый строгий и глубокий из классических. Медленный, по умолчанию очень шумный.
```sh
pipx run pylint my_script.py
```

**Flake8** — комбинирует PyFlakes, pycodestyle и McCabe (cyclomatic complexity). Долго был стандартом, сегодня вытесняется Ruff.
```sh
pipx run flake8 my_script.py
```

**Pycodestyle** — простая проверка соответствия **PEP8** (стиль написания). До 2016 года назывался `pep8`. Входит в состав Flake8.

**Bandit** — специализированный линтер для **поиска уязвимостей безопасности** (hardcoded passwords, использование `eval`, небезопасные YAML-загрузки и т.д.).
```sh
pipx install bandit
bandit -r src/
```

**Vulture** — ищет **«мёртвый» код**: функции, переменные, импорты, которые объявлены, но не используются. Полезно при чистке легаси.
```sh
pipx install vulture
vulture src/
```

#### Проверка типов

**mypy** — самый известный тип-чекер для Python. Использует подсказки типов (`PEP 484`).
```sh
pipx install mypy
mypy src/
```

**pyright** — альтернатива от Microsoft (на TypeScript, входит в Pylance в VS Code). Быстрее mypy, лучше на дженериках.
```sh
pipx install pyright
pyright
```

#### Форматтеры

**Black** — автоматический форматтер «без вариантов»: навязывает один стиль, без настроек.
```sh
pipx install black
black my_script.py
black --check .         # только проверка
```

**isort** — сортирует и группирует импорты по PEP 8. Сегодня заменяется правилом `I` в Ruff.
```sh
pipx install isort
isort .
```

**ruff format** — форматтер от Astral, совместимый с Black (тот же стиль), но в 30× быстрее.
```sh
ruff format .
```

#### Сравнительная таблица

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

### Рекомендуемый стек (2024+)

«Минимальный стек, который покрывает 95% потребностей»:

```
ruff       — линтер + форматтер (заменяет 5 инструментов)
mypy       — типы
bandit     — безопасность (если важна)
pre-commit — автозапуск перед коммитом
```

### Настройка Ruff

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

### Настройка mypy

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

### pre-commit

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

### Интеграция с CI (GitHub Actions)

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

### С чего начинать

1. **Начни с `ruff`**: один конфиг, ноль настроек, моментальные проверки.
2. **Добавь `mypy`** хотя бы для основных модулей (`strict = false`, потом постепенно ужесточай).
3. **Поставь `pre-commit`**: автоматизация бьёт ручные проверки.
4. **Включи в CI**: чтобы плохой код физически не попадал в `main`.

## Частые ошибки

- Линтер включили на старом проекте сразу со всеми правилами → тысячи замечаний, команда отключает проверку целиком → начать с `E`, `F`, `I`, добавлять группы по одной; для legacy есть сценарий в [scenarios.md](scenarios.md).
- Линтер и форматтер спорят друг с другом → ruff ругается на `E501`, а форматтер не режет длинную строку, или isort и ruff сортируют импорты по-разному → у ruff отключить `E501`, импорты сортировать только правилом `I`, isort и black убрать.
- Проверка стоит только в CI → замечания приходят через десять минут после пуша, правки откладываются → поставить `pre-commit install`, чтобы ошибки ловились до коммита.
- `ruff check` в CI, а `ruff format` нет → код проходит проверку, но стиль в репозитории расползается → добавить `ruff format --check .`.
- В pre-commit у mypy нет зависимостей проекта → `Cannot find implementation or library stub` на каждый импорт → перечислить библиотеки в `additional_dependencies` или запускать mypy из venv проекта.
- Замечания глушат комментариями `# noqa` и `# type: ignore` без кода правила → подавляется любая будущая ошибка в этой строке → писать код правила: `# noqa: E501`, `# type: ignore[arg-type]`.
- `mypy --strict` на проекте без аннотаций → сотни ошибок про `Any` и `untyped def` → начать без `strict`, включать флаги постепенно, начиная с новых модулей.

## Когда не использовать

Для одноразового скрипта или учебного примера на двадцать строк линтер с конфигом и pre-commit — лишняя церемония: достаточно `ruff check script.py` вручную. Pylint с его шумом и медленным запуском в обычном проекте тоже не нужен, если уже стоит ruff.

Проверка типов не окупается там, где нет аннотаций и никто не собирается их добавлять: mypy на таком коде молчит или шумит. Сначала аннотировать ключевые модули, потом включать проверку.

Форматтер не стоит ставить на чужой код «ради порядка» в середине работы над фичей: diff из тысяч строк хоронит смысл правок в ревью. Форматирование выносят в отдельный коммит, а его хеш добавляют в `.git-blame-ignore-revs`.

## Связанные темы

- [Сценарии: миграция legacy → ruff, конфиги](scenarios.md)
- [pipx](../pipx/README.md) — установка линтеров как утилит
- [uv](../uv/README.md) — `uv tool install ruff`
- [Git](../git/README.md)
- [Task Runners](../task_runners/README.md) — `make lint` как единая точка входа
- [GitHub Actions](../../cicd/github/README.md)
