# Пользовательский контент в MongoDB

Оценки, комментарии и закладки — пользовательский контент (user-generated content, UGC). У него свой профиль нагрузки: записей много и они мелкие, читают их в основном «по задаче» или «по пользователю», строгие связи между таблицами не нужны, а объём растёт вместе с аудиторией, а не с числом задач. Такие данные часто выносят из основной реляционной базы в отдельное хранилище — например, в шардированный MongoDB. Ниже — как спроектировать схему, чтобы она выдержала рост.

Все примеры запущены на учебном кластере из заметки [Шардирование и кластер MongoDB](sharding.md): два шарда, `mongos` на `localhost:37017`. Полный код — [ugc.py](examples/cluster/ugc.py) и [ugc_async.py](examples/cluster/ugc_async.py).

## Минимальный пример

Пользователь ставит задаче оценку от 1 до 5. Повторная оценка заменяет прежнюю, а не добавляет вторую:

```python
from datetime import UTC, datetime

from pymongo import ASCENDING, MongoClient

ratings = MongoClient('mongodb://localhost:37017').ugc.task_ratings
ratings.create_index([('task_id', ASCENDING), ('user_id', ASCENDING)], unique=True)


def rate(task_id: int, user_id: int, score: int) -> None:
    now = datetime.now(UTC)
    ratings.update_one(
        {'task_id': task_id, 'user_id': user_id},
        {'$set': {'score': score, 'updated_at': now}, '$setOnInsert': {'created_at': now}},
        upsert=True,
    )


rate(1, 101, 5)
rate(1, 101, 4)  # передумал
ratings.count_documents({'task_id': 1, 'user_id': 101})  # 1
```

Две детали делают это надёжным: **upsert** («обнови, а если нет — создай») и **уникальный составной индекс**. Без индекса два одновременных upsert от одного пользователя могут оба не найти документ и оба вставить — индекс второй вставке не даст: она получит `DuplicateKeyError`, и операцию достаточно повторить — теперь это будет обновление.

## Схема: вложить или вынести

Первая мысль — хранить оценки прямо в документе задачи:

```python
{'_id': 1, 'title': 'Сдать отчёт', 'ratings': [{'user_id': 101, 'score': 5}, ...]}
```

Для UGC это плохая идея:

- **предел 16 МБ на документ.** Оценка занимает около 40 байт, и задача с полумиллионом оценок упрётся в предел — запись просто перестанет проходить;
- **растущий документ.** Каждая новая оценка переписывает документ целиком, и он становится всё дороже; читать задачу ради заголовка приходится вместе со всеми оценками;
- **конкуренция.** Все пользователи пишут в один документ, и операции над ним выстраиваются в очередь;
- **шардирование.** Документ целиком живёт на одном шарде, его нельзя разделить, а запрос «мои оценки» превращается в поиск по массивам всех задач.

Правило из [основ](basics.md#вложить-или-сослаться): вкладывать то, что ограничено и читается вместе с родителем; выносить то, что растёт неограниченно. UGC растёт неограниченно, поэтому у каждого вида — своя коллекция:

```python
# ugc.task_ratings — один документ на пару (задача, пользователь)
{'_id': ObjectId(...), 'task_id': 1, 'user_id': 101, 'score': 4, 'created_at': ..., 'updated_at': ...}

# ugc.task_comments — один документ на комментарий
{'_id': ObjectId(...), 'task_id': 1, 'author_id': 102, 'text': 'Не забудь про графики'}

# ugc.bookmarks — один документ на закладку
{'_id': ObjectId(...), 'user_id': 101, 'task_id': 5, 'created_at': ...}
```

Вложение остаётся уместным внутри одного элемента: реакции на комментарий (`{'like': 3, 'fire': 1}`) или последние три комментария в карточке задачи — ограниченная копия для быстрого показа.

## Индексы и уникальность

Индексы подбираются под запросы:

| Коллекция | Запрос | Индекс |
|---|---|---|
| `task_ratings` | оценка пользователя за задачу, уникальность | `{task_id: 1, user_id: 1}`, `unique` |
| `task_ratings` | «мои оценки», новые сверху | `{user_id: 1, created_at: -1}` |
| `task_comments` | комментарии задачи, новые сверху | `{task_id: 1, _id: -1}` |
| `bookmarks` | «мои закладки», без дублей | `{user_id: 1, task_id: 1}`, `unique` |

В шардированной коллекции уникальный индекс обязан начинаться с ключа шардирования: каждый шард проверяет уникальность только у себя и не знает о документах соседей. При ключе `{task_id: 'hashed'}` индекс `{task_id: 1, user_id: 1}` создаётся, а `{user_id: 1}` — нет:

```text
уникальный индекс без ключа шардирования: CannotCreateIndex
вторая оценка того же пользователя: DuplicateKeyError
```

Закладки повторяют тот же приём: `update_one({'user_id': ..., 'task_id': ...}, {'$setOnInsert': {...}}, upsert=True)` идемпотентна — повторный клик по «в закладки» ничего не меняет.

## Счётчики: на лету или денормализовать

Карточке задачи нужны число оценок и средний балл. Есть два пути.

**Агрегат на лету** — считать при каждом запросе:

```python
ratings.aggregate([
    {'$match': {'task_id': 1}},
    {'$group': {'_id': '$task_id', 'count': {'$sum': 1}, 'avg': {'$avg': '$score'}}},
])
# {'_id': 1, 'count': 2, 'avg': 3.5}
```

Всегда точно и ничего не нужно поддерживать. Но запрос читает все оценки задачи, и для популярной задачи в ленте из 50 карточек это 50 агрегаций на каждый показ.

**Денормализованный счётчик** — хранить сумму и количество в документе задачи и менять их атомарным `$inc` при каждой оценке. Если пользователь меняет оценку, счётчик сдвигается на разницу — старую оценку возвращает `find_one_and_update` с `ReturnDocument.BEFORE`:

```python
from pymongo import ReturnDocument


def rate(task_id: int, user_id: int, score: int) -> None:
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
rate(1, 101, 4)
task = db.tasks.find_one({'_id': 1})
task['ratings_count'], task['ratings_sum'] / task['ratings_count']  # (2, 3.5)
```

Чтение стоит одно обращение по `_id`, но появились две записи вместо одной, и они в разных коллекциях — а значит, скорее всего, на разных шардах. Упадёт процесс между ними — счётчик разойдётся с оценками. Варианты: оборачивать обе записи в транзакцию (в шардированном кластере это распределённая транзакция — дорого), обновлять счётчик асинхронно из очереди или [потока изменений](https://www.mongodb.com/docs/manual/changestreams/) (change streams) и периодически пересчитывать его агрегатом.

На практике: агрегат на лету — пока данных мало или нужна точность; счётчик — когда карточки показывают часто, а небольшое расхождение допустимо (счётчик лайков может отстать на секунду).

## Пагинация комментариев

Привычное `skip(offset).limit(10)` на глубоких страницах медленное: базе приходится пройти и выбросить все пропущенные записи. Вместо номера страницы клиент передаёт `_id` последнего показанного комментария (курсорная пагинация, keyset pagination):

```python
from bson import ObjectId
from pymongo import DESCENDING


def comments_page(task_id: int, before_id: ObjectId | None = None, limit: int = 10) -> list[dict]:
    query = {'task_id': task_id}
    if before_id is not None:
        query['_id'] = {'$lt': before_id}
    return list(db.task_comments.find(query, {'text': 1}).sort('_id', DESCENDING).limit(limit))


page1 = comments_page(1)
page2 = comments_page(1, before_id=page1[-1]['_id'])
```

`ObjectId` растёт со временем, поэтому сортировка по `_id` — это «новые сверху» без отдельного поля и с уникальным порядком (у `created_at` бывают одинаковые значения, и записи на границе страницы теряются или дублируются).

Разница на 50 000 комментариев одной задачи (индекс `{task_id: 1, _id: -1}`), страница на глубине 40 000:

```text
skip(40000)        просмотрено ключей:  40010, документов:     10, 331 мс
_id < последнего   просмотрено ключей:     10, документов:     10, 12 мс
```

Цена курсорной пагинации — нельзя перейти сразу на страницу 57. Для ленты комментариев это и не нужно.

## Асинхронный доступ из Python

Для FastAPI нужен асинхронный драйвер. Актуальная картина на конец 2026 года:

- **PyMongo `AsyncMongoClient`** — официальный асинхронный клиент, стабилен с PyMongo 4.13, API совпадает с синхронным плюс `await`. Motor объявлен устаревшим, новый код на нём не пишут;
- **Beanie** — ODM поверх Pydantic. С версии 2.0 работает на `AsyncMongoClient` из PyMongo, а не на Motor.

Проверено с `pymongo==4.19.0` и `beanie==2.2.0`:

```python
import asyncio
from datetime import UTC, datetime

from pymongo import AsyncMongoClient, ReturnDocument


async def main() -> None:
    client = AsyncMongoClient('mongodb://localhost:37017')
    ratings = client.ugc.task_ratings

    doc = await ratings.find_one_and_update(
        {'task_id': 3, 'user_id': 201},
        {'$set': {'score': 4}, '$setOnInsert': {'created_at': datetime.now(UTC)}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    print(doc['score'])  # 4

    async for row in await ratings.aggregate([{'$match': {'task_id': 3}},
                                              {'$group': {'_id': None, 'avg': {'$avg': '$score'}}}]):
        print(row['avg'])  # 4.0
    await client.close()


asyncio.run(main())
```

`aggregate` в асинхронном клиенте — корутина, которая возвращает курсор: отсюда `async for row in await ...`.

То же через Beanie — модель описывает документ и проверяет данные Pydantic-валидацией:

```python
from beanie import Document, init_beanie
from pydantic import Field


class TaskRating(Document):
    task_id: int
    user_id: int
    score: int = Field(ge=1, le=5)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = 'task_ratings'


async def main() -> None:
    client = AsyncMongoClient('mongodb://localhost:37017')
    await init_beanie(database=client.ugc, document_models=[TaskRating])

    await TaskRating.find_one(TaskRating.task_id == 3, TaskRating.user_id == 202).upsert(
        {'$set': {TaskRating.score: 5}},
        on_insert=TaskRating(task_id=3, user_id=202, score=5),
    )
    top = await TaskRating.find(TaskRating.task_id == 3).sort(-TaskRating.score).to_list()
    print([(r.user_id, r.score) for r in top])  # [(202, 5), (201, 4)]

    TaskRating(task_id=3, user_id=203, score=10)
    # ValidationError: Input should be less than or equal to 5
```

Beanie удобен, когда модели уже на Pydantic и хочется проверки схемы на входе. Чистый `AsyncMongoClient` проще и прозрачнее для `find_one_and_update`, агрегаций и тонкой работы с `writeConcern`.

## Ключи шардирования

Ключ выбирают по самому частому запросу и по тому, как распределится запись ([подробнее](sharding.md#ключ-шардирования)):

| Коллекция | Ключ | Почему |
|---|---|---|
| `task_ratings` | `{task_id: 'hashed'}` | Главные запросы — «оценки задачи» и «оценка пользователя за задачу», оба с `task_id` и адресные. Хэш раскладывает запись равномерно, хотя `task_id` растёт. Уникальный индекс `{task_id, user_id}` допустим. «Мои оценки» идут на все шарды — это редкий запрос |
| `task_comments` | `{task_id: 'hashed', _id: 1}` | Комментарии задачи — один адресный запрос, пагинация по `_id` остаётся адресной (`SINGLE_SHARD`). Второе поле позволяет разрезать комментарии одной популярной задачи на несколько чанков |
| `bookmarks` | `{user_id: 'hashed'}` | Закладки читают только «мои». Уникальный `{user_id, task_id}` допустим |
| `tasks` (счётчики) | `{_id: 'hashed'}` | Чтение и `$inc` по `_id` — адресные |

Второе поле в ключе комментариев проверено: 50 000 комментариев одной задачи сначала легли в один чанк на `rs1`, а балансировщик отрезал и перенёс часть на `rs2` — с ключом `{task_id: 'hashed'}` такой чанк остался бы неделимым.

Если бы ключом оценок был `{user_id: 1}`, запрос «оценки задачи» шёл бы на все шарды, а уникальность пары `(task_id, user_id)` пришлось бы держать индексом `{user_id: 1, task_id: 1}` — так тоже можно, если важнее «мои оценки». Ключ `{created_at: 1}` или `{_id: 1}` дал бы горячий шард.

## Частые ошибки

- **Массив всех лайков в документе задачи.** Документ растёт, упирается в 16 МБ, запись в него становится очередью → отдельная коллекция.
- **Проверка «уже оценил?» через `find`, затем `insert`.** Две параллельные заявки обе пройдут проверку → уникальный индекс + upsert.
- **`skip` для ленты комментариев.** Глубокие страницы медленные, при новых комментариях записи сдвигаются и дублируются → пагинация по `_id`.
- **Счётчик через `find` + `update` с `$set: count + 1`.** Параллельные запросы теряют инкременты → атомарный `$inc`.
- **Уникальный индекс без ключа шардирования.** `CannotCreateIndex` → ключ шардирования в начале индекса или другой ключ.

## Когда не использовать

Если оценок немного (тысячи на задачу, миллионы всего), а основная база — PostgreSQL, отдельный MongoDB добавит лишнюю систему для эксплуатации: таблица `task_ratings` с `UNIQUE (task_id, user_id)` и `INSERT ... ON CONFLICT DO UPDATE` решает ту же задачу. Для аналитики по UGC (средние по дням, топы за месяц на миллиардах событий) лучше подходит колоночная база вроде [ClickHouse](../clickhouse/README.md), а MongoDB оставить для быстрых точечных чтений и записи.

## Связанные темы

- [Шардирование и кластер MongoDB](sharding.md) — репликасеты, ключ шардирования, балансировщик
- [MongoDB: основы](basics.md) — вложить или сослаться, индексы, upsert
- [MongoDB: агрегации](aggregation.md) — конвейер `$match` → `$group`
- [Как базы данных хранят данные](../storage/README.md)
