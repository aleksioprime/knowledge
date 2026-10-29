# GitHub Actions

Тесты есть, но запускают их не все и не всегда. Однажды в `main` попадает код, который ломает регистрацию, и об этом узнают пользователи. GitHub Actions выполняет нужные команды сам при каждом push и pull request: линтер, тесты, сборку образа, деплой. Pull request с упавшими проверками видно сразу, и его можно запретить сливать.

## Минимальный пример

```yaml
# .github/workflows/tasker.yml
name: Задачник

on:
  push:
    branches: [main]
    paths: ['docs/practice/projects/tasker/**', '.github/workflows/tasker.yml']
  pull_request:
    paths: ['docs/practice/projects/tasker/**', '.github/workflows/tasker.yml']

defaults:
  run:
    working-directory: docs/practice/projects/tasker

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: '3.12'
      - run: pip install ruff==0.8.4
      - run: ruff check .
```

Это начало [настоящего файла](../../../../.github/workflows/tasker.yml), который проверяет [«Задачник»](../../../practice/projects/tasker/README.md) в этом репозитории. Результаты — на вкладке **Actions** в GitHub.

## Как это работает

- **Workflow** — YAML-файл в `.github/workflows/`. В репозитории их может быть несколько.
- **`on`** — события, на которые он запускается: `push`, `pull_request`, `schedule` (по расписанию), `workflow_dispatch` (кнопкой вручную). `paths` сужает запуск: правка заметок про Vue не будет гонять тесты «Задачника».
- **Job** — набор шагов на одной виртуальной машине (`runs-on: ubuntu-latest`). Разные job выполняются **параллельно** на разных машинах, если не указана зависимость `needs`.
- **Step** — либо команда (`run`), либо готовое действие (`uses`) из Marketplace. `actions/checkout` скачивает код репозитория, `actions/setup-python` ставит Python.

Если любая команда завершилась с ненулевым кодом, шаг, job и весь запуск считаются упавшими.

## Тесты с базой данных и Redis

Тестам «Задачника» нужны PostgreSQL и Redis. В GitHub Actions их запускают как **service containers**: Docker-контейнеры, которые живут, пока идёт job:

```yaml
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: tasker
          POSTGRES_PASSWORD: tasker
          POSTGRES_DB: tasker_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U tasker"
          --health-interval 5s
          --health-retries 10
      redis:
        image: redis:7.4
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 5s
          --health-retries 10
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: '3.12'
          cache: pip
          cache-dependency-path: docs/practice/projects/tasker/requirements*.txt
      - run: pip install -r requirements-dev.txt
      - run: pytest -v
```

- `ports` пробрасывает сервисы на `localhost` машины, поэтому тесты подключаются к `localhost:5432` — ровно туда, куда смотрят адреса по умолчанию в [conftest.py](../../../practice/projects/tasker/tests/conftest.py);
- `--health-cmd` заставляет GitHub дождаться готовности базы, прежде чем начать шаги;
- `cache: pip` сохраняет скачанные пакеты между запусками, и установка зависимостей ускоряется.

## Проверка приложения целиком

Третий job поднимает «Задачник» в Docker так же, как вы у себя, и проверяет его снаружи [коллекцией Postman](../../../backend/testing/postman/README.md):

```yaml
  api:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v7
      - run: cp .env.example .env
      - run: docker compose up -d --build --wait
      - run: |
          docker run --rm --network host -v "$PWD/postman":/etc/newman postman/newman:6-alpine \
            run tasker.postman_collection.json --env-var baseUrl=http://localhost:8000
      - if: failure()
        run: docker compose logs app
```

- `needs: test` — запускать только после успешных тестов;
- `--wait` ждёт, пока все контейнеры станут здоровыми. Для этого у сервиса `app` в `docker-compose.yaml` есть `healthcheck`: без него Compose дождался бы только запуска контейнера, а не готовности API;
- `if: failure()` — шаг выполняется, только если что-то упало, и выводит логи приложения. Разбираться в причине без них трудно.

## Деплой (CD)

Деплой обычно делают отдельным workflow. Ниже — шаблон, который **не подключён** в этом репозитории: собрать образ, сохранить его в GitHub Container Registry и обновить сервер по SSH при создании тега версии.

```yaml
# .github/workflows/deploy.yml — шаблон
name: Деплой

on:
  push:
    tags: ['v*']   # git tag v1.2.0 && git push --tags

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write   # право публиковать образ в ghcr.io
    steps:
      - uses: actions/checkout@v7
      - uses: docker/login-action@v4
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v7
        with:
          context: docs/practice/projects/tasker
          push: true
          tags: ghcr.io/${{ github.repository }}/tasker:${{ github.ref_name }}

  deploy:
    runs-on: ubuntu-latest
    needs: build
    environment: production   # можно требовать ручного подтверждения
    steps:
      - name: Обновить сервис на сервере
        env:
          SSH_KEY: ${{ secrets.DEPLOY_SSH_KEY }}
          HOST: ${{ secrets.DEPLOY_HOST }}
          KNOWN_HOSTS: ${{ secrets.DEPLOY_KNOWN_HOSTS }}
        run: |
          mkdir -p ~/.ssh
          echo "$SSH_KEY" > ~/.ssh/id_ed25519 && chmod 600 ~/.ssh/id_ed25519
          echo "$KNOWN_HOSTS" > ~/.ssh/known_hosts
          ssh deploy@$HOST "cd /srv/tasker && TAG=${{ github.ref_name }} docker compose pull && TAG=${{ github.ref_name }} docker compose up -d"
```

Что нужно, чтобы шаблон заработал:

- **секреты** в Settings → Secrets and variables → Actions: закрытый ключ SSH, адрес сервера и строка `known_hosts` (`ssh-keyscan your-server`). `GITHUB_TOKEN` GitHub выдаёт сам на время запуска;
- **на сервере** — пользователь `deploy` с ключом, Docker и `docker-compose.yaml`, где у сервиса указан `image: ghcr.io/.../tasker:${TAG}` вместо `build: .`. Как подготовить сервер, описано в разделе [Linux](../../linux/README.md);
- **окружение `production`** в Settings → Environments, если нужно ручное подтверждение деплоя.

## Несколько версий Python, отчёты и сообщение о результате

Ещё три вещи, которые часто добавляют в проверки pull request:

- прогнать тесты на всех версиях Python, которые поддерживает проект;
- сохранить отчёты, чтобы не искать причину падения в логах;
- написать в чат команды, чем закончилась проверка.

```yaml
on:
  pull_request:
    branches: [main]

concurrency:
  group: tasker-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: '3.12'
      - run: pip install ruff==0.8.4 mypy==1.13.0
      - name: Линтер
        run: ruff check . --output-format=github
      - name: Проверка типов
        run: mypy app

  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ['3.12', '3.13']
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -r requirements-dev.txt
      - name: Тесты
        run: pytest --junitxml=report.xml --cov=app --cov-report=html
      - uses: actions/upload-artifact@v7
        if: always()
        with:
          name: report-${{ matrix.python-version }}
          path: |
            docs/practice/projects/tasker/report.xml
            docs/practice/projects/tasker/htmlcov/

  notify:
    runs-on: ubuntu-latest
    needs: [lint, test]
    if: always()
    permissions:
      actions: read
    steps:
      - name: Сообщить в Telegram
        env:
          GH_TOKEN: ${{ github.token }}
          TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
          RESULTS: ${{ join(needs.*.result, ' ') }}
          SHA: ${{ github.event.pull_request.head.sha }}
        run: |
          if echo "$RESULTS" | grep -qE 'failure|cancelled'; then
            status='с ошибкой'
            failed=$(gh api --paginate "repos/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID/jobs?per_page=100" \
              --jq '.jobs[] | select(.conclusion == "failure")
                    | "\(.name): \([.steps[] | select(.conclusion == "failure") | .name] | join(", "))"')
          else
            status='успешно'
            failed=''
          fi
          text=$(printf '%s: пайплайн для %s завершился %s\n%s\n%s/%s/actions/runs/%s' \
            "$GITHUB_REPOSITORY" "${SHA:0:7}" "$status" "$failed" \
            "$GITHUB_SERVER_URL" "$GITHUB_REPOSITORY" "$GITHUB_RUN_ID")
          curl -sS --fail-with-body -o /dev/null "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
            --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" --data-urlencode "text=${text}"
```

Это фрагмент, а не файл из репозитория: `defaults` и `paths` — как в минимальном примере выше. [actionlint](https://github.com/rhysd/actionlint) 1.7.12 замечаний к нему не нашёл.

- **`strategy.matrix`** превращает один job в несколько: `test (3.12)` и `test (3.13)` идут параллельно. `fail-fast: false` не даёт остановить вторую версию, когда упала первая. Иначе не видно, ломается код везде или только на одной версии.
- **`--output-format=github`** выводит замечания ruff так, что GitHub показывает их прямо в строках diff pull request.
- **`upload-artifact`** с `if: always()` сохраняет отчёты и при упавших тестах: JUnit XML и HTML-отчёт о покрытии. Их можно скачать со страницы запуска. По умолчанию артефакты хранятся 90 дней, срок меняется параметром `retention-days`.
- **`concurrency`** с `cancel-in-progress` отменяет старый запуск, если в тот же pull request пришёл новый коммит. Минуты не тратятся на проверку кода, который уже устарел.
- **`notify`** ждёт остальные job (`needs`), а `if: always()` запускает его, даже когда они упали. Иначе сообщение приходило бы только об успехе. Результаты job берутся из `needs.*.result`. Названия упавших job и шагов `needs` не знает, поэтому скрипт берёт их из API запусков через `gh`. Для этого job нужно право `actions: read`.
- **Секреты:** токен бота от `@BotFather` и id чата лежат в Secrets репозитория.
- **Pull request из форков** секретов не получают, и сообщение не уйдёт. Для открытых проектов это нормально.

Пример сообщения. Его собрал тот же скрипт: вместо отправки в Telegram был вывод на экран, разбирался настоящий упавший запуск из репозитория CPython:

```text
python/cpython: пайплайн для 0123456 завершился с ошибкой
Sanitizers / TSan (free-threading): Tests
All required checks pass: Check whether the needed jobs succeeded or failed
https://github.com/python/cpython/actions/runs/40835280743
```

Слева от двоеточия — job, справа — упавший шаг. Хэш коммита в этой проверке подставной.

**Запрет пушить в `main`** настраивается не в workflow, а в Settings → Rules → Rulesets для ветки `main`:

- требовать pull request;
- требовать успешных проверок (выбрать нужные job, например `lint` и `test (3.12)`);
- запретить force push.

Без этого проверки только информируют: слить красный pull request или запушить мимо него всё ещё можно.

## Частые ошибки

- **Секреты в YAML.** Пароль, вписанный прямо в workflow, виден всем, у кого есть доступ к репозиторию. Только `${{ secrets.ИМЯ }}`. GitHub скрывает значения секретов в логах, но не защищает от `echo $SECRET | base64`.
- **Плавающие версии действий и образов.** `uses: some/action@main` может однажды измениться и сломать сборку, а то и выполнить чужой код с доступом к секретам. Указывайте версию (`@v7`), а для сторонних действий — полный хэш коммита.
- **Устаревшие версии действий.** Старые мажорные версии перестают поддерживаться. Например, `actions/checkout@v4` и `actions/setup-python@v5` собраны под Node 20, и GitHub выводит предупреждение `Node.js 20 is deprecated`. Периодически поднимайте мажорные версии: после перехода на `checkout@v7` и `setup-python@v7` это предупреждение пропало. Помогает Dependabot с `package-ecosystem: github-actions`.
- **`localhost` для service containers при запуске в контейнере.** Если сам job запускается в контейнере (`container:`), сервисы доступны по имени (`postgres`), а не через `localhost`.
- **Тесты ждут, что база уже есть.** Без `--health-cmd` шаги стартуют раньше, чем PostgreSQL готов принимать подключения.
- **Workflow запускается на каждый чих.** Без `paths` любая правка README гоняет все проверки и тратит минуты.

## Когда не использовать

GitHub Actions привязан к GitHub. Если код живёт в GitLab или на своём сервере, берут GitLab CI или Jenkins: идеи те же, а перенести workflow один в один не получится. Проекты, которые нельзя собирать на чужих машинах (закрытый контур, лицензии), требуют собственных раннеров (self-hosted runners) или своей системы CI.

Для скрипта на вечер или репозитория без тестов workflow нечего проверять: он будет только гонять `pip install`. Начните с тестов и линтера локально, а CI подключите, когда появится что запускать. И не делайте из workflow планировщик задач: `schedule` стартует с задержкой до десятков минут и может пропускаться при нагрузке — для регулярных заданий есть cron, Celery Beat и [Airflow](../../../data/engineering/airflow/README.md).

## Связанные темы

- [Docker Compose на практике](../../devtools/docker/compose.md)
- [Postman и Newman](../../../backend/testing/postman/README.md)
- [Pytest](../../../backend/testing/pytest/README.md)
- [Линтеры](../../devtools/linter/README.md)
