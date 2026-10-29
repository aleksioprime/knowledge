"""Те же отчёты, что в task_stats.py, но в DuckDB на одной машине — для сравнения.

uv run --with duckdb==1.5.6 python duckdb_stats.py data /tmp/out
"""

import sys
import time
from pathlib import Path

import duckdb

data = sys.argv[1] if len(sys.argv) > 1 else 'data'
out = Path(sys.argv[2] if len(sys.argv) > 2 else data)
out.mkdir(parents=True, exist_ok=True)
con = duckdb.connect(config={'threads': 2})  # как local[2] у Spark
print('DuckDB', duckdb.__version__)

for title, sql in [
    ('count() по CSV    ', f"SELECT count(*) FROM '{data}/events.csv' WHERE event_type = 'closed'"),
    ('запись Parquet    ', f"COPY '{data}/events.csv' TO '{out}/events.parquet' (FORMAT parquet)"),
    ('агрегат по CSV    ', f"SELECT event_type, avg(duration_ms) FROM '{data}/events.csv' GROUP BY 1"),
    ('агрегат по Parquet', f"SELECT event_type, avg(duration_ms) FROM '{out}/events.parquet' GROUP BY 1"),
    ('join + group by   ', f"""
        SELECT t.project, date_trunc('month', e.ts) AS month, count(*) AS events, count(DISTINCT e.user_id) AS users
        FROM '{out}/events.parquet' e JOIN '{data}/tasks.csv' t USING (task_id)
        GROUP BY ALL ORDER BY month, project"""),
]:
    started = time.perf_counter()
    con.sql(sql).fetchall() if sql.lstrip().startswith('SELECT') else con.execute(sql)
    print(f'{title}: {time.perf_counter() - started:.2f} с')
