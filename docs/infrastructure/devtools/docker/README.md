# Docker

Docker нужен, когда «у меня работает» перестаёт быть аргументом: на сервере другая версия Python, не хватает системной библиотеки, а соседний сервис занял порт. Образ упаковывает приложение вместе с зависимостями и настройками, и контейнер из него запускается одинаково на ноутбуке, в CI и на сервере.

## Содержание

- [Установка Docker на сервер Ubuntu](install.md)
- [Docker Compose на практике](compose.md) — проверки здоровья, имена сервисов, `.env`, override для разработки, масштабирование

## Минимальный пример

Скрипт «Задачника» упаковывается в образ и запускается в контейнере. В папке два файла: `app.py` и `Dockerfile`.

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY app.py .
CMD ["python", "app.py"]
```

```bash
echo 'print("задачник запущен")' > app.py
docker build -t tasker:0.1 .
# ... (шаги сборки сокращены)
# => [1/3] FROM docker.io/library/python:3.12-slim
# => [2/3] WORKDIR /app
# => [3/3] COPY app.py .
# => naming to docker.io/library/tasker:0.1

docker run --rm tasker:0.1
# задачник запущен

docker images tasker
# REPOSITORY   TAG   IMAGE ID       CREATED          SIZE
# tasker       0.1   3f2a1c9d8e7b   10 seconds ago   130MB
```

Флаг `--rm` удаляет контейнер после завершения, образ остаётся и запускается повторно без сборки.

## Как это работает

Образ — это набор слоёв только для чтения, собранный по инструкциям из `Dockerfile`. Контейнер — процесс, запущенный из образа, со своим тонким слоем для записи. Как коробка с готовым обедом: внутри всё, что нужно, а снаружи достаточно разогреть.

### Ключевые понятия

- **Image** — шаблон контейнера (immutable). Состоит из слоёв.
- **Container** — запущенный экземпляр образа.
- **Dockerfile** — рецепт сборки образа.
- **Volume** — постоянное хранилище, переживающее перезапуск контейнера.
- **Bind mount** — пробрасывание директории хоста в контейнер.
- **Network** — изолированные сети между контейнерами.
- **Docker Compose** — оркестрация нескольких контейнеров через `docker-compose.yml`.
- **Registry** — хранилище образов (Docker Hub, GHCR, GitLab Registry).

### Основные команды

#### Образы
```sh
docker pull nginx:1.27               # скачать образ
docker images                        # список локальных образов
docker rmi <image>                   # удалить образ
docker build -t myapp:1.0 .          # собрать образ из Dockerfile в текущей папке
docker image prune                   # удалить «висящие» образы
```

#### Контейнеры
```sh
docker run -d --name web -p 8080:80 nginx        # запустить в фоне
docker ps                                         # список запущенных
docker ps -a                                      # все, включая остановленные
docker logs -f web                                # смотреть логи
docker exec -it web bash                          # зайти в контейнер
docker stop web && docker rm web                  # остановить и удалить
docker container prune                            # удалить все остановленные
```

#### Тома и сети
```sh
docker volume create pgdata
docker volume ls
docker volume rm pgdata

docker network create app_net
docker network ls
```

#### Очистка
```sh
docker system df          # сколько занято места
docker system prune -a    # снести всё неиспользуемое (осторожно)
```

### Пример Dockerfile (Python-приложение)

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

#### Multi-stage build (тоньше итоговый образ)

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

### Пример docker-compose.yml

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

### Лучшие практики

- Используй **`.dockerignore`** — исключай `__pycache__/`, `.git`, `node_modules/`, `*.env`.
- **Кешируй зависимости отдельным слоем** — сначала `COPY requirements.txt && pip install`, потом `COPY .`.
- Тэги **`:latest`** — зло в проде. Фиксируй версии.
- Не запускай контейнер от root — добавь `USER appuser`.
- **Multi-stage builds** уменьшают размер образа в 2–10 раз.
- Один контейнер = один процесс. Для нескольких сервисов — compose.
- Используй **healthcheck** для зависимостей.

### Как Docker устроен внутри

Контейнер — не виртуальная машина. У него нет своего ядра: это обычный процесс на ядре Linux хоста, которому ядро показывает урезанный мир и ограничивает ресурсы. Это делают три механизма ядра.

**Пространства имён (namespaces)** определяют, *что процесс видит*. Отдельное пространство имён есть у процессов (PID), сети, точек монтирования, имени хоста (UTS), пользователей и IPC. Поэтому внутри контейнера процесс считает себя первым и единственным:

```bash
docker run --rm alpine:3.20 ps
# PID   USER     TIME  COMMAND
#     1 root      0:00 ps

docker run --rm alpine:3.20 hostname
# 71020f3f61ad — своё имя хоста, по умолчанию это короткий id контейнера
```

**Контрольные группы (cgroups)** определяют, *сколько процесс может потребить*: память, процессор, ввод-вывод, число процессов. Флаги `docker run` просто записывают лимиты в cgroup:

```bash
docker run --rm --memory 64m alpine:3.20 cat /sys/fs/cgroup/memory.max
# 67108864

docker run --rm --cpus 0.5 alpine:3.20 cat /sys/fs/cgroup/cpu.max
# 50000 100000 — 50 мс процессорного времени из каждых 100 мс

docker run --rm --memory 32m python:3.12-alpine python -c 'b = bytearray(100 * 1024 * 1024)'
echo $?
# 137 — процесс убит по нехватке памяти (OOM killer): 128 + сигнал 9
```

**Слоёная файловая система (union filesystem, в Docker это overlay2)** собирает файловую систему контейнера из слоёв образа. Слои доступны только на чтение и общие для всех контейнеров из одного образа. Сверху каждый контейнер получает свой тонкий слой для записи. Изменение файла из образа копирует его в верхний слой (copy-on-write), удаление оставляет пометку. `docker diff` показывает именно верхний слой:

```bash
docker run --name demo alpine:3.20 sh -c 'echo hi > /tmp/note.txt && rm /etc/motd'
docker diff demo
# C /tmp
# A /tmp/note.txt
# C /etc
# D /etc/motd
```

Отсюда несколько практических следствий:

- контейнер стартует за доли секунды: не нужно загружать ОС, нужно только запустить процесс;
- запись в контейнер пропадает вместе с ним, поэтому данные базы хранят в томе;
- десять контейнеров из одного образа не занимают на диске в десять раз больше места;
- каждая инструкция `RUN`, `COPY`, `ADD` в Dockerfile создаёт слой (`docker image history` их показывает), поэтому удалённый в следующей инструкции файл всё равно остаётся в образе;
- `root` в контейнере по умолчанию тот же `root`, что на хосте, только в изоляции. Если изоляцию пробить (уязвимость, смонтированный `docker.sock`, `--privileged`), это права администратора хоста. Поэтому — `USER` в Dockerfile.

На macOS и Windows этих механизмов нет, поэтому Docker Desktop запускает лёгкую виртуальную машину с Linux, и контейнеры работают внутри неё.

Остальные части: **dockerd** — демон, который управляет образами, контейнерами, сетями и томами. **docker** (CLI) — клиент, который отправляет демону команды через REST API. **Registry** (Docker Hub или свой) — хранилище образов.

## Частые ошибки

- `COPY . .` стоит перед установкой зависимостей → любое изменение кода сбрасывает кеш, и `pip install` выполняется заново на каждой сборке → сначала копировать `requirements.txt` и ставить зависимости, потом код.
- Нет `.dockerignore` → в образ попадают `.git`, `.venv`, `__pycache__`, а с ними секреты из `.env`; сборка долгая, образ раздутый → добавить `.dockerignore` и проверить `docker image history`.
- Данные базы лежат в контейнере → после `docker rm` или пересоздания контейнера база пустая → подключить том (`-v pgdata:/var/lib/postgresql/data`).
- Сервер слушает `127.0.0.1` внутри контейнера → снаружи порт проброшен, но соединение отклоняется → слушать `0.0.0.0`.
- Контейнер сразу завершается после `docker run -d` → главный процесс отработал или упал, видно по `docker ps -a` и `docker logs` → запускать сервер в foreground-режиме и смотреть логи, а не «добавлять `sleep infinity`».
- Образ с тегом `:latest` в проде → после `docker pull` поднялась другая версия, и поведение изменилось без правок в коде → фиксировать версии образов.
- Процесс в контейнере работает от root → при побеге из контейнера это root на хосте → добавить пользователя и `USER appuser`.

## Когда не использовать

Для одного скрипта на своей машине Docker лишний: достаточно виртуального окружения через [uv](../uv/README.md) или [Poetry](../poetry/README.md). Утилиты командной строки удобнее ставить через [pipx](../pipx/README.md), чем заворачивать в образ.

Контейнер не заменит виртуальную машину, когда нужно другое ядро, своя ОС или жёсткая изоляция между недоверенными арендаторами: контейнеры делят ядро хоста. Для тяжёлых десктопных приложений с графикой Docker тоже не подходит.

Запуск нескольких контейнеров одной командой — это уже [Docker Compose](compose.md), а оркестрация на нескольких серверах с автоматическим перезапуском и масштабированием — [Kubernetes](../../cicd/kubernetes/README.md).

## Что спрашивают на собеседовании

- В чём разница между **image** и **container**?
- В чём разница между **volume** и **bind mount**?
- Что такое **layer** и как работает **кеш слоёв**?
- Чем отличается **`CMD`** от **`ENTRYPOINT`**? *(ENTRYPOINT — программа, CMD — её аргументы.)*
- Чем **`COPY`** отличается от **`ADD`**? *(ADD умеет распаковывать архивы и качать по URL — но обычно лучше COPY.)*
- Что такое **multi-stage build** и зачем он нужен?
- Как контейнеры общаются между собой? *(По имени сервиса внутри одной docker-сети.)*
- Чем контейнер отличается от виртуальной машины? *(Общее ядро хоста; изоляция через namespaces, лимиты через cgroups, файловая система из слоёв.)*
- Почему код 137? *(Процесс убит сигналом 9, чаще всего по лимиту памяти.)*

## Связанные темы

- [Установка Docker на сервер Ubuntu](install.md)
- [Docker Compose на практике](compose.md)
- [Git](../git/README.md)
- [uv](../uv/README.md)
- [Task Runners](../task_runners/README.md)
