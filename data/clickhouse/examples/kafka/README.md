# События «Задачника»: FastAPI → Kafka → ClickHouse

API принимает пользовательские события и пишет их в Kafka, ClickHouse читает топик движком Kafka и складывает в `MergeTree`. Объяснение — в заметке [Из Kafka в ClickHouse](../../docs/kafka.md), сравнение с PostgreSQL — в [Как выбрать аналитическое хранилище](../../docs/research.md).

| Сервис | Образ | Порт на хосте |
|---|---|---|
| `kafka` | `apache/kafka:4.1.0`, один узел KRaft, 3 партиции | `39192` |
| `clickhouse` | `clickhouse/clickhouse-server:26.3.62.3` | `38123` (HTTP) |
| `api` | `python:3.12-slim` + FastAPI 0.162, aiokafka 0.15 | `38000` |
| `postgres` | `postgres:17-alpine`, только в профиле `research` | `35432` |

Пользователь ClickHouse: `ugc` / `ugc`. Схема создаётся из [clickhouse/init.sql](clickhouse/init.sql) при первом запуске. Файл [clickhouse/low-memory.xml](clickhouse/low-memory.xml) ограничивает сервер 2 ГБ памяти (сразу после запуска он занимает около 0,9 ГБ), чтобы стенд уживался с другими контейнерами.

## Запуск

```bash
docker compose -p kb-ugc up -d --build

curl -X POST localhost:38000/events -H 'Content-Type: application/json' \
  -d '{"event_type": "task.rated", "user_id": 1, "task_id": 7, "rating": 5}'

docker compose -p kb-ugc exec clickhouse clickhouse-client --user ugc --password ugc \
  -q "SELECT * FROM ugc.events FORMAT Vertical"
```

Типы событий: `task.created`, `task.done`, `task.viewed`, `task.rated` (с полем `rating` от 1 до 5).

## Нагрузка

```bash
uv run --with httpx==0.28.1 --with clickhouse-connect==1.11.0 load.py --count 100000
```

Скрипт шлёт события в API (50 одновременных запросов) и ждёт, пока все они окажутся в `ugc.events`.

## Свой консьюмер вместо движка Kafka

```bash
uv run --with aiokafka==0.15.0 --with clickhouse-connect==1.11.0 consumer.py
```

Читает тот же топик в группе `batch-writer` и вставляет пачками в `ugc.events_batch`. Остановка — `Ctrl+C`.

## Состояние потребителей

```bash
# ClickHouse как потребитель
docker compose -p kb-ugc exec clickhouse clickhouse-client --user ugc --password ugc \
  -q "SELECT table, assignments.partition_id, assignments.current_offset, num_messages_read, exceptions.text
      FROM system.kafka_consumers FORMAT Vertical"

# Лаг групп со стороны Kafka
docker compose -p kb-ugc exec kafka /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 --describe --all-groups
```

## Сравнение с PostgreSQL

```bash
docker compose -p kb-ugc --profile research up -d
bash research/bench.sh
```

Генерирует 10 млн событий в CSV (в volume `bench_data`, не в репозиторий), загружает в обе базы и прогоняет три запроса по три раза. SQL — в папке [research](research/).

## Удаление

```bash
docker compose -p kb-ugc --profile research down -v
docker image rm kb-ugc-api:local
```
