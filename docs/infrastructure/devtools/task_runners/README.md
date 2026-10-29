# Task Runners

Команды проекта расползаются по README, истории терминала и памяти коллег: как именно запускать тесты с покрытием, с какими флагами линтер, что сделать перед деплоем. **Task runner** (Make, Just, Task) собирает эти команды в один файл с именами: `make test`, `just lint`, `task deploy` — одинаково у каждого разработчика и в CI, с зависимостями между задачами и встроенной справкой.

## Содержание

> Дополнительные шаблоны для разных типов проектов будут добавляться по мере проработки темы.

## Минимальный пример

`Makefile` с тремя целями; `check` сначала выполняет `lint` и `test`. `make` есть на любом Linux и macOS, ставить ничего не нужно.

```makefile
.PHONY: lint test check

lint:
	ruff check src

test:
	pytest -q

check: lint test
```

```bash
make -n check          # -n показывает команды, не выполняя их
# ruff check src
# pytest -q

make check             # выполнит lint, затем test; остановится на первой ошибке
```

Отступ перед командой — символ табуляции. С пробелами `make` ответит `Makefile:4: *** missing separator.  Stop.`

## Как это работает

Файл задач — это список имён, у каждого — команды для shell и список других задач, которые должны выполниться раньше. Runner строит граф зависимостей, выполняет нужные задачи в правильном порядке и прерывается, если команда вернула ненулевой код. В CI вызывают те же имена, что и локально, поэтому различия между «у меня работает» и пайплайном исчезают. Make дополнительно сравнивает время изменения файлов и пропускает цель, если её результат свежее входов, — отсюда его происхождение как системы сборки.

### Три популярных варианта

| Инструмент | Язык | Файл | Особенности |
|---|---|---|---|
| **Make** | C (есть везде) | `Makefile` | Стандарт со времён Unix. Капризный синтаксис (табы!). |
| **Just** | Rust | `justfile` | Современный, дружелюбный синтаксис. Без «магии» make. |
| **Task** | Go | `Taskfile.yml` | YAML-конфиг, кроссплатформенный, удобные шаблоны. |

### Make

Стоит из коробки на любом Linux/macOS. Минимальный порог входа, но синтаксис специфический.

Особенности:

- **Отступы — только табы**, не пробелы (главная ловушка для новичков).
- Каждая «строка команды» выполняется в **отдельном shell**, переменные между ними не живут.
- Имена целей, совпадающие с файлами/папками, надо помечать `.PHONY`.

Пример Makefile:

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

```bash
make help          # справка по командам
make install
make test
make lint format   # несколько целей за раз
```

Зависимости между целями:

```makefile
deploy: test lint        # сначала прогонит test и lint
	./scripts/deploy.sh

test: install            # перед test всегда install
	pytest
```

### Just

Современная альтернатива Make без «исторических» проблем. Установка:

```bash
brew install just         # macOS
cargo install just        # из исходников
```

Особенности:

- Отступы — пробелы.
- Команды одной задачи выполняются в **одном shell** (как ожидаешь).
- Встроенный механизм аргументов и значений по умолчанию.
- `just --list` показывает список задач с описаниями автоматически.

Пример justfile:

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

```bash
just --list
just install
just run                 # порт по умолчанию 8000
just run 9000            # с аргументом
just migrate "add users table"
```

### Task (Taskfile)

Кроссплатформенный (умеет Windows), YAML-конфиг. Хороший выбор, если команда смешанная по ОС.

```bash
brew install go-task/tap/go-task        # macOS
# или: https://taskfile.dev/installation/
```

Пример Taskfile.yml:

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

```bash
task --list
task install
task test
task lint format
```

Фишки Task:

- **`deps:`** — задачи, которые выполнятся параллельно перед текущей.
- **`sources:` / `generates:`** — задача не перезапустится, если входные файлы не менялись (как настоящий Make).
- **`includes:`** — подключение `Taskfile.yml` из подпапок.

### Что выбрать

```
Make           — везде есть, минимум зависимостей. Для CI-скриптов и серверов.
Just           — самый удобный для повседневной разработки.
Task           — если важна кроссплатформенность (Windows-разработчики в команде).
```

В **новом проекте** проще всего начать с `just` — удобный синтаксис, понятный `--list`, нормальный shell.
В **легаси / минимальном окружении** — `Makefile`, потому что `make` всегда есть.

## Частые ошибки

- Пробелы вместо табуляции в `Makefile` → `*** missing separator.  Stop.` → заменить отступ на таб; в редакторе включить показ невидимых символов для `Makefile`.
- Цель `test` при наличии папки `tests/` или файла `build` → `make: 'build' is up to date.` и ничего не выполняется → перечислить такие цели в `.PHONY`.
- `cd src` на одной строке и команда на следующей → команда выполняется не в `src`: каждая строка Make — отдельный shell → писать `cd src && pytest` одной строкой или включить `.ONESHELL:`.
- Переменная shell в Makefile через `$VAR` → Make подставляет свою переменную `$V` и остаток `AR` → экранировать: `$$VAR`.
- Длинные скрипты внутри задач → файл задач превращается в программу, которую нельзя тестировать → вынести логику в `scripts/*.sh` или Python, а в runner оставить вызов.
- В CI команды дублируются вручную, а не через runner → локальный и CI-прогон расходятся → в пайплайне вызывать `make test` / `just test`, а не копировать содержимое задач.

## Когда не использовать

Если в проекте одна-две команды, которые и так помещаются в README (`uv run pytest`, `uv run fastapi dev`), отдельный файл задач не добавляет ничего, кроме ещё одной зависимости. Для сборки с реальным отслеживанием изменений файлов (C/C++, генерация артефактов) нужны настоящие системы сборки — CMake, Bazel, а не task runner. Если команда уже использует [mise](../env_management/README.md), его секция `[tasks]` закрывает те же потребности без второго инструмента; в Node-проектах ту же роль выполняют `scripts` в `package.json`.

## Что спрашивают на собеседовании

- Зачем нужен task runner и чем плох обычный shell-скрипт? *(Документированность, зависимости задач, переиспользуемость, единый интерфейс.)*
- Главная ловушка Makefile? *(Отступы — табы, и каждая строка в своём shell.)*
- Что такое `.PHONY` и когда без него ломается? *(Помечает цели, не создающие файл; без него Make пропускает цель, если есть одноимённый файл или папка.)*
- Как ваш task runner работает в CI? *(Тот же `make test` / `just test`, что и локально.)*
- Make, Just или Task — что выберете для нового проекта и почему? *(Just для удобства, Make для минимальных окружений, Task для Windows в команде.)*

## Связанные темы

- [Управление окружением: direnv и mise](../env_management/README.md)
- [uv](../uv/README.md)
- [Линтеры и форматтеры](../linter/README.md)
- [Docker](../docker/README.md)
- [Git](../git/README.md)
