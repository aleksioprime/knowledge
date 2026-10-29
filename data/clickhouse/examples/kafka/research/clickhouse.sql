DROP TABLE IF EXISTS ugc.events_bench;
CREATE TABLE ugc.events_bench
(
    event_id   UUID,
    event_type LowCardinality(String),
    user_id    UInt64,
    task_id    UInt64,
    rating     Nullable(UInt8),
    event_time DateTime64(3, 'UTC')
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(event_time)
ORDER BY (event_type, event_time, task_id);
