#!/usr/bin/env bash
# Сравнение ClickHouse и PostgreSQL на 10 млн событий.
# Запуск из папки примера: bash research/bench.sh
set -euo pipefail

dc() { docker compose -p kb-ugc "$@"; }
ch() { dc exec -T clickhouse clickhouse-client --user ugc --password ugc "$@"; }
pg() { dc exec -T postgres psql -U ugc -d ugc -v ON_ERROR_STOP=1 "$@"; }
now() { python3 -c 'import time; print(time.time())'; }
since() { python3 -c "import sys, time; print(f'{time.time() - float(sys.argv[1]):.1f} с')" "$1"; }

echo '== Генерация CSV'
ch --queries-file /scripts/generate.sql
dc exec -T clickhouse ls -lh /research/events.csv

echo '== ClickHouse: загрузка'
ch --queries-file /scripts/clickhouse.sql
start=$(now)
dc exec -T clickhouse bash -c 'clickhouse-client --user ugc --password ugc --query "INSERT INTO ugc.events_bench FORMAT CSV" < /research/events.csv'
echo "загрузка: $(since "$start")"
ch --query "SELECT sum(rows) AS rows, count() AS parts, formatReadableSize(sum(bytes_on_disk)) AS on_disk,
            formatReadableSize(sum(data_uncompressed_bytes)) AS uncompressed
            FROM system.parts WHERE database = 'ugc' AND table = 'events_bench' AND active" --format PrettyCompact

echo '== PostgreSQL: загрузка'
pg -f /scripts/postgres.sql
start=$(now)
pg -c "COPY events_bench FROM '/research/events.csv' WITH (FORMAT csv, NULL '\\N')"
echo "COPY: $(since "$start")"
start=$(now)
pg -f /scripts/postgres_indexes.sql
echo "индексы и VACUUM ANALYZE: $(since "$start")"
pg -c "SELECT pg_size_pretty(pg_relation_size('events_bench')) AS table,
              pg_size_pretty(pg_indexes_size('events_bench')) AS indexes,
              pg_size_pretty(pg_total_relation_size('events_bench')) AS total"

echo '== Запросы: по три прогона, время в секундах'
for q in 1 2 3; do
  ch_sql=$(awk -v n="-- Q$q:" 'index($0, n) == 1 {f = 1; next} /^-- Q/ {f = 0} f' research/queries_clickhouse.sql)
  pg_sql=$(awk -v n="-- Q$q:" 'index($0, n) == 1 {f = 1; next} /^-- Q/ {f = 0} f' research/queries_postgres.sql)
  for run in 1 2 3; do
    ch_time=$(ch --time --format Null --query "$ch_sql" 2>&1)
    pg_time=$(pg -c '\timing on' -c "$pg_sql" | awk '/^Time:/ {printf "%.3f", $2 / 1000}')
    echo "Q$q прогон $run: ClickHouse $ch_time, PostgreSQL $pg_time"
  done
done
