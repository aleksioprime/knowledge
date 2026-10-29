import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

TASKS_MAPPING = json.loads((Path(__file__).parent / 'tasks_mapping.json').read_text())

START = datetime(2026, 10, 1, tzinfo=timezone.utc)


def make_task(number: int, **fields) -> dict:
    """Документ задачи в том виде, в каком его кладёт в индекс ETL; id — отдельно, как _id."""
    task = {
        'id': str(uuid.uuid4()),
        'title': f'Задача №{number}',
        'description': None,
        'done': False,
        'owner': 'anna',
        'tags': [],
        'modified': (START + timedelta(hours=number)).isoformat(),
    }
    task.update(fields)
    return task
