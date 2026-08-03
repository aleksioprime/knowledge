# Локальный ClickHouse-кластер

Пример поднимает ClickHouse-кластер в Docker:

- 4 сервера ClickHouse (отдельные ноды, каждая запускает свой процесс ClickHouse)
- 2 шарда (части кластера, между которыми распределяются данные)
- 2 реплики в каждом шарде (копии одного шарда для отказоустойчивости)
- ZooKeeper для репликации (координатор, который помогает нодам синхронизировать реплики)
- отдельный Python-контейнер для запросов через `clickhouse-driver`

## Конфигурация

ClickHouse-ноды:

| Сервис | HTTP на хосте | TCP на хосте | Внутри Docker | Роль |
|---|---:|---:|---|---|
| `clickhouse-node1` | `18123` | `19000` | `8123` / `9000` | shard 1, replica 1 |
| `clickhouse-node2` | `18124` | `19001` | `8123` / `9000` | shard 1, replica 2 |
| `clickhouse-node3` | `18125` | `19002` | `8123` / `9000` | shard 2, replica 1 |
| `clickhouse-node4` | `18126` | `19003` | `8123` / `9000` | shard 2, replica 2 |

ZooKeeper:

- сервис: `zookeeper`
- внутренний порт: `2181`

Клиент:

- сервис: `python-client`
- внутри уже установлен `clickhouse-driver`

Внутри Docker-сети сервисы доступны по именам `clickhouse-node1`, `clickhouse-node2`, `clickhouse-node3`, `clickhouse-node4`. Из Python-контейнера нельзя подключаться к ClickHouse через `localhost`, потому что `localhost` будет указывать на сам Python-контейнер.

В Python-контейнере используйте внутренний порт `9000`: `Client(host='clickhouse-node1', port=9000)`.
С хост-машины первая нода доступна на `localhost:19000` по TCP и `localhost:18123` по HTTP.

## Запуск

Перейти в папку проекта:

```sh
cd /Users/aleksioprime/edu/knowledge/data/clickhouse/examples/nodes
```

Запустить кластер вместе с Python-клиентом:

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

Подключиться к первой ноде:

```python
from clickhouse_driver import Client

client = Client(host='clickhouse-node1', port=9000)
client.execute('SELECT 1')
```

Проверить список баз данных:

```python
client.execute('SHOW DATABASES')
```

## Обычная таблица на кластере

Создать базу данных на всех нодах:

```python
client.execute('CREATE DATABASE IF NOT EXISTS example ON CLUSTER company_cluster')
```

Создать таблицу на всех нодах:

```python
client.execute("""
CREATE TABLE IF NOT EXISTS example.regular_table ON CLUSTER company_cluster
(
    id Int64,
    x Int32
)
ENGINE = MergeTree()
ORDER BY id
""")
```

Вставить данные:

```python
client.execute('INSERT INTO example.regular_table (id, x) VALUES', [(1, 10), (2, 20)])
```

Прочитать данные:

```python
client.execute('SELECT * FROM example.regular_table ORDER BY id')
```

## Реплицированная таблица

Для примера с `ReplicatedMergeTree` нужно подготовить локальные таблицы на каждой ноде.
Здесь удобнее использовать `clickhouse-client` внутри ClickHouse-контейнеров.

### Шард 1, реплика 1

```sh
docker compose exec clickhouse-node1 clickhouse-client
```

```sql
CREATE DATABASE IF NOT EXISTS shard;

CREATE TABLE IF NOT EXISTS shard.test
(
    id Int64,
    event_time DateTime
)
ENGINE = ReplicatedMergeTree('/clickhouse/tables/shard1/test', 'replica_1')
PARTITION BY toYYYYMMDD(event_time)
ORDER BY id;

CREATE TABLE IF NOT EXISTS default.test
(
    id Int64,
    event_time DateTime
)
ENGINE = Distributed('company_cluster', '', test, rand());
```

### Шард 1, реплика 2

```sh
docker compose exec clickhouse-node2 clickhouse-client
```

```sql
CREATE DATABASE IF NOT EXISTS replica;

CREATE TABLE IF NOT EXISTS replica.test
(
    id Int64,
    event_time DateTime
)
ENGINE = ReplicatedMergeTree('/clickhouse/tables/shard1/test', 'replica_2')
PARTITION BY toYYYYMMDD(event_time)
ORDER BY id;
```

### Шард 2, реплика 1

```sh
docker compose exec clickhouse-node3 clickhouse-client
```

```sql
CREATE DATABASE IF NOT EXISTS shard;

CREATE TABLE IF NOT EXISTS shard.test
(
    id Int64,
    event_time DateTime
)
ENGINE = ReplicatedMergeTree('/clickhouse/tables/shard2/test', 'replica_1')
PARTITION BY toYYYYMMDD(event_time)
ORDER BY id;

CREATE TABLE IF NOT EXISTS default.test
(
    id Int64,
    event_time DateTime
)
ENGINE = Distributed('company_cluster', '', test, rand());
```

### Шард 2, реплика 2

```sh
docker compose exec clickhouse-node4 clickhouse-client
```

```sql
CREATE DATABASE IF NOT EXISTS replica;

CREATE TABLE IF NOT EXISTS replica.test
(
    id Int64,
    event_time DateTime
)
ENGINE = ReplicatedMergeTree('/clickhouse/tables/shard2/test', 'replica_2')
PARTITION BY toYYYYMMDD(event_time)
ORDER BY id;
```

## Запросы к Distributed-таблице из Python

Открыть Python shell:

```sh
docker compose exec python-client python
```

Вставить данные:

```python
from clickhouse_driver import Client

client = Client(host='clickhouse-node1', port=9000)

client.execute(
    'INSERT INTO default.test (id, event_time) VALUES',
    [(1, '2026-01-01 10:00:00'), (2, '2026-01-01 11:00:00'), (3, '2026-01-01 12:00:00')],
)
```

Прочитать данные:

```python
client.execute('SELECT * FROM default.test ORDER BY id')
```

Проверить, на какие ноды попали строки:

```python
client.execute("""
SELECT
    hostName(),
    count()
FROM cluster('company_cluster', system.one)
GROUP BY hostName()
ORDER BY hostName()
""")
```

Если запрос падает с `Database shard does not exist` или `Database replica does not exist`, значит локальные базы `shard` и `replica` ещё не созданы на соответствующих нодах.

## Остановка

Остановить контейнеры:

```sh
docker compose down
```
