# pyenv

**pyenv** — менеджер версий Python. Позволяет держать на одной машине несколько версий Python одновременно и переключаться между ними для разных проектов.

Зачем нужен:
- разные проекты требуют разные версии Python;
- системный Python трогать не хочется;
- не зависеть от пакетов дистрибутива.

## Содержание

- [Сценарии использования](scenarios.md) — установка версий, локальный/глобальный Python, pyenv-virtualenv, типовые проблемы

## Установка

### macOS (через Homebrew)
```sh
brew install pyenv
```

### Linux
```sh
curl https://pyenv.run | bash
```

Добавить в `~/.zshrc` (или `~/.bashrc`):
```sh
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init - zsh)"
```

Перезагрузить shell:
```sh
exec "$SHELL"
```

## Основные команды

```sh
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

## Локальный Python для проекта

В корне проекта:
```sh
cd ~/projects/my-app
pyenv local 3.12.3
```

Создаст файл `.python-version` — git закоммитит его, и любой, у кого стоит pyenv, получит ту же версию.

## Приоритет выбора версии

```
1. shell-окружение  (pyenv shell)
2. local            (.python-version в текущей или родительских папках)
3. global           (~/.pyenv/version)
4. system           (системный python)
```

## pyenv-virtualenv (плагин для venv)

```sh
brew install pyenv-virtualenv
# или
git clone https://github.com/pyenv/pyenv-virtualenv.git $(pyenv root)/plugins/pyenv-virtualenv
```

Добавить в `~/.zshrc`:
```sh
eval "$(pyenv virtualenv-init -)"
```

Использование:
```sh
pyenv virtualenv 3.12.3 myapp-3.12       # создать venv
pyenv activate myapp-3.12                # активировать
pyenv deactivate                         # деактивировать
pyenv virtualenvs                        # список
pyenv uninstall myapp-3.12               # удалить
```

Привязать venv к папке:
```sh
cd ~/projects/my-app
pyenv local myapp-3.12     # авто-активация при входе в папку
```

## Частые проблемы

- **`python` не находит pyenv-версию** → нет `eval "$(pyenv init -)"` в shell-конфиге.
- **При установке ошибка про `_ssl`, `_ctypes`** → не хватает системных библиотек:
  ```sh
  # macOS
  brew install openssl readline sqlite3 xz zlib tcl-tk
  ```
- **Долгая установка** → `pyenv` собирает Python из исходников. Альтернатива — использовать `uv python install` (готовые бинарники, быстрее).

## pyenv vs альтернативы

| Инструмент | Что делает |
|---|---|
| **pyenv** | Менеджер версий Python (компилирует из исходников). Большой стаж. |
| **uv** | Менеджер пакетов + интерпретаторов. Качает готовые бинарники, очень быстро. |
| **asdf** | Универсальный менеджер версий (Python, Node, Ruby, Go и т.д.). |
| **conda** | Менеджер окружений и пакетов, в основном для data science. |
