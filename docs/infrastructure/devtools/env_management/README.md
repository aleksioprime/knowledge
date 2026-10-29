# Управление окружением

Перед работой над проектом приходится вспоминать ритуал: `source .venv/bin/activate`, `export DATABASE_URL=...`, переключить версию Python, а в соседнем проекте — всё другое, и забытая переменная из прошлого проекта незаметно ломает текущий. **direnv** и **mise** делают это автоматически: зашли в папку — подгрузились переменные, venv и версии языков; вышли — всё снялось.

## Содержание

> Готовые шаблоны для типичных проектов будут добавляться по мере проработки темы.

## Минимальный пример

Файл `.envrc` в корне проекта: при входе в папку direnv экспортирует переменные и добавляет `.venv/bin` в `PATH`, при выходе убирает.

```bash
brew install direnv                             # Ubuntu: sudo apt install direnv
echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc && exec "$SHELL"

cd ~/projects/tasker
cat > .envrc <<'ENVRC'
export DATABASE_URL="postgresql://admin:1q2w3e@localhost:5432/tasker"
export DEBUG=1
PATH_add .venv/bin
ENVRC

# direnv: error /Users/me/projects/tasker/.envrc is blocked. Run `direnv allow` to approve its content
direnv allow
# direnv: loading ~/projects/tasker/.envrc
# direnv: export +DATABASE_URL +DEBUG ~PATH

echo $DATABASE_URL                              # postgresql://admin:1q2w3e@localhost:5432/tasker
which python                                    # /Users/me/projects/tasker/.venv/bin/python

cd ..
# direnv: unloading
echo $DATABASE_URL                              # (пусто)
```

## Как это работает

Хук в shell-конфиге после каждой команды проверяет, есть ли в текущей или родительской папке `.envrc` (для mise — `mise.toml`). direnv выполняет файл в отдельном bash-процессе, сравнивает окружение до и после и переносит разницу в вашу текущую сессию; при выходе из папки восстанавливает прежнее состояние. Поэтому `.envrc` — это скрипт, а не список пар, и поэтому direnv требует явного `direnv allow`: иначе любой склонированный репозиторий мог бы выполнить код при `cd`. mise устроен так же, но помимо переменных подменяет в `PATH` нужные версии языков и умеет запускать задачи.

### Два инструмента

| Инструмент | Что делает |
|---|---|
| **direnv** | Подгружает переменные окружения из `.envrc` при входе в папку |
| **mise** | direnv + менеджер версий языков (заменяет pyenv, nvm, asdf) |

### direnv

Маленькая утилита: видит файл `.envrc` в текущей папке — выполняет его и подгружает переменные. Выход из папки — переменные снимаются.

#### Установка

```bash
brew install direnv          # macOS
sudo apt install direnv      # Ubuntu/Debian
```

Подключение в shell (`~/.zshrc` или `~/.bashrc`):

```bash
eval "$(direnv hook zsh)"     # для zsh
# eval "$(direnv hook bash)"  # для bash
```

#### Базовое использование

В корне проекта создаём `.envrc`:

```bash
# .envrc
export DATABASE_URL="postgresql://admin:1q2w3e@localhost:5432/myapp"
export REDIS_URL="redis://localhost:6379/0"
export ENV="local"
export DEBUG=1
```

Первый раз direnv заблокирует выполнение (мера безопасности):

```bash
cd my-project
# direnv: error /Users/me/my-project/.envrc is blocked
direnv allow                 # подтвердить, что доверяешь файлу
```

После этого:

```bash
cd my-project
# direnv: loading ~/my-project/.envrc
# direnv: export +DATABASE_URL +REDIS_URL +DEBUG +ENV

echo $DATABASE_URL
# postgresql://admin:1q2w3e@localhost:5432/myapp

cd ..
# direnv: unloading
```

#### Авто-активация venv

```bash
# .envrc
source .venv/bin/activate
```

Или через готовую функцию `layout`:

```bash
# .envrc
layout python3                # создаст .direnv/python-3.x.x/ и активирует
```

Для poetry / uv:

```bash
# Poetry
export VIRTUAL_ENV=$(poetry env info --path)
PATH_add $VIRTUAL_ENV/bin

# uv
PATH_add .venv/bin
export VIRTUAL_ENV=$PWD/.venv
```

#### Загрузка из .env

Если уже есть `.env` файл (например, для Docker), не дублируй — подключи его:

```bash
# .envrc
dotenv .env
dotenv_if_exists .env.local      # необязательный
```

#### .gitignore

```
# .gitignore
.envrc                # если есть секреты
.envrc.local          # локальные оверрайды
.direnv/              # кэш direnv
```

Часто делают так:

- `.envrc.template` коммитят (с пустыми значениями) — как образец;
- `.envrc` не коммитят, каждый разработчик заполняет сам.

#### Полезные хелперы (встроенные функции)

```bash
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

### mise

**mise** (раньше `rtx`) — современный «всё-в-одном»: менеджер версий языков + переменные окружения. Заменяет: pyenv + nvm + rbenv + direnv + asdf.

#### Установка

```bash
brew install mise              # macOS
curl https://mise.run | sh     # Linux
```

В shell-конфиг (`~/.zshrc`):

```bash
eval "$(mise activate zsh)"
```

#### Конфиг mise.toml

Один файл на проект — описывает версии языков и переменные:

```toml
# mise.toml в корне проекта (старое имя .mise.toml тоже читается)

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

- mise проверит, что нужный Python и Node установлены, иначе предложит `mise install`;
- активирует venv `.venv`;
- экспортирует переменные;
- задачи доступны как `mise run dev`, `mise run test`.

#### Команды

```bash
mise install                  # установить все версии из mise.toml
mise use python@3.12          # назначить версию для проекта
mise use -g node@lts          # глобально

mise ls                       # установленные версии
mise ls-remote python         # доступные для установки

mise current                  # текущие версии для папки

mise run test                 # запустить задачу из [tasks.*]
mise tasks                    # список задач

mise trust                    # доверять конфигу (как direnv allow)
```

#### Совместимость

- mise читает `.tool-versions` от **asdf** — миграция почти бесплатна.
- mise читает `.python-version` от **pyenv** — тоже работает.
- mise читает `.nvmrc` от **nvm**.

### direnv vs mise

|  | direnv | mise |
|---|---|---|
| Переменные окружения | да | да |
| Версии языков | нет (нужен pyenv/asdf отдельно) | да |
| Авто-активация venv | через layout | встроено |
| Запуск задач (как Make/Just) | нет | да |
| Размер/сложность | минимальный | средний |

**Если просто нужны переменные** — direnv (один файл, всё прозрачно).
**Если нужно ещё управление версиями и задачами** — mise (один инструмент вместо четырёх).

### Безопасность

В `.envrc` / `mise.toml` могут быть секреты. Несколько правил:

1. **Не коммить файлы с секретами.** Добавь в `.gitignore`.
2. **Делай шаблоны:** `.envrc.template` / `mise.toml.template` без значений.
3. **Не доверяй чужим репо вслепую:** `direnv allow` / `mise trust` запускают код. Прочитай файл перед подтверждением.
4. **Для прода** — секреты не из файла на диске, а из vault/secret manager (Vault, AWS Secrets, sealed-secrets).

## Частые ошибки

- Зашли в папку, а переменных нет и сообщений direnv тоже → хук не подключён в shell-конфиге → добавить `eval "$(direnv hook zsh)"` (для mise — `mise activate zsh`) и перезапустить shell.
- Поправили `.envrc`, direnv пишет `.envrc is blocked` → после каждого изменения файла доверие сбрасывается → `direnv allow` заново (это и есть защита от подмены файла).
- `.envrc` с паролями попал в git → секреты в истории репозитория → добавить `.envrc` в `.gitignore`, коммитить `.envrc.template`, а утёкшие пароли сменить.
- `source .venv/bin/activate` в `.envrc` «не работает» в другом shell или после пересоздания venv → активация зависит от конкретного пути и shell → использовать `PATH_add .venv/bin` или `layout python3`.
- Переменные из `.envrc` не видят `docker compose` и приложение в контейнере → direnv меняет окружение только текущего shell → для контейнеров держать `.env` и подключать его в `.envrc` через `dotenv .env`, чтобы не дублировать.
- Скрипт в `.envrc` выполняется долго (`poetry env info` на каждый `cd`) → задержка при каждом переходе между папками → кешировать результат (`export VIRTUAL_ENV=$PWD/.venv`) или перейти на `_.python.venv` в mise.
- `direnv allow` в чужом склонированном репозитории без чтения `.envrc` → выполнение произвольного кода → сначала `cat .envrc`.

## Когда не использовать

На сервере и в CI окружение задаёт оркестратор или пайплайн (переменные в Docker Compose, Kubernetes Secrets, секреты GitHub Actions), а не файл при `cd`: direnv и mise — инструменты рабочей машины разработчика. Если переменные читает только приложение, достаточно `.env` и `pydantic-settings`: shell-экспорт тут не нужен. Если в проекте один Python и уже есть [uv](../uv/README.md) с `uv run`, активация venv решена без direnv, а версии Python — через `uv python pin`. mise как менеджер версий избыточен, когда язык один и есть [pyenv](../pyenv/README.md) или uv.

## Что спрашивают на собеседовании

- Чем `.envrc` отличается от `.env`? *(`.env` — пассивный файл с парами KEY=VALUE, читают приложения. `.envrc` — скрипт, исполняется direnv и кладёт в shell.)*
- Почему direnv просит `direnv allow`? *(Любой файл в репозитории мог бы выполнить код при `cd`. Защита от вредоносных репо.)*
- Как настроить разный `DATABASE_URL` для прода и локалки? *(Не коммитить `.envrc` с прод-значениями. Использовать `.envrc.local` или подгружать из vault.)*
- Как direnv снимает переменные при выходе из папки? *(Запоминает разницу окружения до и после выполнения `.envrc` и откатывает её.)*
- Чем mise отличается от direnv и pyenv? *(Один инструмент: переменные + версии нескольких языков + задачи; читает конфиги asdf, pyenv и nvm.)*

## Связанные темы

- [pyenv](../pyenv/README.md)
- [uv](../uv/README.md)
- [Poetry](../poetry/README.md)
- [Task Runners](../task_runners/README.md)
- [Docker](../docker/README.md)
