# Task Runners

**Task runner** — инструмент, который запускает набор именованных команд проекта (`build`, `test`, `lint`, `deploy`) из одного конфиг-файла. Команда становится единой точкой входа — не нужно помнить длинные опции каждой утилиты.

Зачем нужен:
- стандартизация: `make test` работает в любом проекте одинаково;
- документация: конфиг сам по себе — список того, что умеет проект;
- зависимости задач (`test` зависит от `build`);
- CI и локалка пользуются одними командами.

## Содержание

> Дополнительные шаблоны для разных типов проектов будут добавляться по мере проработки темы.

## Три популярных варианта

| Инструмент | Язык | Файл | Особенности |
|---|---|---|---|
| **Make** | C (есть везде) | `Makefile` | Стандарт со времён Unix. Капризный синтаксис (табы!). |
| **Just** | Rust | `justfile` | Современный, дружелюбный синтаксис. Без «магии» make. |
| **Task** | Go | `Taskfile.yml` | YAML-конфиг, кроссплатформенный, удобные шаблоны. |

---

## Make

Стоит из коробки на любом Linux/macOS. Минимальный порог входа, но синтаксис специфический.

### Особенности
- **Отступы — только табы**, не пробелы (главная ловушка для новичков).
- Каждая «строка команды» выполняется в **отдельном shell**, переменные между ними не живут.
- Имена `target`-ов, совпадающие с файлами/папками, надо помечать `.PHONY`.

### Пример Makefile

```makefile
# Переменные
PYTHON := python3
SRC := src
TESTS := tests

# Цели, которые не создают файл с таким именем
.PHONY: help install lint format test run clean

help:        ## Показать список команд
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

install:     ## Установить зависимости
	uv sync

lint:        ## Проверить код линтером
	ruff check $(SRC) $(TESTS)
	mypy $(SRC)

format:      ## Отформатировать код
	ruff format $(SRC) $(TESTS)
	ruff check --fix $(SRC) $(TESTS)

test:        ## Запустить тесты
	uv run pytest -v --cov=$(SRC)

run:         ## Запустить приложение
	uv run fastapi dev $(SRC)/main.py

clean:       ## Очистить кеши и сборки
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache .mypy_cache dist build *.egg-info
```

Использование:
```sh
make help          # справка по командам
make install
make test
make lint format   # несколько целей за раз
```

### Зависимости между целями

```makefile
deploy: test lint        # сначала прогонит test и lint
	./scripts/deploy.sh

test: install            # перед test всегда install
	pytest
```

---

## Just

Современная альтернатива Make без «исторических» проблем. Установка:
```sh
brew install just         # macOS
cargo install just        # из исходников
```

### Особенности
- Отступы — пробелы.
- Команды одной задачи выполняются в **одном shell** (как ожидаешь).
- Встроенный механизм аргументов и значений по умолчанию.
- `just --list` показывает список задач с описаниями автоматически.

### Пример justfile

```just
# Алиас по умолчанию (если запустить просто `just`)
default: lint test

# Установить зависимости
install:
    uv sync

# Запустить линтеры
lint:
    ruff check src tests
    mypy src

# Отформатировать код
format:
    ruff format src tests
    ruff check --fix src tests

# Тесты с покрытием
test:
    uv run pytest -v --cov=src

# Запустить приложение
run port="8000":
    uv run fastapi dev src/main.py --port {{port}}

# Очистить кеши
clean:
    find . -type d -name __pycache__ -exec rm -rf {} +
    rm -rf .pytest_cache .ruff_cache .mypy_cache dist build *.egg-info

# Создать миграцию
migrate name:
    uv run alembic revision --autogenerate -m "{{name}}"
```

Использование:
```sh
just --list
just install
just run                 # порт по умолчанию 8000
just run 9000            # с аргументом
just migrate "add users table"
```

---

## Task (Taskfile)

Кроссплатформенный (умеет Windows), YAML-конфиг. Хороший выбор, если команда смешанная по ОС.

```sh
brew install go-task/tap/go-task        # macOS
# или: https://taskfile.dev/installation/
```

### Пример Taskfile.yml

```yaml
version: '3'

vars:
  SRC: src
  TESTS: tests

tasks:
  default:
    desc: По умолчанию — lint и test
    cmds:
      - task: lint
      - task: test

  install:
    desc: Установить зависимости
    cmds:
      - uv sync

  lint:
    desc: Запустить линтеры
    cmds:
      - ruff check {{.SRC}} {{.TESTS}}
      - mypy {{.SRC}}

  format:
    desc: Отформатировать код
    cmds:
      - ruff format {{.SRC}} {{.TESTS}}
      - ruff check --fix {{.SRC}} {{.TESTS}}

  test:
    desc: Тесты с покрытием
    deps: [install]
    cmds:
      - uv run pytest -v --cov={{.SRC}}

  run:
    desc: Запустить приложение
    cmds:
      - uv run fastapi dev {{.SRC}}/main.py

  clean:
    desc: Очистить кеши
    cmds:
      - find . -type d -name __pycache__ -exec rm -rf {} +
      - rm -rf .pytest_cache .ruff_cache .mypy_cache dist build *.egg-info
```

Использование:
```sh
task --list
task install
task test
task lint format
```

### Фишки Task

- **`deps:`** — задачи, которые выполнятся параллельно перед текущей.
- **`sources:` / `generates:`** — задача не перезапустится, если входные файлы не менялись (как настоящий Make).
- **`includes:`** — подключение `Taskfile.yml` из подпапок.

---

## Что выбрать

```
Make           — везде есть, минимум зависимостей. Для CI-скриптов и серверов.
Just           — самый удобный для повседневной разработки.
Task           — если важна кроссплатформенность (Windows-разработчики в команде).
```

В **новом проекте** проще всего начать с `just` — удобный синтаксис, понятный `--list`, нормальный shell.
В **легаси / минимальном окружении** — `Makefile`, потому что `make` всегда есть.

## Что спрашивают на собеседовании

- Зачем нужен task runner и чем плох обычный shell-скрипт? *(Документированность, зависимости задач, переиспользуемость, единый интерфейс.)*
- Главная ловушка Makefile? *(Отступы — табы, и каждая строка в своём shell.)*
- Как ваш task runner работает в CI? *(Тот же `make test` / `just test`, что и локально.)*
