"""Загружает оценки задач в шардированный кластер.

ratings         — ключ {task_id: 'hashed'}: записи равномерно расходятся по шардам
ratings_by_time — ключ {created_at: 1}: все новые записи попадают в один «горячий» шард

uv run --with-requirements requirements.txt python load.py [количество]
"""

import random
import sys
import time
from datetime import UTC, datetime, timedelta

from pymongo import MongoClient

TOTAL = int(sys.argv[1]) if len(sys.argv) > 1 else 200_000
BATCH = 5_000

client = MongoClient('mongodb://localhost:37017')
admin = client.admin
db = client.tasker

for name in ('ratings', 'ratings_by_time'):
    db.drop_collection(name)

admin.command('enableSharding', 'tasker')
admin.command('shardCollection', 'tasker.ratings', key={'task_id': 'hashed'})
admin.command('shardCollection', 'tasker.ratings_by_time', key={'created_at': 1})

# Делим диапазон времени на «прошлое» и «будущее» и отдаём будущее второму шарду.
# Так нагляднее: всё, что пишется сейчас, попадает в чанк с верхней границей MaxKey.
now = datetime.now(UTC).replace(microsecond=0)
admin.command('split', 'tasker.ratings_by_time', middle={'created_at': now})
admin.command('moveChunk', 'tasker.ratings_by_time', find={'created_at': now}, to='rs2')
admin.command('moveChunk', 'tasker.ratings_by_time', find={'created_at': now - timedelta(days=1)}, to='rs1')
# Выключаем балансировщик для этой коллекции, чтобы перекос было видно (sh.disableBalancing)
client.config.collections.update_one({'_id': 'tasker.ratings_by_time'}, {'$set': {'noBalance': True}})

random.seed(42)
started = time.perf_counter()
for offset in range(0, TOTAL, BATCH):
    batch = [
        {
            'task_id': random.randint(1, 20_000),
            'user_id': random.randint(1, 50_000),
            'score': random.randint(1, 5),
            'created_at': now + timedelta(milliseconds=10 * (offset + i)),
        }
        for i in range(min(BATCH, TOTAL - offset))
    ]
    db.ratings.insert_many(batch, ordered=False)
    for doc in batch:
        doc.pop('_id')
    db.ratings_by_time.insert_many(batch, ordered=False)

elapsed = time.perf_counter() - started
print(f'вставлено {TOTAL} × 2 документов за {elapsed:.1f} с')
