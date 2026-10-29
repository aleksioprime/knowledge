# Из Kafka в ClickHouse

Пользователи «Задачника» создают, просматривают, выполняют и оценивают задачи. Каждое действие — событие, и аналитикам нужны отчёты: какие задачи смотрят чаще всего, сколько людей пользуются сервисом в день, какие задачи хуже оценивают. Писать такие события в основную базу PostgreSQL плохо: их в сотни раз больше, чем задач, а отчёты по ним сканируют миллионы строк. Обычная схема: API принимает событие и сразу кладёт его в Kafka, а оттуда оно попадает в аналитическое хранилище ClickHouse.

```text
клиент ──POST /events──► API (FastAPI) ──► Kafka: task-events ──► ClickHouse: ugc.events ──► отчёты
```

Kafka здесь — буфер: API отвечает быстро, даже если ClickHouse перегружен или на обслуживании, а события дождутся его в журнале. Пример — [examples/kafka](examples/kafka/README.md).

## Минимальный пример

```bash
cd docs/backend/databases/clickhouse/examples/kafka
docker compose -p kb-ugc up -d --build

curl -X POST localhost:38000/events -H 'Content-Type: application/json' \
  -d '{"event_type": "task.rated", "user_id": 1, "task_id": 7, "rating": 5}'
# {"event_id":"d886f205-6868-48b9-a905-7b608c338416"}

# через несколько секунд
docker compose -p kb-ugc exec clickhouse clickhouse-client --user ugc --password ugc \
  -q "SELECT * FROM ugc.events FORMAT Vertical"
```

```text
event_id:        d886f205-6868-48b9-a905-7b608c338416
event_type:      task.rated
user_id:         1
task_id:         7
rating:          5
event_time:      2026-10-29 07:36:39.586
kafka_partition: 0
kafka_offset:    0
```

## Как это работает

### API: принять событие и положить в Kafka

API не пишет в ClickHouse сам: его задача — проверить событие и как можно быстрее отдать его в Kafka.

```python
# api/main.py
producer = AIOKafkaProducer(
    bootstrap_servers=os.environ.get('KAFKA_BOOTSTRAP_SERVERS', '127.0.0.1:39192'),
    acks='all',
    enable_idempotence=True,
    linger_ms=20,
    max_batch_size=256 * 1024,
    compression_type='gzip',
    key_serializer=lambda key: str(key).encode(),
    value_serializer=lambda value: json.dumps(value).encode(),
)


@app.post('/events', status_code=202)
async def create_event(event: EventIn, request: Request) -> dict:
    payload = event.model_dump() | {
        'event_id': str(uuid.uuid4()),
        'event_time': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
    }
    await request.app.state.producer.send_and_wait(TOPIC, key=event.user_id, value=payload)
    return {'event_id': payload['event_id']}
```

- **Батчинг продюсера.** `linger_ms=20` — продюсер ждёт до 20 мс, собирая в одну пачку события от разных одновременных HTTP-запросов, и отправляет их одним запросом к брокеру. `max_batch_size` — потолок пачки на партицию. Пачка сжимается целиком (`gzip`), а одинаковые JSON-ключи сжимаются хорошо. Цена — до 20 мс задержки на запрос;
- **Ключ = `user_id`.** События одного пользователя попадают в одну партицию и не перемешиваются: «создал» не обгонит «выполнил». Подробнее о ключах — в [Kafka в FastAPI](../../microservices/broker/kafka/fastapi.md);
- **`acks='all'` и идемпотентность** — подтверждённое событие не потеряется при падении брокера, а повтор отправки не создаст дубль в Kafka. Что именно они гарантируют — в [Kafka изнутри](../../microservices/broker/kafka/internals.md);
- **`event_time` ставит сервер** — клиентскому времени верить нельзя. `event_id` в примере тоже генерирует сервер, и это упрощение: от повторов клиента он не спасает (что из этого вышло — в разделе «Сколько это заняло»);
- **`send_and_wait`** — ответ 202 уходит, только когда Kafka подтвердила запись. Можно отвечать сразу после `send()`, не дожидаясь подтверждения: быстрее, но при падении API события из буфера продюсера пропадут.

### ClickHouse читает Kafka сам: движок Kafka и materialized view

В ClickHouse есть движок таблиц `Kafka`: таблица с ним — это подписка на топик, а не хранилище. Схема из трёх объектов:

```sql
-- 1. Хранилище: здесь лежат данные, отсюда читают отчёты
CREATE TABLE ugc.events
(
    event_id        UUID,
    event_type      LowCardinality(String),
    user_id         UInt64,
    task_id         UInt64,
    rating          Nullable(UInt8),
    event_time      DateTime64(3, 'UTC'),
    kafka_partition UInt16,
    kafka_offset    UInt64
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(event_time)
ORDER BY (event_type, event_time, task_id);

-- 2. Очередь: потребитель топика task-events в группе clickhouse
CREATE TABLE ugc.events_queue
(
    event_id String, event_type String, user_id UInt64, task_id UInt64,
    rating Nullable(UInt8), event_time String
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:9092',
    kafka_topic_list = 'task-events',
    kafka_group_name = 'clickhouse',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1,
    kafka_max_block_size = 65536,
    kafka_skip_broken_messages = 10;

-- 3. Перекладчик: всё, что прочитано из очереди, вставляется в events
CREATE MATERIALIZED VIEW ugc.events_mv TO ugc.events AS
SELECT
    toUUID(event_id) AS event_id,
    event_type, user_id, task_id, rating,
    parseDateTime64BestEffort(event_time, 3, 'UTC') AS event_time,
    _partition AS kafka_partition,
    _offset AS kafka_offset
FROM ugc.events_queue;
```

Как это работает. Пока к таблице `events_queue` привязан хотя бы один materialized view, ClickHouse в фоне читает топик: набирает блок до `kafka_max_block_size` сообщений или до `stream_flush_interval_ms` (7,5 секунды), прогоняет его через `SELECT` из view и вставляет результат в `events` одной пачкой. Потом фиксирует смещения в Kafka. Materialized view в ClickHouse — это не сохранённый результат запроса, как в PostgreSQL, а **триггер на вставку**: он срабатывает на каждый новый блок.

Почему не читать таблицу `events_queue` напрямую:

- **Чтение забирает данные.** `SELECT` из Kafka-таблицы — это чтение потребителем группы `clickhouse`: смещения сдвигаются, и прочитанное уже не попадёт в `events`. Второй `SELECT` вернёт другие строки. Это очередь, а не таблица;
- **Нет хранения.** Kafka-таблица ничего не сохраняет на диск ClickHouse, по ней нельзя построить отчёт за месяц;
- поэтому в свежих версиях прямой `SELECT` запрещён:

```text
Code: 620. DB::Exception: Direct select is not allowed. To enable use setting
`stream_like_engine_allow_direct_select`, but be aware that usually the read data is removed from the queue.. (QUERY_NOT_ALLOWED)
```

Ещё полезное:

- **Типы в очереди — «как пришло».** Время приходит строкой ISO 8601, поэтому в `events_queue` оно `String`, а преобразование — во view. Так поломка формата не роняет чтение всего топика, а `kafka_skip_broken_messages` пропускает до 10 битых сообщений на блок;
- **Виртуальные колонки** `_partition`, `_offset`, `_key`, `_timestamp` — откуда пришло событие. По `(kafka_partition, kafka_offset)` легко найти дубли;
- **Состояние потребителя** — в `system.kafka_consumers`: назначенные партиции, текущие смещения, последние ошибки;
- **Поменять схему** — отцепить view (`DETACH TABLE ugc.events_mv`), изменить таблицы, прицепить обратно. Пока view отцеплен, данные копятся в Kafka;
- **Гарантия — at least once.** ClickHouse вставляет блок, а потом фиксирует смещения. Упал между ними — блок придёт ещё раз. Дубли гасят движком `ReplacingMergeTree` с `ORDER BY`, включающим `event_id`, или дедупликацией в запросах.

### Альтернатива: свой консьюмер, который пишет пачками

Движок Kafka удобен, но вся логика — внутри ClickHouse: сложную валидацию, обогащение из других сервисов, метрики и алерты так не сделаешь. Тогда пишут свой сервис-потребитель. Главное правило — **вставлять пачками**:

```python
# consumer.py
while True:
    batches = await consumer.getmany(timeout_ms=500, max_records=10_000)
    for messages in batches.values():
        rows.extend(to_row(message) for message in messages)

    if rows and (len(rows) >= BATCH_SIZE or time.monotonic() - flushed_at >= BATCH_SECONDS):
        await asyncio.to_thread(ch.insert, 'ugc.events_batch', rows, column_names=COLUMNS)
        await consumer.commit()
        rows = []
        flushed_at = time.monotonic()
```

Пачка уходит, когда набралось 50 000 строк или прошло 2 секунды — что раньше. Смещения фиксируются **после** вставки: при падении пачка придёт снова (at least once). Клиент — `clickhouse-connect` (HTTP-протокол, вставка в колоночном бинарном формате). Он синхронный, поэтому вызов уходит в поток через `asyncio.to_thread`.

На стенде этот консьюмер вычитал весь топик с начала (100 420 событий) в таблицу `events_batch` за 9,9 секунды вместе с запуском, двумя вставками по 51 807 и 48 613 строк. В таблице появились две части.

#### Почему ClickHouse не любит вставки по одной строке

Каждый `INSERT` в таблицу `MergeTree` создаёт на диске новую **часть** (part) — каталог с отдельным файлом на каждую колонку, засечками и индексом. Фоновые **слияния** (merges) потом склеивают мелкие части в крупные. Вставили 1 строку — создали каталог с десятком файлов и ещё потратили работу на слияние. Вставили 50 000 — то же самое, но один раз.

Если части появляются быстрее, чем сливаются, ClickHouse защищается: при числе активных частей в партиции больше `parts_to_delay_insert` (1000) замедляет вставки, а больше `parts_to_throw_insert` (3000) отказывает с ошибкой `TOO_MANY_PARTS` — «Too many parts ... Merges are processing significantly slower than inserts» (на стенде до неё не доводили, пороги взяты из `system.merge_tree_settings`).

Правило из документации: не чаще одного `INSERT` в секунду на таблицу, пачками от тысяч строк.

**Асинхронная вставка** (async insert) — если пачки собрать на клиенте нельзя (много мелких источников, serverless-функции), это может сделать сервер:

```sql
INSERT INTO ugc.events SETTINGS async_insert = 1, wait_for_async_insert = 1 VALUES (...);
```

Сервер копит мелкие вставки в памяти и сбрасывает их одной частью по размеру (`async_insert_max_data_size`, 10 МБ) или по времени (`async_insert_busy_timeout_max_ms`, 200 мс). С `wait_for_async_insert = 1` клиент ждёт записи на диск. С `0` ответ приходит сразу, но при падении сервера накопленное теряется.

В ClickHouse 26.3 со стенда `async_insert` и `wait_for_async_insert` уже включены по умолчанию (`system.settings`: `value = 1`, `changed = 0`); раньше `async_insert` по умолчанию был выключен, поэтому в своей версии лучше проверить. Но асинхронная вставка склеивает только **одновременные** вставки от многих клиентов. Один клиент, который шлёт строки по очереди и ждёт ответа на каждую, ничего не выигрывает: на стенде 500 последовательных однострочных `INSERT` с `async_insert = 0` заняли 3,2 с, а с `async_insert = 1` — 36,2 с (каждая вставка ждала таймера сброса), и частей в обоих случаях получилось одинаково. Для своего консьюмера пачки на клиенте по-прежнему лучше.

### Ключ сортировки и партиции для событий

`ORDER BY` в MergeTree — физический порядок строк на диске и разреженный первичный индекс: на каждые 8192 строки хранится одна засечка с значениями ключа. По фильтру ClickHouse отбрасывает целые блоки, не читая их. Как выбрать:

- впереди — колонки, по которым **фильтруют почти всегда** и у которых **мало разных значений**: `event_type` (четыре значения);
- затем время: отчёты почти всегда за период;
- в конце — то, по чему группируют: `task_id`. Одинаковые значения рядом лучше сжимаются.

С `ORDER BY (event_type, event_time, task_id)` запрос «просмотры за 15 октября» читает только блоки, где `event_type = 'task.viewed'` и время в нужном дне. Запрос по `user_id` без других фильтров индекс не ускорит — для этого добавляют проекцию (projection) или отдельную таблицу с другим ключом.

`PARTITION BY` — крупное деление для **управления данными**, а не для скорости: удалить старый месяц (`ALTER TABLE ... DROP PARTITION`), перенести на холодный диск. Части разных партиций не сливаются друг с другом, поэтому слишком мелкие партиции (по дню при небольшом потоке, по `user_id`) плодят части. Для событий обычно хватает месяца: `toYYYYMM(event_time)`.

### Отчёты

Самые просматриваемые задачи за день:

```sql
SELECT task_id, count() AS views
FROM ugc.events
WHERE event_type = 'task.viewed' AND toDate(event_time) = today()
GROUP BY task_id
ORDER BY views DESC
LIMIT 5;
```

```text
   ┌─task_id─┬─views─┐
1. │       1 │ 20370 │
2. │       2 │  6032 │
3. │       3 │  2833 │
4. │       4 │  1665 │
5. │       5 │  1009 │
   └─────────┴───────┘
```

Генератор нагрузки делает задачи с маленькими номерами популярнее, поэтому лидирует задача 1.

Уникальные пользователи по типам событий:

```sql
SELECT event_type, uniq(user_id) AS users, uniqExact(user_id) AS users_exact, count() AS events
FROM ugc.events
GROUP BY event_type
ORDER BY events DESC;
```

```text
   ┌─event_type───┬─users─┬─users_exact─┬─events─┐
1. │ task.viewed  │  5000 │        5000 │  71933 │
2. │ task.done    │  4446 │        4446 │  12052 │
3. │ task.created │  4476 │        4476 │  11964 │
4. │ task.rated   │  4417 │        4417 │  11874 │
   └──────────────┴───────┴─────────────┴────────┘
```

Оба запроса выполнились за 0,08–0,15 с. Счётчики `events` включают дубли — о них ниже.

`uniq` — приближённый подсчёт (HyperLogLog-подобный алгоритм, погрешность доли процента), занимает фиксированную память. `uniqExact` — точный, но держит в памяти все значения. На миллиардах строк разница в памяти и скорости заметна.

### Сколько это заняло

Скрипт [load.py](examples/kafka/load.py) отправил 100 000 событий в API, по 50 запросов одновременно. Машина: MacBook на Apple M1, 8 ГБ памяти, Docker Desktop 29.8 (виртуальной машине выделено 8 ядер и 3,8 ГБ). Важная оговорка: одновременно в том же Docker работали чужие стенды (MongoDB, Elasticsearch, Spark и другие), средняя загрузка виртуальной машины держалась на 50–90 при 8 ядрах, а ClickHouse за время опыта дважды убивался системой из-за нехватки памяти. Поэтому цифры скорости ниже **не характеризуют** ни FastAPI, ни Kafka, ни ClickHouse — на свободной машине они будут на порядки лучше. Зато опыт показал, как стек ведёт себя при сбоях.

```text
API принял 99921 событий за 2761.5 с (36 в секунду), ошибок: 79
```

Для сравнения, контрольный прогон на 2 000 событий, когда загрузка машины упала до 3–4: API принимал 176 событий в секунду, все 2 000 оказались в ClickHouse через 37 с после старта (первые блоки ждали, пока движок Kafka переподключится к только что перезапущенному брокеру). Где узкое место API на этом стенде — в FastAPI, в ожидании `send_and_wait` или в пробросе портов Docker Desktop на macOS, — не исследовалось.

Итоги большого прогона:

| Что | Число |
|---|---|
| Принято API с ответом 202 | 99 921 |
| Не принято после трёх попыток (обрыв соединения через проброс портов Docker) | 79 |
| Сообщений в топике `task-events` | 100 420 |
| Строк в `ugc.events` | 107 823 |
| Уникальных `event_id` в `ugc.events` | 100 420 — все сообщения топика дошли |
| Дублей в `ugc.events` | 7 403 |
| Частей, созданных движком Kafka за 47 минут / активных после слияний | 136 / 5 |
| Размер `ugc.events` на диске | 3,17 МБ |

Что видно из таблицы:

- **Все события из Kafka дошли до ClickHouse**, несмотря на два падения сервера: смещения фиксируются после вставки, после перезапуска чтение продолжилось.
- **7 403 дубля — это at least once в действии.** ClickHouse вставил блоки, упал раньше, чем зафиксировал смещения, и после перезапуска прочитал их снова. Дубли легко найти по `event_id` или по паре `(kafka_partition, kafka_offset)`. В бою берут `ReplacingMergeTree` с `event_id` в ключе сортировки или считают `uniqExact(event_id)` вместо `count()`.
- **В топике на 498 сообщений больше, чем ответов 202** (плюс одно событие из минимального примера). Это повторы клиента: API успел отправить событие в Kafka, а ответ потерялся по дороге, и скрипт отправил его ещё раз. Сервер каждый раз ставил новый `event_id`, поэтому такие дубли уже не отличить от настоящих событий. Вывод: если клиент может повторять запросы, `event_id` должен генерировать **клиент** — тогда повтор несёт тот же id и отсеивается.
- **Движок Kafka сам делает пачки.** При медленном потоке он сбрасывал блок примерно раз в 7,5 секунды (`stream_flush_interval_ms`), получилось 136 частей за 47 минут, которые фоновые слияния свели к пяти. При одной строке на `INSERT` частей было бы 100 тысяч.

## Частые ошибки

- **`SELECT` из Kafka-таблицы для проверки.** Прочитанные так сообщения не попадут в хранилище. Смотрите в `MergeTree`-таблицу и в `system.kafka_consumers`.
- **Kafka-таблица без materialized view.** Без view никто не читает топик, данные копятся в Kafka. С двумя view на одну очередь каждый блок вставится в обе цели — иногда это и нужно (сырые события и агрегаты).
- **Строгие типы в очереди.** Одно сообщение с неожиданным форматом даты — и чтение встаёт с ошибкой парсинга. Принимайте строкой, преобразуйте во view, задайте `kafka_skip_broken_messages`.
- **`INSERT` на каждое событие из своего консьюмера.** Тысячи частей, `Too many parts`, сервер тратит CPU на слияния. Только пачки или async insert.
- **`PARTITION BY` по дню или по пользователю.** Слишком много частей, которые не сливаются между партициями. Месяц — разумный старт.
- **`kafka_num_consumers` больше числа партиций.** Лишние потребители простаивают, а каждый занимает поток. Ставьте не больше числа партиций и не больше числа ядер.
- **`count()` по таблице, куда пишут с гарантией at least once.** После сбоя в ней есть дубли, и счётчики завышены. Считайте `uniqExact(event_id)` или используйте `ReplacingMergeTree`.
- **`event_id` генерирует сервер, а клиент повторяет запросы.** Повтор получает новый id, и дубль уже не отличить. Ключ идемпотентности создаёт тот, кто повторяет.
- **Ожидать, что событие появится сразу.** Движок Kafka сбрасывает блок раз в `stream_flush_interval_ms` (7,5 с) или по заполнению. Для аналитики это нормально, для «показать пользователю его оценку» — нет: такое читают из основной базы.

## Когда не использовать

Если событий немного (тысячи в день) и отчёты простые, хватит таблицы в PostgreSQL и запроса по индексу — Kafka и ClickHouse добавят две системы, которые надо поддерживать. Если нужно показывать пользователю его же данные сразу после действия — это работа основной базы, а не аналитического хранилища. Как выбирать хранилище обоснованно — в заметке [Как выбрать аналитическое хранилище](research.md).

## Связанные темы

- [ClickHouse](README.md) — движки MergeTree, OLTP и OLAP
- [Как выбрать аналитическое хранилище: исследование](research.md)
- [Kafka изнутри: надёжность и хранение](../../microservices/broker/kafka/internals.md)
- [Kafka в FastAPI](../../microservices/broker/kafka/fastapi.md)
- [Контракты между сервисами](../../microservices/contracts.md) — схема событий в Avro
