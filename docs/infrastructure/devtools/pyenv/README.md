# pyenv

Один проект требует Python 3.10, другой уже на 3.12, а системный Python трогать нельзя — на нём держатся утилиты дистрибутива. **pyenv** ставит сколько угодно версий Python рядом друг с другом и подменяет команду `python` в зависимости от папки, в которой вы находитесь.

## Содержание

- [Сценарии использования](scenarios.md) — установка версий, локальный/глобальный Python, pyenv-virtualenv, типовые проблемы

## Минимальный пример

Ставим версию и закрепляем её за папкой проекта: внутри папки `python` — это 3.12.3, снаружи — прежняя версия.

```bash
brew install pyenv                    # macOS; на Linux: curl https://pyenv.run | bash
echo 'eval "$(pyenv init - zsh)"' >> ~/.zshrc && exec "$SHELL"

pyenv install 3.12.3
# Installed Python-3.12.3 to /Users/me/.pyenv/versions/3.12.3

cd ~/projects/tasker
pyenv local 3.12.3
cat .python-version                   # 3.12.3
python --version                      # Python 3.12.3

cd ..
python --version                      # Python 3.13.2 — версия из pyenv global или system
```

`.python-version` коммитится: у любого, кто поставил pyenv, в этой папке будет та же версия.

## Как это работает

pyenv не меняет системный Python. Он кладёт в начало `PATH` папку с «прокладками» (shims): `python`, `pip`, `pytest` и прочие команды из установленных версий. При вызове прокладка смотрит, какая версия выбрана для текущей папки, и запускает бинарник из `~/.pyenv/versions/<версия>/bin`. Выбор версии — через переменную `PYENV_VERSION`, файл `.python-version` или глобальную настройку.

### Установка

macOS (через Homebrew):

```bash
brew install pyenv
```

Linux:

```bash
curl https://pyenv.run | bash
```

Добавить в `~/.zshrc` (или `~/.bashrc`):

```bash
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init - zsh)"
```

Перезагрузить shell:

```bash
exec "$SHELL"
```

### Основные команды

```bash
pyenv install --list                  # все доступные версии
pyenv install 3.12.3                  # установить версию
pyenv uninstall 3.10.0                # удалить

pyenv versions                        # установленные версии
pyenv version                         # текущая активная

pyenv global 3.12.3                   # системная версия по умолчанию
pyenv local 3.11.9                    # для текущей папки (создаёт .python-version)
pyenv shell 3.10.0                    # только для текущей shell-сессии

pyenv which python                    # путь к активному python
pyenv rehash                          # после установки новых пакетов
```

### Локальный Python для проекта

В корне проекта:

```bash
cd ~/projects/my-app
pyenv local 3.12.3
```

Создаст файл `.python-version` — git закоммитит его, и любой, у кого стоит pyenv, получит ту же версию.

### Приоритет выбора версии

```
1. shell-окружение  (pyenv shell, переменная PYENV_VERSION)
2. local            (.python-version в текущей или родительских папках)
3. global           (~/.pyenv/version)
4. system           (системный python)
```

### pyenv-virtualenv (плагин для venv)

```bash
brew install pyenv-virtualenv
# или
git clone https://github.com/pyenv/pyenv-virtualenv.git $(pyenv root)/plugins/pyenv-virtualenv
```

Добавить в `~/.zshrc`:

```bash
eval "$(pyenv virtualenv-init -)"
```

Использование:

```bash
pyenv virtualenv 3.12.3 myapp-3.12       # создать venv
pyenv activate myapp-3.12                # активировать
pyenv deactivate                         # деактивировать
pyenv virtualenvs                        # список
pyenv uninstall myapp-3.12               # удалить
```

Привязать venv к папке:

```bash
cd ~/projects/my-app
pyenv local myapp-3.12     # авто-активация при входе в папку
```

### pyenv vs альтернативы

| Инструмент | Что делает |
|---|---|
| **pyenv** | Менеджер версий Python (компилирует из исходников). Большой стаж. |
| **uv** | Менеджер пакетов + интерпретаторов. Качает готовые бинарники, очень быстро. |
| **asdf** | Универсальный менеджер версий (Python, Node, Ruby, Go и т.д.). |
| **mise** | Наследник asdf: версии языков + переменные окружения + задачи. |
| **conda** | Менеджер окружений и пакетов, в основном для data science. |

## Частые ошибки

- `python --version` показывает системную версию, хотя `pyenv local` сделан → в shell-конфиге нет `eval "$(pyenv init -)"`, прокладки не попали в `PATH` → добавить строку и перезапустить shell; проверить `which python` (должно быть `~/.pyenv/shims/python`).
- `pyenv install` падает с `ModuleNotFoundError: No module named '_ssl'` или `_ctypes` → не хватает системных библиотек для сборки → `brew install openssl readline sqlite3 xz zlib tcl-tk` (macOS) или `build-essential libssl-dev libffi-dev ...` (Debian/Ubuntu), затем переустановить версию.
- Поставили пакет с консольной командой (`pip install black`), а `black` не находится → прокладка ещё не создана → `pyenv rehash`.
- Установка идёт десять минут → pyenv собирает Python из исходников → это нормально; если нужно быстро, `uv python install 3.12` качает готовый бинарник.
- `pyenv global 3.12.3` «сломал» системные утилиты → они рассчитывали на системный `python3` → вернуть `pyenv global system` и задавать версию только через `pyenv local` в проектах.
- В одной сессии нужна другая версия, а `.python-version` переписывать не хочется → `pyenv shell 3.10.0`: действует только в текущем терминале.

## Когда не использовать

Если вы уже работаете с [uv](../uv/README.md), отдельный pyenv не нужен: `uv python install 3.12` и `uv python pin 3.12` делают то же самое, только качают готовые сборки за секунды вместо компиляции. Для нескольких языков сразу (Python + Node + Go) удобнее [mise](../env_management/README.md): один конфиг на проект. В Docker-образе и CI версию Python задаёт базовый образ (`python:3.12-slim`) или `setup-python`, pyenv там лишний. На сервере с одним проектом достаточно Python из дистрибутива или готового бинарника.

## Что спрашивают на собеседовании

- Как на одной машине держать несколько версий Python и не сломать системную? *(pyenv: версии в `~/.pyenv/versions`, системный Python остаётся нетронутым, выбор через `pyenv local` / `global`.)*
- Что такое shims в pyenv? *(Прокладки в `PATH`, которые при каждом вызове выбирают нужную версию по `.python-version` или `PYENV_VERSION`.)*
- Что хранится в `.python-version` и зачем его коммитить? *(Номер версии или имя virtualenv; чтобы у всей команды был одинаковый интерпретатор.)*
- Чем pyenv отличается от venv? *(pyenv выбирает интерпретатор, venv изолирует пакеты; обычно используются вместе.)*
- Почему pyenv ставит версию долго, а uv — быстро? *(pyenv компилирует CPython из исходников, uv качает готовые сборки.)*

## Связанные темы

- [pyenv: сценарии использования](scenarios.md)
- [uv](../uv/README.md)
- [Poetry](../poetry/README.md)
- [pipx](../pipx/README.md)
- [Управление окружением: direnv и mise](../env_management/README.md)
