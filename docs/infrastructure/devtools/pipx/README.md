# pipx

pipx нужен, когда утилиты вроде Poetry, Ruff или HTTPie ставятся через `pip install` в системный Python, их зависимости конфликтуют между собой, а после удаления остаются «хвосты». pipx ставит каждую утилиту в собственное виртуальное окружение, но команду делает доступной глобально: `ruff` работает из любой папки, а пакеты внутри ничего не ломают.

## Содержание

- [Сценарии использования](scenarios.md) — установка набора утилит, генерация проектов, обслуживание

## Минимальный пример

Установка линтера как глобальной команды и разовый запуск утилиты без установки.

```bash
pipx install ruff
#   installed package ruff 0.6.9, installed using Python 3.12.6
#   These apps are now globally available
#     - ruff
# done! ✨ 🌟 ✨

ruff --version
# ruff 0.6.9

pipx list
# venvs are in /Users/user/.local/pipx/venvs
# apps are exposed on your $PATH at /Users/user/.local/bin
#    package ruff 0.6.9, installed using Python 3.12.6
#     - ruff

pipx run cowsay -t "задачник"
#   ________
# | задачник |
#   ========
#         \
#          \
#            ^__^
#            (oo)\_______
#            (__)\       )\/\
#                ||----w |
#                ||     ||
```

`pipx run` создаёт временное окружение, запускает утилиту и кеширует его; в `pipx list` такой пакет не появляется.

## Как это работает

На каждую утилиту pipx создаёт отдельный venv в `~/.local/pipx/venvs/<package>/` и кладёт символическую ссылку на её исполняемый файл в `~/.local/bin/`. Эта папка есть в `PATH`, поэтому команда запускается отовсюду, а зависимости утилиты остаются внутри её окружения. Как отдельная полка для каждого инструмента: взять можно с любого места, а перемешаться они не могут.

### Зачем он нужен

Когда ставишь утилиту через обычный `pip install poetry --user`:
- она засоряет глобальный Python;
- её зависимости могут конфликтовать с другими утилитами;
- удаление оставляет «хвосты».

`pipx` решает все три проблемы: каждая утилита изолирована, но команда всё равно работает из любой точки терминала.

**Аналогии**:
- `npm install -g <pkg>` в Node.js
- `brew install <pkg>` для Python-CLI
- Альтернатива: `uv tool install` (то же самое, но быстрее).

### Установка

#### macOS
```sh
brew install pipx
pipx ensurepath        # добавит ~/.local/bin в PATH
```

#### Linux
```sh
sudo apt install pipx        # Ubuntu 23.04+
# или
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

После установки перезапусти терминал.

### Основные команды

```sh
pipx install <package>             # установить утилиту (создаётся venv в ~/.local/pipx/venvs/)
pipx run <package>                 # запустить разово, без установки
pipx upgrade <package>             # обновить
pipx upgrade-all                   # обновить все
pipx uninstall <package>           # удалить
pipx list                          # список установленных

pipx inject <package> <dep>        # доставить зависимость в venv утилиты
pipx ensurepath                    # настроить PATH
pipx reinstall-all                 # пересоздать все venv (например, после обновления Python)
```

### Чем `pipx run` отличается от `pipx install`

- **`pipx install <tool>`** — создаёт постоянный venv и команду. Используй для того, чем пользуешься регулярно (Poetry, Ruff, Black).
- **`pipx run <tool>`** — создаёт временный venv, запускает один раз, кеширует. Используй для одноразовых задач или редкого использования.

```sh
pipx install poetry              # всегда нужен → ставим постоянно
pipx run cookiecutter ...        # разовая генерация проекта → run
```

### Когда `pipx`, а не обычный `pip`

| Сценарий | Чем ставить |
|---|---|
| CLI-утилита для всей системы (poetry, ruff, black, mypy) | **pipx** |
| Зависимость проекта (fastapi, sqlalchemy) | `pip` / `poetry` / `uv` |
| Разовый запуск чего-то экспериментального | `pipx run` |
| Глобальный пакет с библиотечной частью | обычно — не нужен глобально |

### Полезные программы для запуска через pipx

#### Автоматизация и управление проектами

**Ansible** — автоматизация IT-инфраструктуры.
```sh
pipx install --include-deps ansible
```
Флаг `--include-deps` нужен, потому что Ansible поставляет несколько связанных CLI-команд (`ansible-playbook`, `ansible-vault` и т.д.), которые иначе не попадут в `PATH`.

**Hatch** — менеджер Python-проектов (создание пакетов, окружения, задачи).
```sh
pipx run hatch
```

**Poetry** — управление зависимостями и упаковка.
```sh
pipx install poetry
poetry --version
```

**Pipenv** — упрощённое управление venv и зависимостями.
```sh
pipx run pipenv
```

#### Работа с кодом и стилем

**Black** — автоматический форматтер.
```sh
pipx install black
black my_script.py
# или разово
pipx run black my_script.py
```

**Flake8** — проверка PEP8.
```sh
pipx run flake8 my_script.py
```

**Pylint** — статический анализатор.
```sh
pipx run pylint my_script.py
```

**Ruff** — быстрый линтер на Rust.
```sh
pipx install ruff
ruff check my_script.py
ruff format my_script.py
```

#### Работа с терминалом

**Asciinema** — запись терминальных сессий.
```sh
pipx install asciinema
asciinema rec demo.cast       # запись
asciinema play demo.cast      # воспроизведение
```
Часто используется для записи демок в README/документацию.

**Gdbgui** — графический интерфейс для gdb.
```sh
pipx run gdbgui
```
Запускает локальный веб-интерфейс для отладки C/C++ и Rust.

**Shell-Functools** — функциональные инструменты для shell.
```sh
pipx install shell-functools
# теперь доступны команды map, filter, foldl и т.п. для unix-pipe
```

**Pyxtermjs** — терминал в браузере.
```sh
pipx run pyxtermjs
```

#### Работа с текстом и локализацией

**PyBabel** — интернационализация (i18n) и локализация (l10n).
```sh
pipx run --spec babel pybabel --help
```
Используется в Flask, Django для перевода приложений.

**Chardetect** — определение кодировки файла.
```sh
pipx run --spec chardet chardetect myfile.txt
```

#### Создание и упаковка проектов

**Cookiecutter** — генерация проекта из шаблона.
```sh
pipx run cookiecutter gh:audreyfeldroy/cookiecutter-pypackage
```
Огромная экосистема шаблонов на GitHub (FastAPI, Django, Flask, ML-проекты).

**Create-Python-Package** — создание и публикация пакетов.
```sh
pipx run create-python-package
```

**PyInstaller** — упаковка приложения в самостоятельный исполняемый файл.
```sh
pipx run pyinstaller my_script.py
```
Создаёт бинарник, который не требует Python на машине пользователя.

**HexSticker** — генерация шестиугольных стикеров (как у пакетов R).
```sh
pipx run hexsticker
```

### Шпаргалка использования

```sh
# Узнать, где живёт утилита
pipx list
ls ~/.local/pipx/venvs/

# Переустановить под новый Python после обновления pyenv
pipx reinstall-all --python python3.12

# Установить из git
pipx install git+https://github.com/user/repo.git

# Установить с extras
pipx install 'httpie[all]'

# Запустить конкретный entrypoint из пакета
pipx run --spec <package> <command>

# Доустановить зависимость в venv существующей утилиты
pipx inject mkdocs mkdocs-material
```

### pipx vs `uv tool`

`uv` тоже умеет работать в режиме «pipx»:
```sh
uv tool install ruff
uv tool run black .
uvx ruff check          # alias для uv tool run
```

Плюсы `uv tool`: быстрее, тот же бинарник для управления проектами.
Плюсы `pipx`: дольше существует, всё ещё стандарт де-факто.

Для новых сетапов можно полностью переходить на `uv tool` — он покрывает все сценарии pipx.

## Частые ошибки

- После `pipx install` команда не найдена → `~/.local/bin` нет в `PATH` → выполнить `pipx ensurepath` и перезапустить терминал.
- Утилите нужен плагин или дополнительная библиотека, её ставят через `pip install` → пакет попадает в системный Python, а утилита в своём venv его не видит → `pipx inject <утилита> <пакет>`.
- Обновили Python через pyenv или brew → все утилиты падают с `No such file or directory: .../bin/python` → `pipx reinstall-all`, при необходимости с `--python python3.12`.
- Библиотеку проекта (`fastapi`, `sqlalchemy`) поставили через pipx → `import` в проекте не работает: пакет лежит в изолированном venv утилиты → зависимости проекта ставить в его окружение через uv, Poetry или pip.
- `pipx install ansible` без `--include-deps` → доступна только команда `ansible`, а `ansible-playbook` нет → переустановить с `--include-deps`.
- Имя команды не совпадает с именем пакета → `pipx run pybabel` не находит пакет → указывать пакет явно: `pipx run --spec babel pybabel`.

## Когда не использовать

pipx — только для утилит командной строки. Зависимости проекта ставят в окружение проекта через [uv](../uv/README.md) или [Poetry](../poetry/README.md); библиотеки без исполняемого файла pipx и вовсе откажется ставить.

Если uv уже стоит, отдельный pipx не нужен: `uv tool install` и `uvx` делают то же самое быстрее и из того же бинарника. В Docker-образе pipx тоже лишний: там одно окружение на контейнер, и утилиту проще поставить обычным `pip install`.

## Что спрашивают на собеседовании

- Чем `pipx install` отличается от `pip install --user`? *(Изоляция: каждая утилита в своём venv, нет конфликтов зависимостей.)*
- Когда использовать `pipx run`, а когда `pipx install`?
- Где `pipx` хранит venv-ы? *(`~/.local/pipx/venvs/`)*
- Как обновить все pipx-утилиты разом? *(`pipx upgrade-all`)*

## Связанные темы

- [Сценарии использования pipx](scenarios.md)
- [uv](../uv/README.md) — `uv tool` как замена pipx
- [Poetry](../poetry/README.md)
- [pyenv](../pyenv/README.md) — после смены версии Python нужен `pipx reinstall-all`
- [Линтеры и форматтеры](../linter/README.md)
