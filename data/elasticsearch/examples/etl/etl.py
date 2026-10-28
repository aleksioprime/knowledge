"""ETL: задачи из PostgreSQL → индекс tasks в Elasticsearch.

Запуск: python etl.py (бесконечный цикл) или python etl.py --once (один проход).
"""
import json
import logging
import os
import random
import sys
import time
from datetime import datetime
from functools import wraps
from pathlib import Path

import psycopg
from elasticsearch import ConnectionError as ESConnectionError
from elasticsearch import Elasticsearch, helpers
from psycopg.rows import dict_row

PG_DSN = os.environ.get('PG_DSN', 'postgresql://app:app@localhost:15432/tasks')
ES_URL = os.environ.get('ES_URL', 'http://localhost:19200')
STATE_FILE = Path(os.environ.get('STATE_FILE', 'state.json'))
BATCH_SIZE = int(os.environ.get('BATCH_SIZE', '100'))
SLEEP_SECONDS = float(os.environ.get('SLEEP_SECONDS', '10'))
LOCK_ID = 42  # любое число, одинаковое у всех копий ETL

INDEX = 'tasks'
MAPPING = {
    'properties': {
        'title': {'type': 'text', 'analyzer': 'russian'},
        'description': {'type': 'text', 'analyzer': 'russian'},
        'done': {'type': 'boolean'},
        'owner': {'type': 'keyword'},
        'tags': {'type': 'keyword'},
        'modified': {'type': 'date'},
    },
}

logger = logging.getLogger('etl')


def backoff(exceptions, start_sleep=0.1, factor=2, border_sleep=10):
    """Повторяет вызов при ошибках из exceptions: пауза растёт до border_sleep, со случайным разбросом."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as error:
                    delay = random.uniform(0, min(border_sleep, start_sleep * factor ** attempt))
                    logger.warning('%s: %r, повтор через %.1f с', func.__name__, error, delay)
                    time.sleep(delay)
                    attempt += 1
        return wrapper
    return decorator


class JsonFileStorage:
    def __init__(self, path: Path):
        self.path = path

    def retrieve_state(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text())

    def save_state(self, state: dict) -> None:
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(state, ensure_ascii=False))
        tmp.replace(self.path)  # атомарная замена: при падении не останется полузаписанного файла


class State:
    def __init__(self, storage: JsonFileStorage):
        self.storage = storage
        self.state = storage.retrieve_state()

    def get_state(self, key: str, default=None):
        return self.state.get(key, default)

    def set_state(self, key: str, value) -> None:
        self.state[key] = value
        self.storage.save_state(self.state)


# Курсор — пара (modified, id): записи с одинаковым modified не потеряются на границе пачки
CHANGED = """
    SELECT id, modified FROM content.{table}
    WHERE (modified, id) > (%(modified)s, %(id)s)
    ORDER BY modified, id
    LIMIT %(limit)s
"""

ENRICH = """
    SELECT
        t.id, t.title, t.description, t.done, t.owner, t.modified,
        COALESCE(array_agg(g.name ORDER BY g.name) FILTER (WHERE g.id IS NOT NULL), '{}') AS tags
    FROM content.task AS t
    LEFT JOIN content.task_tag AS tt ON tt.task_id = t.id
    LEFT JOIN content.tag AS g ON g.id = tt.tag_id
    WHERE t.id = ANY(%s)
    GROUP BY t.id
"""

START = {'modified': datetime.min.isoformat() + '+00:00', 'id': '00000000-0000-0000-0000-000000000000'}


def transform(row: dict) -> dict:
    return {
        '_index': INDEX,
        '_id': str(row['id']),
        '_source': {
            'title': row['title'],
            'description': row['description'],
            'done': row['done'],
            'owner': row['owner'],
            'tags': row['tags'],
            'modified': row['modified'].isoformat(),
        },
    }


def load(es: Elasticsearch, docs: list[dict]) -> None:
    ok, errors = helpers.bulk(es, docs, raise_on_error=False)
    for error in errors:
        logger.error('Документ не загружен: %s', error)  # ошибка в данных: повтор не поможет
    logger.info('Загружено документов: %s', ok)


@backoff((psycopg.OperationalError, ESConnectionError))
def run_once(state: State) -> None:
    es = Elasticsearch(ES_URL, request_timeout=10)
    if not es.indices.exists(index=INDEX):
        es.indices.create(index=INDEX, mappings=MAPPING)

    with psycopg.connect(PG_DSN, row_factory=dict_row, connect_timeout=5) as conn:
        # Вторая копия ETL (например, наложившийся запуск cron) не возьмёт блокировку и выйдет
        if not conn.execute('SELECT pg_try_advisory_lock(%s) AS ok', (LOCK_ID,)).fetchone()['ok']:
            logger.warning('ETL уже запущен в другом процессе')
            return

        for table in ('task', 'tag'):
            while True:
                cursor = state.get_state(table, START)
                rows = conn.execute(CHANGED.format(table=table), {**cursor, 'limit': BATCH_SIZE}).fetchall()
                if not rows:
                    break
                ids = [row['id'] for row in rows]
                if table == 'tag':  # переименовали метку — переиндексировать все задачи с ней
                    ids = [r['task_id'] for r in conn.execute(
                        'SELECT DISTINCT task_id FROM content.task_tag WHERE tag_id = ANY(%s)', (ids,))]
                for start in range(0, len(ids), BATCH_SIZE):  # у одной метки могут быть тысячи задач
                    chunk = ids[start:start + BATCH_SIZE]
                    load(es, [transform(row) for row in conn.execute(ENRICH, (chunk,))])
                last = rows[-1]
                # Состояние сохраняем только после успешной загрузки пачки
                state.set_state(table, {'modified': last['modified'].isoformat(), 'id': str(last['id'])})


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    logging.getLogger('elastic_transport').setLevel(logging.WARNING)
    state = State(JsonFileStorage(STATE_FILE))
    while True:
        run_once(state)
        if '--once' in sys.argv:
            break
        time.sleep(SLEEP_SECONDS)


if __name__ == '__main__':
    main()
