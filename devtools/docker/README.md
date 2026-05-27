# Docker

**Docker** — платформа для упаковки приложений и их зависимостей в изолированные контейнеры. Контейнер запускается одинаково на любой машине, где установлен Docker.

## Ключевые понятия

- **Image** — шаблон контейнера (immutable). Состоит из слоёв.
- **Container** — запущенный экземпляр образа.
- **Dockerfile** — рецепт сборки образа.
- **Volume** — постоянное хранилище, переживающее перезапуск контейнера.
- **Bind mount** — пробрасывание директории хоста в контейнер.
- **Network** — изолированные сети между контейнерами.
- **Docker Compose** — оркестрация нескольких контейнеров через `docker-compose.yml`.
- **Registry** — хранилище образов (Docker Hub, GHCR, GitLab Registry).

## Основные команды

### Образы
```sh
docker pull nginx:1.27               # скачать образ
docker images                        # список локальных образов
docker rmi <image>                   # удалить образ
docker build -t myapp:1.0 .          # собрать образ из Dockerfile в текущей папке
docker image prune                   # удалить «висящие» образы
```

### Контейнеры
```sh
docker run -d --name web -p 8080:80 nginx        # запустить в фоне
docker ps                                         # список запущенных
docker ps -a                                      # все, включая остановленные
docker logs -f web                                # смотреть логи
docker exec -it web bash                          # зайти в контейнер
docker stop web && docker rm web                  # остановить и удалить
docker container prune                            # удалить все остановленные
```

### Тома и сети
```sh
docker volume create pgdata
docker volume ls
docker volume rm pgdata

docker network create app_net
docker network ls
```

### Очистка
```sh
docker system df          # сколько занято места
docker system prune -a    # снести всё неиспользуемое (осторожно)
```

## Пример Dockerfile (Python-приложение)

```dockerfile
# 1. Базовый образ
FROM python:3.12-slim

# 2. Рабочая директория внутри контейнера
WORKDIR /app

# 3. Зависимости (отдельным слоем — кешируется)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Код приложения
COPY . .

# 5. Порт и команда запуска
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Multi-stage build (тоньше итоговый образ)

```dockerfile
# Stage 1: сборка
FROM python:3.12 AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt

# Stage 2: рантайм
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/*
COPY . .
CMD ["python", "main.py"]
```

## Пример docker-compose.yml

```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://admin:1q2w3e@db:5432/app
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./app:/app

  db:
    image: postgres:16
    environment:
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: 1q2w3e
      POSTGRES_DB: app
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U admin -d app"]
      interval: 5s
      retries: 5

volumes:
  pgdata:
```

Запуск:
```sh
docker compose up -d --build
docker compose logs -f api
docker compose down              # остановить и удалить контейнеры
docker compose down -v           # + удалить тома
```

## Лучшие практики

- Используй **`.dockerignore`** — исключай `__pycache__/`, `.git`, `node_modules/`, `*.env`.
- **Кешируй зависимости отдельным слоем** — сначала `COPY requirements.txt && pip install`, потом `COPY .`.
- Тэги **`:latest`** — зло в проде. Фиксируй версии.
- Не запускай контейнер от root — добавь `USER appuser`.
- **Multi-stage builds** уменьшают размер образа в 2–10 раз.
- Один контейнер = один процесс. Для нескольких сервисов — compose.
- Используй **healthcheck** для зависимостей.

## Что спрашивают на собеседовании

- В чём разница между **image** и **container**?
- В чём разница между **volume** и **bind mount**?
- Что такое **layer** и как работает **кеш слоёв**?
- Чем отличается **`CMD`** от **`ENTRYPOINT`**? *(ENTRYPOINT — программа, CMD — её аргументы.)*
- Чем **`COPY`** отличается от **`ADD`**? *(ADD умеет распаковывать архивы и качать по URL — но обычно лучше COPY.)*
- Что такое **multi-stage build** и зачем он нужен?
- Как контейнеры общаются между собой? *(По имени сервиса внутри одной docker-сети.)*

## Содержание

- [Установка Docker на сервер Ubuntu](docs/install.md)
