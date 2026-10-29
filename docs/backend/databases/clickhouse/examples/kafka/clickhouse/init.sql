CREATE DATABASE IF NOT EXISTS ugc;

-- Хранилище событий: сюда приходят данные и отсюда читают запросы
CREATE TABLE IF NOT EXISTS ugc.events
(
    event_id        UUID,
    event_type      LowCardinality(String),
    user_id         UInt64,
    task_id         UInt64,
    rating          Nullable(UInt8),
    event_time      DateTime64(3, 'UTC'),
    kafka_partition UInt16,
    kafka_offset    UInt64
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(event_time)
ORDER BY (event_type, event_time, task_id);

-- Подписка на топик: таблица не хранит данные, а читает их из Kafka
CREATE TABLE IF NOT EXISTS ugc.events_queue
(
    event_id   String,
    event_type String,
    user_id    UInt64,
    task_id    UInt64,
    rating     Nullable(UInt8),
    event_time String
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:9092',
    kafka_topic_list = 'task-events',
    kafka_group_name = 'clickhouse',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1,
    kafka_max_block_size = 65536,
    kafka_skip_broken_messages = 10;

-- Перекладчик: каждый прочитанный блок из очереди вставляется в events
CREATE MATERIALIZED VIEW IF NOT EXISTS ugc.events_mv TO ugc.events AS
SELECT
    toUUID(event_id) AS event_id,
    event_type,
    user_id,
    task_id,
    rating,
    parseDateTime64BestEffort(event_time, 3, 'UTC') AS event_time,
    _partition AS kafka_partition,
    _offset AS kafka_offset
FROM ugc.events_queue;

-- Таблица для второго способа: свой консьюмер пишет сюда пачками (consumer.py)
CREATE TABLE IF NOT EXISTS ugc.events_batch AS ugc.events;
