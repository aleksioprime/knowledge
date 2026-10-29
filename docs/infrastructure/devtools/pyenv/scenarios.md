# pyenv — сценарии использования

## Сценарий 1. Поставить новую версию Python

```bash
pyenv --version
```

```bash
# Список того, что можно установить (сильно длинный)
pyenv install --list 2>/dev/null | grep -E '^\s*3\.(11|12|13)\.[0-9]+$' | head -10
```

```bash
# Установка (долго, компилируется из исходников)
pyenv install 3.12.3
```

```bash
pyenv versions   # что уже стоит
```

## Сценарий 2. Глобальная версия

```bash
pyenv global 3.12.3   # системная по умолчанию
pyenv version         # активная сейчас
```

## Сценарий 3. Локальная версия для проекта

Создаёт `.python-version`. Файл коммитится в git — все разработчики получают одну версию.

```bash
mkdir demo-pyenv && cd demo-pyenv
pyenv local 3.11.9
cat .python-version   # 3.11.9
```

## Сценарий 4. Версия только для одной shell-сессии

```bash
pyenv shell 3.10.0
python --version
pyenv shell --unset   # вернуть как было
```

## Сценарий 5. pyenv-virtualenv: venv привязан к папке

```bash
# Создать venv на базе версии
pyenv virtualenv 3.12.3 myapp-3.12

# Список
pyenv virtualenvs

# Привязать к папке (создаётся .python-version с именем venv)
cd my-project
pyenv local myapp-3.12

# Удалить
pyenv virtualenv-delete myapp-3.12
```

## Сценарий 6. Решение типичных проблем

```bash
# Что мешает встроенному python (приоритеты выбора)
pyenv which python
type python
```

```bash
# Часто после установки нового пакета через pip нужно сделать rehash
pyenv rehash
```

### Ошибка `ModuleNotFoundError: No module named '_ssl'`

Не хватает системных библиотек для сборки. Поставь их и переустанови Python:
```sh
# macOS
brew install openssl readline sqlite3 xz zlib tcl-tk

# Ubuntu/Debian
sudo apt install -y make build-essential libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
    libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev \
    libffi-dev liblzma-dev

# затем заново
pyenv install 3.12.3
```

## Связанные темы

- [pyenv](README.md)
- [uv: сценарии](../uv/scenarios.md)
- [Poetry: сценарии](../poetry/scenarios.md)
