-- Одна и та же колонка времени и статуса с разными кодеками.
-- docker run -d --name kb-storage-ch -p 48123:8123 clickhouse/clickhouse-server:26.3.62.3
-- docker exec -i kb-storage-ch clickhouse-client --multiquery < clickhouse_codecs.sql
-- docker rm -fv kb-storage-ch    # -v удаляет и анонимный том с данными

DROP TABLE IF EXISTS task_events;

CREATE TABLE task_events
(
    ts_lz4          DateTime64(3),                                 -- кодек по умолчанию: LZ4
    ts_zstd         DateTime64(3) CODEC(ZSTD(3)),
    ts_delta_lz4    DateTime64(3) CODEC(Delta, LZ4),
    ts_delta_zstd   DateTime64(3) CODEC(Delta, ZSTD(3)),
    ts_ddelta_zstd  DateTime64(3) CODEC(DoubleDelta, ZSTD(3)),
    status_string   String,
    status_lowcard  LowCardinality(String),
    status_zstd     LowCardinality(String) CODEC(ZSTD(3))
)
ENGINE = MergeTree
ORDER BY tuple();

-- 1 000 000 событий: шаг между событиями 0–200 мс, как в column_compression.py
INSERT INTO task_events
WITH
    toDateTime64('2026-10-29 00:00:00', 3) + toIntervalMillisecond(
        sum(rand(1) % 201) OVER (ORDER BY number ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
    ) AS ts,
    ['new', 'in_progress', 'review', 'done', 'cancelled'][1 + multiIf(
        rand(2) % 100 < 30, 0, rand(2) % 100 < 55, 1, rand(2) % 100 < 65, 2, rand(2) % 100 < 95, 3, 4)] AS status
SELECT ts, ts, ts, ts, ts, status, status, status
FROM numbers(1000000);

OPTIMIZE TABLE task_events FINAL;

SELECT
    name,
    type,
    compression_codec AS codec,
    formatReadableSize(data_uncompressed_bytes) AS raw,
    formatReadableSize(data_compressed_bytes) AS compressed,
    round(data_uncompressed_bytes / data_compressed_bytes, 1) AS ratio
FROM system.columns
WHERE database = currentDatabase() AND table = 'task_events'
FORMAT PrettyCompactMonoBlock;

-- Те же статусы, но таблица отсортирована по статусу: одинаковые значения идут подряд
DROP TABLE IF EXISTS task_events_by_status;
CREATE TABLE task_events_by_status ENGINE = MergeTree ORDER BY status_lowcard
AS SELECT status_string, status_lowcard FROM task_events;
OPTIMIZE TABLE task_events_by_status FINAL;

SELECT name, formatReadableSize(data_compressed_bytes) AS compressed
FROM system.columns
WHERE database = currentDatabase() AND table = 'task_events_by_status'
FORMAT PrettyCompactMonoBlock;
