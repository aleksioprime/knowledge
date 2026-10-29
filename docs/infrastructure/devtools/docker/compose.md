# Docker Compose на практике

Приложению нужны база, Redis, воркер фоновых задач и планировщик. Запускать всё это пятью командами `docker run` с длинными параметрами неудобно, а новичок в команде точно что-нибудь перепутает. Docker Compose описывает всю систему в одном файле: какие сервисы, как они связаны, какие у них настройки. Запуск — одна команда.

Основные команды Docker и простой пример — в [README раздела](README.md). Здесь — то, что встречается в настоящих проектах, на примере [«Задачника»](../../../practice/projects/tasker/docker-compose.yaml).

## Минимальный пример

```yaml
# docker-compose.yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:16
    env_file: .env
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 5s
      retries: 5

volumes:
  pgdata:
```

```bash
docker compose up -d --build
docker compose ps
```

```text
SERVICE   STATUS
app       Up 4 seconds
db        Up 9 seconds (healthy)
```

## Как это работает

**Сервисы видят друг друга по имени.** Compose создаёт для проекта общую сеть, а имя сервиса становится адресом в ней:

```bash
docker compose exec app python -c "import socket; print(socket.gethostbyname('db'))"
# 172.20.0.3
```

Поэтому в `.env` адрес базы — `db:5432`, а не `localhost:5432`. Внутри контейнера `localhost` — это сам контейнер, и там базы нет:

```text
ConnectionRefusedError: [Errno 111] Connection refused
```

`ports: "8000:8000"` нужен только для того, чтобы зайти в сервис **с вашей машины**. Друг с другом сервисы общаются без него.

**`depends_on` с `condition: service_healthy`** ждёт, пока проверка здоровья базы не начнёт проходить. Без условия Compose ждёт только *запуска контейнера*, а PostgreSQL внутри ещё несколько секунд готовится, и приложение падает на первом подключении.

```text
Container kb-tasker-db-1   Waiting
Container kb-tasker-db-1   Healthy
Container kb-tasker-app-1  Started
```

`$$` в `healthcheck` — экранирование: переменную `$POSTGRES_USER` подставит оболочка внутри контейнера, а не Compose при чтении файла.

**Именованный том** (`pgdata`) хранит данные базы между перезапусками. `docker compose down` его не трогает, а `docker compose down -v` удаляет вместе с данными.

## Настройки через `.env`

```bash
# .env.example — лежит в репозитории
POSTGRES_DB=tasker
POSTGRES_USER=tasker
POSTGRES_PASSWORD=tasker
DATABASE_URL=postgresql+asyncpg://tasker:tasker@db:5432/tasker
```

В репозиторий кладут `.env.example`, а настоящий `.env` создаёт каждый у себя (`cp .env.example .env`) и добавляет в `.gitignore`. Так пароли не попадают в git.

`env_file` передаёт переменные **в контейнер**. Кроме того, Compose сам читает `.env` рядом с файлом и подставляет `${ПЕРЕМЕННАЯ}` в сам `docker-compose.yaml`. Это два разных механизма, их легко спутать.

## Один образ, несколько ролей

API, воркер и планировщик Celery в «Задачнике» собираются из одного `Dockerfile`, но запускают разные команды:

```yaml
  worker:
    build: .
    command: celery -A app.worker worker --loglevel=info
    env_file: .env

  beat:
    build: .
    command: celery -A app.worker beat --loglevel=info
    env_file: .env
```

Несколько копий воркера:

```bash
docker compose up -d --scale worker=3
# kb-tasker-worker-1, kb-tasker-worker-2, kb-tasker-worker-3
```

Масштабировать можно только сервисы без фиксированного `ports` наружу и без `container_name`: два контейнера не могут занять один порт на вашей машине.

## Настройки для разработки: override-файл

Для разработки удобно, чтобы код подхватывался без пересборки образа. Файл `docker-compose.override.yaml` Compose подмешивает к основному автоматически:

```yaml
# docker-compose.override.yaml
services:
  app:
    command: sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
    volumes:
      - ./app:/code/app
```

Папка `app` с вашей машины подключается внутрь контейнера, а `--reload` перезапускает сервер при изменении файла:

```text
WARNING:  WatchFiles detected changes in 'app/main.py'. Reloading...
```

Итоговую конфигурацию после слияния файлов показывает `docker compose config`.

Для продакшена override обычно не кладут на сервер или явно указывают файлы: `docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d`.

## Полезные команды

```bash
docker compose up -d --build        # собрать и запустить в фоне
docker compose ps                   # состояние и проверки здоровья
docker compose logs -f app          # логи сервиса
docker compose exec db psql -U tasker  # зайти в работающий контейнер
docker compose run --rm app pytest  # одноразовый контейнер для команды
docker compose restart worker
docker compose down                 # остановить и удалить контейнеры (тома остаются)
docker compose down -v              # то же вместе с томами — данные базы пропадут
```

## Частые ошибки

- **`localhost` в адресе соседнего сервиса.** Внутри контейнера используйте имя сервиса: `db`, `redis`.
- **`depends_on` без проверки здоровья.** Приложение стартует раньше, чем база готова принимать подключения.
- **Override заменил команду и потерял миграции.** В «Задачнике» `CMD` в `Dockerfile` сначала выполняет `alembic upgrade head`. Если в override написать просто `command: uvicorn ... --reload`, миграции перестанут применяться. Повторяйте всю цепочку команд.
- **`down -v` по привычке.** Вместе с томами удаляются данные базы.
- **Изменения в `requirements.txt` не применились.** Зависимости устанавливаются при сборке образа. После изменения нужен `docker compose up -d --build`.
- **Порт уже занят.** `Bind for 0.0.0.0:5432 failed: port is already allocated` — на машине уже работает PostgreSQL. Поменяйте внешний порт: `"5433:5432"`.

## Связанные темы

- [Docker: основы](README.md)
- [Учебный проект «Задачник»](../../../practice/projects/tasker/README.md)
- [GitHub Actions](../../cicd/github/README.md) — те же сервисы в CI
- [Kubernetes](../../cicd/kubernetes/README.md) — когда одной машины мало
