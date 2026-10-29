"""Генерирует журнал событий задач и справочник задач в CSV.

python generate_events.py /data 3000000
"""

import csv
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

out = Path(sys.argv[1] if len(sys.argv) > 1 else 'data')
rows = int(sys.argv[2]) if len(sys.argv) > 2 else 3_000_000
tasks_count = rows // 20

random.seed(42)
out.mkdir(parents=True, exist_ok=True)

projects = ['backend', 'frontend', 'mobile', 'infra', 'design']
with (out / 'tasks.csv').open('w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['task_id', 'project', 'priority'])
    for task_id in range(1, tasks_count + 1):
        writer.writerow([task_id, random.choice(projects), random.choices([1, 2, 3], weights=[2, 5, 3])[0]])

event_types = ['created', 'assigned', 'status_changed', 'commented', 'rated', 'closed']
weights = [5, 5, 40, 30, 15, 5]
start = datetime(2026, 1, 1)
with (out / 'events.csv').open('w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['event_id', 'task_id', 'user_id', 'event_type', 'ts', 'duration_ms'])
    for event_id in range(1, rows + 1):
        ts = start + timedelta(seconds=event_id * 300 * 24 * 3600 // rows + random.randint(0, 59))
        writer.writerow([
            event_id,
            random.randint(1, tasks_count),
            random.randint(1, 5_000),
            random.choices(event_types, weights)[0],
            ts.isoformat(sep=' '),
            int(random.expovariate(1 / 800)),
        ])

print(f'{rows:,} событий, {tasks_count:,} задач → {out}')
