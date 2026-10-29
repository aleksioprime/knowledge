# Kafka в FastAPI: события между сервисами

Сервис задач должен сообщать другим сервисам, что произошло: задача создана, задача выполнена. Аналитика считает статистику, поиск обновляет индекс, уведомления шлют письма. Kafka хранит такие события в журнале: сервис задач только дописывает их в конец, а каждый потребитель читает журнал в своём темпе и с того места, где остановился. Новый сервис может прочитать и всю историю с самого начала.

Код примера — в [examples/fastapi](examples/fastapi/README.md). Клиент — `aiokafka`, асинхронный, подходит для FastAPI.

```bash
pip install aiokafka
```

## Минимальный пример

```bash
curl -X POST localhost:8010/tasks -H 'Content-Type: application/json' -d '{"title": "Сдать отчёт", "owner_id": 1}'
curl -X POST localhost:8010/tasks -H 'Content-Type: application/json' -d '{"title": "Купить хлеб", "owner_id": 1}'
curl -X POST localhost:8010/tasks -H 'Content-Type: application/json' -d '{"title": "Починить кран", "owner_id": 2}'
curl -X POST localhost:8010/tasks/1/done

curl localhost:8011/stats
# {"1":{"created":2,"done":1},"2":{"created":1,"done":0}}
```

Сервис задач ничего не знает об аналитике: он только пишет события в топик `task-events`.

## Производитель: публикуем событие

Производитель создаётся один раз при старте приложения и закрывается при остановке — в `lifespan`:

```python
# tasks_service/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    producer = AIOKafkaProducer(
        bootstrap_servers=os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9096'),
        key_serializer=lambda key: str(key).encode(),
        value_serializer=lambda value: json.dumps(value, ensure_ascii=False).encode(),
        acks='all',
    )
    await producer.start()
    app.state.producer = producer
    yield
    await producer.stop()


async def publish(request: Request, event_type: str, task: dict) -> None:
    event = {'type': event_type, 'task': task, 'at': datetime.now(timezone.utc).isoformat()}
    # Ключ — владелец: все события одного пользователя попадут в одну партицию и сохранят порядок
    await request.app.state.producer.send_and_wait(TOPIC, key=task['owner_id'], value=event)
```

- `send_and_wait` ждёт подтверждения от Kafka. Если оно не пришло, эндпоинт упадёт, и клиент узнает об ошибке;
- `acks='all'` — подтверждение приходит, когда событие записали все реплики партиции. Медленнее, зато не теряется при падении одного брокера.

## Ключ и партиции

Топик разделён на **партиции** — независимые журналы. В примере их три (`KAFKA_NUM_PARTITIONS: 3`). Kafka выбирает партицию по хэшу ключа, поэтому все события пользователя 1 попадают в одну партицию:

```text
task.created, партиция 0, смещение 0    ← пользователь 1
task.created, партиция 0, смещение 1    ← пользователь 1
task.created, партиция 2, смещение 0    ← пользователь 2
task.done,    партиция 0, смещение 2    ← пользователь 1
```

Порядок Kafka гарантирует **только внутри партиции**. Благодаря ключу «создана» у задачи пользователя 1 никогда не обгонит «выполнена». Без ключа события разошлись бы по разным партициям, и потребитель мог бы получить их в другом порядке.

**Смещение** (offset) — номер события внутри партиции. Потребитель запоминает смещение, до которого дочитал.

## Потребитель: читаем в фоне

Потребитель тоже стартует в `lifespan`, а чтение идёт в фоновой задаче asyncio, пока API отвечает на запросы:

```python
# analytics_service/main.py
async def consume(consumer: AIOKafkaConsumer) -> None:
    async for message in consumer:
        event = json.loads(message.value)
        handle(event)
        # Смещение фиксируем только после обработки: при падении событие придёт снова
        await consumer.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    consumer = AIOKafkaConsumer(
        'task-events',
        bootstrap_servers=os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9096'),
        group_id='analytics',
        auto_offset_reset='earliest',
        enable_auto_commit=False,
    )
    await consumer.start()
    worker = asyncio.create_task(consume(consumer))
    yield
    worker.cancel()
    await consumer.stop()
```

- `group_id='analytics'` — **группа потребителей**. Kafka хранит смещения для группы, а партиции делит между её участниками. Запустите три копии аналитики — каждая будет читать свою партицию. Другая группа (например, `search`) читает тот же топик независимо;
- `auto_offset_reset='earliest'` — новая группа, у которой ещё нет смещений, начнёт с самого первого события;
- `enable_auto_commit=False` и `commit()` после обработки — гарантия «хотя бы один раз». Если сервис упадёт после обработки, но до `commit`, событие придёт ещё раз. Поэтому обработка должна выдерживать повторы.

Состояние группы можно посмотреть утилитой Kafka:

```bash
docker compose exec kafka /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 --describe --group analytics
```

```text
TOPIC        PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
task-events  0          3               3               0
task-events  1          0               0               0
task-events  2          1               1               0
```

`LAG` — сколько событий потребитель ещё не прочитал. Растущий `LAG` — первый признак того, что потребитель не справляется.

## Перечитать историю

В примере статистика хранится в памяти. Перезапустим аналитику и посмотрим:

```bash
docker compose restart analytics-service
curl localhost:8011/stats
# {}
```

Данные пропали, а события заново не пришли: смещения сохранены, и группа продолжает с того места, где остановилась. В журнале события при этом никуда не делись, поэтому статистику можно восстановить, перемотав смещения группы на начало:

```bash
docker compose stop analytics-service
docker compose exec kafka /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group analytics --topic task-events --reset-offsets --to-earliest --execute
docker compose start analytics-service

curl localhost:8011/stats
# {"1":{"created":2,"done":1},"2":{"created":1,"done":0}}
```

Это главное отличие Kafka от классических очередей: прочитанное сообщение не удаляется. Новый сервис можно запустить через полгода, и он построит своё состояние по всей истории (пока она хранится — по умолчанию 7 дней, настраивается).

В рабочем сервисе состояние, конечно, хранят в базе, а не в памяти.

## Частые ошибки

- **Нет ключа там, где важен порядок.** События одной сущности окажутся в разных партициях и придут перепутанными.
- **Автоматическая фиксация смещений.** С `enable_auto_commit=True` смещение может зафиксироваться до обработки. Упал посередине — событие потеряно.
- **Неидемпотентная обработка.** После перебалансировки группы или падения события приходят повторно. Если обработчик прибавляет +1 к счётчику, статистика завысится. Запоминайте обработанные id событий или делайте операции идемпотентными.
- **Потребителей в группе больше, чем партиций.** У лишних потребителей не будет партиций, и они будут простаивать. Число партиций — потолок параллелизма группы.
- **Событие отправлено, а транзакция в базе откатилась.** Или наоборот: задача сохранена, а событие не ушло. Надёжное решение — паттерн Outbox: событие сохраняется в таблицу той же транзакцией, а отдельный процесс публикует его в Kafka.

## Связанные темы

- [Партиции и группы потребителей наглядно](partitions_visual.md)
- [Apache Kafka: основные понятия](README.md)
- [Простые примеры Kafka](examples/simple/README.md)
- [NATS](../nats/README.md) — более лёгкая альтернатива для событий
- [Брокеры сообщений: гарантии доставки](../README.md)
