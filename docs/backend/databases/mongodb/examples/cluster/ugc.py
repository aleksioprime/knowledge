"""Оценки, комментарии и закладки задач в шардированном кластере.

uv run --with-requirements requirements.txt python ugc.py
"""

from datetime import UTC, datetime

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING, MongoClient, ReturnDocument
from pymongo.errors import DuplicateKeyError

client = MongoClient('mongodb://localhost:37017')
admin = client.admin
db = client.ugc

for name in ('task_ratings', 'task_comments', 'bookmarks', 'tasks'):
    db.drop_collection(name)

# --- коллекции и ключи шардирования ------------------------------------------
admin.command('enableSharding', 'ugc')
admin.command('shardCollection', 'ugc.task_ratings', key={'task_id': 'hashed'})
admin.command('shardCollection', 'ugc.task_comments', key={'task_id': 'hashed', '_id': 1})
admin.command('shardCollection', 'ugc.bookmarks', key={'user_id': 'hashed'})
admin.command('shardCollection', 'ugc.tasks', key={'_id': 'hashed'})

# Один пользователь — одна оценка задачи. Ключ шардирования (task_id) — префикс индекса,
# иначе MongoDB не сможет гарантировать уникальность между шардами.
db.task_ratings.create_index([('task_id', ASCENDING), ('user_id', ASCENDING)], unique=True)
db.task_ratings.create_index([('user_id', ASCENDING), ('created_at', DESCENDING)])
db.task_comments.create_index([('task_id', ASCENDING), ('_id', DESCENDING)])
db.bookmarks.create_index([('user_id', ASCENDING), ('task_id', ASCENDING)], unique=True)

try:
    db.task_ratings.create_index('user_id', unique=True, name='bad_unique')
except Exception as error:
    print('уникальный индекс без ключа шардирования:', error.details['codeName'])

# --- оценка: upsert + денормализованный счётчик ------------------------------
db.tasks.insert_many([{'_id': task_id, 'title': f'Задача {task_id}', 'ratings_count': 0, 'ratings_sum': 0}
                      for task_id in range(1, 6)])


def rate(task_id: int, user_id: int, score: int) -> None:
    """Ставит или меняет оценку и поправляет счётчик задачи на разницу."""
    now = datetime.now(UTC)
    before = db.task_ratings.find_one_and_update(
        {'task_id': task_id, 'user_id': user_id},
        {'$set': {'score': score, 'updated_at': now}, '$setOnInsert': {'created_at': now}},
        upsert=True,
        return_document=ReturnDocument.BEFORE,
    )
    if before is None:
        db.tasks.update_one({'_id': task_id}, {'$inc': {'ratings_count': 1, 'ratings_sum': score}})
    else:
        db.tasks.update_one({'_id': task_id}, {'$inc': {'ratings_sum': score - before['score']}})


rate(1, 101, 5)
rate(1, 102, 3)
rate(1, 101, 4)  # передумал: оценка заменяется, а не добавляется
rate(2, 101, 2)

try:
    db.task_ratings.insert_one({'task_id': 1, 'user_id': 102, 'score': 1})
except DuplicateKeyError:
    print('вторая оценка того же пользователя: DuplicateKeyError')

task = db.tasks.find_one({'_id': 1})
print('счётчик в задаче:', task['ratings_count'], 'оценки, среднее', task['ratings_sum'] / task['ratings_count'])

on_the_fly = db.task_ratings.aggregate([
    {'$match': {'task_id': 1}},
    {'$group': {'_id': '$task_id', 'count': {'$sum': 1}, 'avg': {'$avg': '$score'}}},
]).next()
print('агрегат на лету:', on_the_fly)

# --- комментарии: пагинация по _id -------------------------------------------
db.task_comments.insert_many(
    [{'task_id': 1, 'author_id': 100 + i % 3, 'text': f'Комментарий {i}'} for i in range(1, 26)]
)


def comments_page(task_id: int, before_id: ObjectId | None = None, limit: int = 10) -> list[dict]:
    query = {'task_id': task_id}
    if before_id is not None:
        query['_id'] = {'$lt': before_id}
    return list(db.task_comments.find(query, {'text': 1}).sort('_id', DESCENDING).limit(limit))


page1 = comments_page(1)
page2 = comments_page(1, before_id=page1[-1]['_id'])
page3 = comments_page(1, before_id=page2[-1]['_id'])
print('страницы:', [c['text'] for c in page1][:3], '...', [c['text'] for c in page3])

plan = db.task_comments.find({'task_id': 1, '_id': {'$lt': page1[-1]['_id']}}).sort('_id', -1).limit(10).explain()
print('план страницы:', plan['queryPlanner']['winningPlan']['stage'],
      [s['shardName'] for s in plan['queryPlanner']['winningPlan']['shards']])

# --- закладки ----------------------------------------------------------------
for task_id in (3, 1, 5):
    db.bookmarks.update_one(
        {'user_id': 101, 'task_id': task_id},
        {'$setOnInsert': {'created_at': datetime.now(UTC)}},
        upsert=True,
    )
db.bookmarks.update_one({'user_id': 101, 'task_id': 3}, {'$setOnInsert': {'created_at': datetime.now(UTC)}},
                        upsert=True)  # повтор ничего не меняет
print('закладки 101:', [b['task_id'] for b in db.bookmarks.find({'user_id': 101}).sort('created_at', -1)])
db.bookmarks.delete_one({'user_id': 101, 'task_id': 1})
print('после удаления:', db.bookmarks.count_documents({'user_id': 101}))

# --- skip против курсора по _id на 50 000 комментариев -----------------------
db.task_comments.insert_many([{'task_id': 2, 'author_id': 100, 'text': f'#{i}'} for i in range(50_000)])
deep = list(db.task_comments.find({'task_id': 2}, {'_id': 1}).sort('_id', DESCENDING).skip(40_000).limit(1))[0]['_id']
for title, cursor in [
    ('skip(40000)', db.task_comments.find({'task_id': 2}).sort('_id', DESCENDING).skip(40_000).limit(10)),
    ('_id < последнего', db.task_comments.find({'task_id': 2, '_id': {'$lt': deep}}).sort('_id', DESCENDING).limit(10)),
]:
    stats = cursor.explain()['executionStats']
    print(f'{title:<18} просмотрено ключей: {stats["totalKeysExamined"]:>6}, '
          f'документов: {stats["totalDocsExamined"]:>6}, {stats["executionTimeMillis"]} мс')
