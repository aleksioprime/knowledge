-- 10 млн событий за октябрь 2026: 100 тыс. пользователей, 200 тыс. задач, часть задач популярнее других
SELECT
    generateUUIDv4(number) AS event_id,
    ['task.viewed', 'task.viewed', 'task.viewed', 'task.viewed', 'task.viewed', 'task.viewed',
     'task.created', 'task.done', 'task.rated'][1 + rand(1) % 9] AS event_type,
    1 + rand(2) % 100000 AS user_id,
    if(rand(3) % 2 = 0, 1 + toUInt64(pow(rand(4) / 4294967296.0, 3) * 200000), 1 + rand(5) % 200000) AS task_id,
    if(event_type = 'task.rated', 1 + rand(6) % 5, NULL) AS rating,
    toDateTime64('2026-10-01 00:00:00', 3, 'UTC') + toIntervalMillisecond(rand64(7) % (31 * 86400000)) AS event_time
FROM numbers(10000000)
INTO OUTFILE '/research/events.csv' TRUNCATE
FORMAT CSV
