DROP TABLE IF EXISTS events_bench;
CREATE TABLE events_bench
(
    event_id   uuid,
    event_type text        NOT NULL,
    user_id    bigint      NOT NULL,
    task_id    bigint      NOT NULL,
    rating     smallint,
    event_time timestamptz NOT NULL
);
