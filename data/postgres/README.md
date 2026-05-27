# PostgreSQL

**PostgreSQL** — мощная объектно-реляционная СУБД с открытым исходным кодом. Поддерживает ACID-транзакции, расширения (PostGIS, pg_trgm, pgvector), JSON/JSONB, оконные функции, CTE, partitioning и репликацию.

## Установка и запуск

Через `docker run`:
```sh
docker run --name postgres \
  --platform linux/arm64 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=test_db \
  -p 5432:5432 \
  -v postgres_data:/var/lib/postgresql/data \
  -d postgres:16
```

Через `docker-compose`:
```yaml
services:
  postgres:
    image: postgres:16
    container_name: postgres
    platform: linux/amd64
    restart: unless-stopped
    environment:
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: 1q2w3e
      POSTGRES_DB: database
      TZ: Europe/Moscow
      PGTZ: Europe/Moscow
    volumes:
      - postgres_volume:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U admin -d database"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_volume:
```

## Содержание

- [Подключение к БД](docs/connect.ipynb)
- [Запросы (SELECT, JOIN, агрегации)](docs/query.ipynb)
- [Транзакции и уровни изоляции](docs/transaction.ipynb)
- [Дополнительные возможности](docs/extra.ipynb)
- [Практические задачи](docs/tasks.ipynb)
