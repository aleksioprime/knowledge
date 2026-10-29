# Простой ClickHouse

Пример поднимает один сервер ClickHouse и отдельный Python-контейнер для тестовых запросов через `clickhouse-driver`.

## Конфигурация

Сервисы:

| Сервис | Назначение |
|---|---|
| `clickhouse` | один сервер ClickHouse |
| `python-client` | Python shell с установленным `clickhouse-driver` |

Порты ClickHouse:

| Интерфейс | На хосте | Внутри Docker |
|---|---:|---:|
| HTTP | `18223` | `8123` |
| Native TCP | `19100` | `9000` |

Пользователь:

- база данных: `analytics`
- пользователь: `developer`
- пароль: `demo_password`

Данные ClickHouse сохраняются в Docker volume `clickhouse_data`.

## Запуск

Перейти в папку примера:

```sh
cd docs/backend/databases/clickhouse/examples/simple
```

Запустить ClickHouse и Python-клиент:

```sh
docker compose up -d --build
```

Проверить контейнеры:

```sh
docker compose ps
```

## Python shell

Открыть Python shell:

```sh
docker compose exec python-client python
```

Подключиться к ClickHouse:

```python
from clickhouse_driver import Client

client = Client(
    host='clickhouse',
    port=9000,
    user='developer',
    password='demo_password',
    database='analytics',
)
```

Проверить подключение:

```python
client.execute('SELECT 1')
```

Создать таблицу:

```python
client.execute("""
CREATE TABLE IF NOT EXISTS events
(
    id UInt64,
    name String,
    created_at DateTime
)
ENGINE = MergeTree()
ORDER BY id
""")
```

Добавить данные:

```python
client.execute(
    'INSERT INTO events (id, name, created_at) VALUES',
    [(1, 'open', '2026-01-01 10:00:00'), (2, 'click', '2026-01-01 10:01:00')],
)
```

Прочитать данные:

```python
client.execute('SELECT * FROM events ORDER BY id')
```

## Подключение с хост-машины

Если Python запущен не в Docker, а на хосте, используйте внешний TCP-порт:

```python
from clickhouse_driver import Client

client = Client(
    host='localhost',
    port=19100,
    user='developer',
    password='demo_password',
    database='analytics',
)
```

## Остановка

Остановить контейнеры:

```sh
docker compose down
```

Остановить контейнеры и удалить данные:

```sh
docker compose down -v
```
