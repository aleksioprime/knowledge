# pipx

**pipx** — инструмент для установки и запуска Python-приложений (CLI-утилит) в **изолированных окружениях**. Каждая утилита получает собственный venv, но при этом её команда доступна глобально в `PATH`.

## Содержание

- [Сценарии использования](scenarios.md) — установка набора утилит, генерация проектов, обслуживание

## Зачем он нужен

Когда ставишь утилиту через обычный `pip install poetry --user`:
- она засоряет глобальный Python;
- её зависимости могут конфликтовать с другими утилитами;
- удаление оставляет «хвосты».

`pipx` решает все три проблемы: каждая утилита изолирована, но команда всё равно работает из любой точки терминала.

**Аналогии**:
- `npm install -g <pkg>` в Node.js
- `brew install <pkg>` для Python-CLI
- Альтернатива: `uv tool install` (то же самое, но быстрее).

## Установка

### macOS
```sh
brew install pipx
pipx ensurepath        # добавит ~/.local/bin в PATH
```

### Linux
```sh
sudo apt install pipx        # Ubuntu 23.04+
# или
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

После установки перезапусти терминал.

## Основные команды

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

## Чем `pipx run` отличается от `pipx install`

- **`pipx install <tool>`** — создаёт постоянный venv и команду. Используй для того, чем пользуешься регулярно (Poetry, Ruff, Black).
- **`pipx run <tool>`** — создаёт временный venv, запускает один раз, кеширует. Используй для одноразовых задач или редкого использования.

```sh
pipx install poetry              # всегда нужен → ставим постоянно
pipx run cookiecutter ...        # разовая генерация проекта → run
```

## Когда `pipx`, а не обычный `pip`

| Сценарий | Чем ставить |
|---|---|
| CLI-утилита для всей системы (poetry, ruff, black, mypy) | **pipx** |
| Зависимость проекта (fastapi, sqlalchemy) | `pip` / `poetry` / `uv` |
| Разовый запуск чего-то экспериментального | `pipx run` |
| Глобальный пакет с библиотечной частью | обычно — не нужен глобально |

---

## Полезные программы для запуска через pipx

### 1. Автоматизация и управление проектами

#### Ansible — автоматизация IT-инфраструктуры
```sh
pipx install --include-deps ansible
```
Флаг `--include-deps` нужен, потому что Ansible поставляет несколько связанных CLI-команд (`ansible-playbook`, `ansible-vault` и т.д.), которые иначе не попадут в `PATH`.

#### Hatch — менеджер Python-проектов (создание пакетов, окружения, задачи)
```sh
pipx run hatch
```

#### Poetry — управление зависимостями и упаковка
```sh
pipx install poetry
poetry --version
```

#### Pipenv — упрощённое управление venv и зависимостями
```sh
pipx run pipenv
```

---

### 2. Работа с кодом и стилем

#### Black — автоматический форматтер
```sh
pipx install black
black my_script.py
# или разово
pipx run black my_script.py
```

#### Flake8 — проверка PEP8
```sh
pipx run flake8 my_script.py
```

#### Pylint — статический анализатор
```sh
pipx run pylint my_script.py
```

#### Ruff — быстрый линтер на Rust
```sh
pipx install ruff
ruff check my_script.py
ruff format my_script.py
```

---

### 3. Работа с терминалом

#### Asciinema — запись терминальных сессий
```sh
pipx install asciinema
asciinema rec demo.cast       # запись
asciinema play demo.cast      # воспроизведение
```
Часто используется для записи демок в README/документацию.

#### Gdbgui — графический интерфейс для gdb
```sh
pipx run gdbgui
```
Запускает локальный веб-интерфейс для отладки C/C++ и Rust.

#### Shell-Functools — функциональные инструменты для shell
```sh
pipx install shell-functools
# теперь доступны команды map, filter, foldl и т.п. для unix-pipe
```

#### Pyxtermjs — терминал в браузере
```sh
pipx run pyxtermjs
```

---

### 4. Работа с текстом и локализацией

#### PyBabel — интернационализация (i18n) и локализация (l10n)
```sh
pipx run --spec babel pybabel --help
```
Используется в Flask, Django для перевода приложений.

#### Chardetect — определение кодировки файла
```sh
pipx run --spec chardet chardetect myfile.txt
```

---

### 5. Создание и упаковка проектов

#### Cookiecutter — генерация проекта из шаблона
```sh
pipx run cookiecutter gh:audreyfeldroy/cookiecutter-pypackage
```
Огромная экосистема шаблонов на GitHub (FastAPI, Django, Flask, ML-проекты).

#### Create-Python-Package — создание и публикация пакетов
```sh
pipx run create-python-package
```

#### PyInstaller — упаковка приложения в самостоятельный исполняемый файл
```sh
pipx run pyinstaller my_script.py
```
Создаёт бинарник, который не требует Python на машине пользователя.

#### HexSticker — генерация шестиугольных стикеров (как у пакетов R)
```sh
pipx run hexsticker
```

---

## Шпаргалка использования

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

## pipx vs `uv tool`

`uv` тоже умеет работать в режиме «pipx»:
```sh
uv tool install ruff
uv tool run black .
uvx ruff check          # alias для uv tool run
```

Плюсы `uv tool`: быстрее, тот же бинарник для управления проектами.
Плюсы `pipx`: дольше существует, всё ещё стандарт де-факто.

Для новых сетапов можно полностью переходить на `uv tool` — он покрывает все сценарии pipx.

## Что спрашивают на собеседовании

- Чем `pipx install` отличается от `pip install --user`? *(Изоляция: каждая утилита в своём venv, нет конфликтов зависимостей.)*
- Когда использовать `pipx run`, а когда `pipx install`?
- Где `pipx` хранит venv-ы? *(`~/.local/pipx/venvs/`)*
- Как обновить все pipx-утилиты разом? *(`pipx upgrade-all`)*
