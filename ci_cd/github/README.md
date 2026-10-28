# GitHub Actions

Тесты есть, но запускают их не все и не всегда. Однажды в `main` попадает код, который ломает регистрацию, и об этом узнают пользователи. GitHub Actions выполняет нужные команды сам при каждом push и pull request: линтер, тесты, сборку образа, деплой. Pull request с упавшими проверками видно сразу, и его можно запретить сливать.

## Минимальный пример

```yaml
# .github/workflows/tasker.yml
name: Задачник

on:
  push:
    branches: [main]
    paths: ['pet/tasker/**', '.github/workflows/tasker.yml']
  pull_request:
    paths: ['pet/tasker/**', '.github/workflows/tasker.yml']

defaults:
  run:
    working-directory: pet/tasker

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

Это начало [настоящего файла](../../.github/workflows/tasker.yml), который проверяет [«Задачник»](../../pet/tasker/README.md) в этом репозитории. Результаты — на вкладке **Actions** в GitHub.

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
          cache-dependency-path: pet/tasker/requirements*.txt
      - run: pip install -r requirements-dev.txt
      - run: pytest -v
```

- `ports` пробрасывает сервисы на `localhost` машины, поэтому тесты подключаются к `localhost:5432` — ровно туда, куда смотрят адреса по умолчанию в [conftest.py](../../pet/tasker/tests/conftest.py);
- `--health-cmd` заставляет GitHub дождаться готовности базы, прежде чем начать шаги;
- `cache: pip` сохраняет скачанные пакеты между запусками, и установка зависимостей ускоряется.

## Проверка приложения целиком

Третий job поднимает «Задачник» в Docker так же, как вы у себя, и проверяет его снаружи [коллекцией Postman](../../tests/postman/README.md):

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
          context: pet/tasker
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

## Частые ошибки

- **Секреты в YAML.** Пароль, вписанный прямо в workflow, виден всем, у кого есть доступ к репозиторию. Только `${{ secrets.ИМЯ }}`. GitHub скрывает значения секретов в логах, но не защищает от `echo $SECRET | base64`.
- **Плавающие версии действий и образов.** `uses: some/action@main` может однажды измениться и сломать сборку, а то и выполнить чужой код с доступом к секретам. Указывайте версию (`@v7`), а для сторонних действий — полный хэш коммита.
- **Устаревшие версии действий.** Старые мажорные версии перестают поддерживаться. Например, `actions/checkout@v4` и `actions/setup-python@v5` собраны под Node 20, и GitHub выводит предупреждение `Node.js 20 is deprecated`. Периодически поднимайте мажорные версии — после этого прогон этого workflow проходит без предупреждений. Помогает Dependabot с `package-ecosystem: github-actions`.
- **`localhost` для service containers при запуске в контейнере.** Если сам job запускается в контейнере (`container:`), сервисы доступны по имени (`postgres`), а не через `localhost`.
- **Тесты ждут, что база уже есть.** Без `--health-cmd` шаги стартуют раньше, чем PostgreSQL готов принимать подключения.
- **Workflow запускается на каждый чих.** Без `paths` любая правка README гоняет все проверки и тратит минуты.

## Связанные темы

- [Docker Compose на практике](../../devtools/docker/docs/compose.md)
- [Postman и Newman](../../tests/postman/README.md)
- [Pytest](../../tests/pytest/README.md)
- [Линтеры](../../devtools/linter/README.md)
