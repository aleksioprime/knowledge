ALTER TABLE events_bench ADD PRIMARY KEY (event_id);
CREATE INDEX ON events_bench (event_type, event_time);
VACUUM ANALYZE events_bench;
