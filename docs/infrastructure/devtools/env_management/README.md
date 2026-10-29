# Управление окружением

Инструменты, которые **автоматически** активируют нужный набор переменных окружения, версии языков и виртуальных окружений при входе в папку проекта. Заходишь в `~/projects/my-app` — у тебя сразу нужный Python, нужный venv, нужные `DATABASE_URL` и `API_KEY`. Выходишь — всё снимается.

Зачем это нужно:
- разные проекты — разные секреты и конфигурации;
- не таскать руками `source .venv/bin/activate` и `export …`;
- разные версии Python/Node на проект.

## Содержание

> Готовые шаблоны для типичных проектов будут добавляться по мере проработки темы.

## Два инструмента

| Инструмент | Что делает |
|---|---|
| **direnv** | Подгружает переменные окружения из `.envrc` при входе в папку |
| **mise** | direnv + менеджер версий языков (заменяет pyenv, nvm, asdf) |

---

## direnv

Маленькая утилита: видит файл `.envrc` в текущей папке — выполняет его и подгружает переменные. Выход из папки — переменные снимаются.

### Установка

```sh
brew install direnv          # macOS
sudo apt install direnv      # Ubuntu/Debian
```

Подключение в shell (`~/.zshrc` или `~/.bashrc`):
```sh
eval "$(direnv hook zsh)"     # для zsh
# eval "$(direnv hook bash)"  # для bash
```

### Базовое использование

В корне проекта создаём `.envrc`:
```sh
# .envrc
export DATABASE_URL="postgresql://admin:1q2w3e@localhost:5432/myapp"
export REDIS_URL="redis://localhost:6379/0"
export ENV="local"
export DEBUG=1
```

Первый раз direnv заблокирует выполнение (мера безопасности):
```sh
cd my-project
# direnv: error /Users/me/my-project/.envrc is blocked
direnv allow                 # подтвердить, что доверяешь файлу
```

После этого:
```sh
$ cd my-project
direnv: loading ~/my-project/.envrc
direnv: export +DATABASE_URL +REDIS_URL +DEBUG +ENV

$ echo $DATABASE_URL
postgresql://admin:1q2w3e@localhost:5432/myapp

$ cd ..
direnv: unloading
```

### Авто-активация venv

```sh
# .envrc
source .venv/bin/activate
```

Или через готовую функцию `layout`:
```sh
# .envrc
layout python3                # создаст .direnv/python-3.x.x/ и активирует
```

Для poetry / uv:
```sh
# Poetry
export VIRTUAL_ENV=$(poetry env info --path)
PATH_add $VIRTUAL_ENV/bin

# uv
PATH_add .venv/bin
export VIRTUAL_ENV=$PWD/.venv
```

### Загрузка из .env

Если уже есть `.env` файл (например, для Docker), не дублируй — подключи его:
```sh
# .envrc
dotenv .env
dotenv_if_exists .env.local      # необязательный
```

### .gitignore

```
# .gitignore
.envrc                # ❗ если есть секреты
.envrc.local          # локальные оверрайды
.direnv/              # кэш direnv
```

Часто делают так:
- `.envrc.template` коммитят (с пустыми значениями) — как образец;
- `.envrc` НЕ коммитят, каждый разработчик заполняет сам.

### Полезные хелперы (встроенные функции)

```sh
# .envrc

# добавить в PATH
PATH_add bin
PATH_add ./node_modules/.bin

# подключить .env-файл
dotenv

# подключить .envrc из другой папки (для монорепо)
source_up_if_exists

# обновить выполнение при изменении файла
watch_file requirements.txt
```

---

## mise

**mise** (раньше `rtx`) — современный «всё-в-одном»: менеджер версий языков + переменные окружения. Заменяет: pyenv + nvm + rbenv + direnv + asdf.

### Установка

```sh
brew install mise              # macOS
curl https://mise.run | sh     # Linux
```

В shell-конфиг (`~/.zshrc`):
```sh
eval "$(mise activate zsh)"
```

### Конфиг mise.toml

Один файл на проект — описывает версии языков и переменные:
```toml
# .mise.toml в корне проекта

[tools]
python = "3.12.3"
node = "20.11.0"
uv = "latest"

[env]
DATABASE_URL = "postgresql://admin:1q2w3e@localhost:5432/myapp"
REDIS_URL = "redis://localhost:6379/0"
DEBUG = "1"

# Загрузить из .env-файла
_.file = ".env.local"

# Активировать venv проекта
_.python.venv = ".venv"

[tasks.dev]
description = "Запустить приложение"
run = "uv run fastapi dev src/main.py"

[tasks.test]
description = "Тесты"
run = "uv run pytest"
```

После `cd my-project`:
- mise проверит, что нужный Python и Node установлены, иначе скачает;
- активирует venv `.venv`;
- экспортирует переменные;
- задачи доступны как `mise run dev`, `mise run test`.

### Команды

```sh
mise install                  # установить все версии из .mise.toml
mise use python@3.12          # назначить версию для проекта
mise use -g node@lts          # глобально

mise ls                       # установленные версии
mise ls-remote python         # доступные для установки

mise current                  # текущие версии для папки

mise run test                 # запустить задачу из [tasks.*]
mise tasks                    # список задач

mise trust                    # доверять конфигу (как direnv allow)
```

### Совместимость

- mise читает `.tool-versions` от **asdf** — миграция почти бесплатна.
- mise читает `.python-version` от **pyenv** — тоже работает.
- mise читает `.nvmrc` от **nvm**.

---

## direnv vs mise

|  | direnv | mise |
|---|---|---|
| Переменные окружения | ✅ | ✅ |
| Версии языков | ❌ (нужен pyenv/asdf отдельно) | ✅ |
| Авто-активация venv | через layout | встроено |
| Запуск задач (как Make/Just) | ❌ | ✅ |
| Размер/сложность | минимальный | средний |

**Если просто нужны переменные** — direnv (один файл, всё прозрачно).
**Если нужно ещё управление версиями и задачами** — mise (один инструмент вместо четырёх).

---

## Безопасность

В `.envrc` / `.mise.toml` могут быть секреты. Несколько правил:

1. **Не коммить файлы с секретами.** Добавь в `.gitignore`.
2. **Делай шаблоны:** `.envrc.template` / `.mise.toml.template` без значений.
3. **Не доверяй чужим репо вслепую:** `direnv allow` / `mise trust` запускают код. Прочитай файл перед подтверждением.
4. **Для прода** — секреты не из файла на диске, а из vault/secret manager (Vault, AWS Secrets, sealed-secrets).

## Что спрашивают на собеседовании

- Чем `.envrc` отличается от `.env`? *(`.env` — пассивный файл с парами KEY=VALUE, читают приложения. `.envrc` — скрипт, исполняется direnv и кладёт в shell.)*
- Почему direnv просит `direnv allow`? *(Любой файл в репозитории мог бы выполнить код при `cd`. Защита от вредоносных репо.)*
- Как настроить разный `DATABASE_URL` для прода и локалки? *(Не коммитить `.envrc` с прод-значениями. Использовать `.envrc.local` или подгружать из vault.)*
