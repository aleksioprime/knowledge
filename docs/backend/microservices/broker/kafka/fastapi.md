# Kafka в FastAPI: события между сервисами

Сервис задач должен сообщать другим сервисам, что произошло: задача создана, задача выполнена. Аналитика считает статистику, поиск обновляет индекс, уведомления шлют письма. Kafka хранит такие события в журнале: сервис задач только дописывает их в конец, а каждый потребитель читает журнал в своём темпе и с того места, где остановился. Новый сервис может прочитать и всю историю с самого начала.

Код примера — в [examples/fastapi](examples/fastapi/README.md). Клиент — `aiokafka`, асинхронный, подходит для FastAPI.

## Минимальный пример

Производитель (producer) пишет событие в топик `task-events`, потребитель (consumer) из группы `analytics` читает его. Нужен запущенный брокер Kafka (в примере — на порту 9096).

```python
import asyncio
import json

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

BOOTSTRAP = 'localhost:9096'


async def main():
    producer = AIOKafkaProducer(
        bootstrap_servers=BOOTSTRAP,
        value_serializer=lambda value: json.dumps(value, ensure_ascii=False).encode(),
    )
    await producer.start()
    event = {'type': 'task.created', 'task': {'id': 1, 'title': 'Сдать отчёт', 'owner_id': 1}}
    await producer.send_and_wait('task-events', key=b'1', value=event)
    await producer.stop()

    consumer = AIOKafkaConsumer(
        'task-events', bootstrap_servers=BOOTSTRAP, group_id='analytics', auto_offset_reset='earliest',
    )
    await consumer.start()
    message = await consumer.getone()
    print(message.offset, json.loads(message.value))
    # 0 {'type': 'task.created', 'task': {'id': 1, 'title': 'Сдать отчёт', 'owner_id': 1}}
    await consumer.stop()


asyncio.run(main())
```

## Как это работает

Установка клиента:

```bash
pip install aiokafka
```

### Два сервиса из примера

В [examples/fastapi](examples/fastapi/README.md) сервис задач (порт 8010) публикует события, а сервис аналитики (порт 8011) считает по ним статистику:

```bash
curl -X POST localhost:8010/tasks -H 'Content-Type: application/json' -d '{"title": "Сдать отчёт", "owner_id": 1}'
curl -X POST localhost:8010/tasks -H 'Content-Type: application/json' -d '{"title": "Купить хлеб", "owner_id": 1}'
curl -X POST localhost:8010/tasks -H 'Content-Type: application/json' -d '{"title": "Починить кран", "owner_id": 2}'
curl -X POST localhost:8010/tasks/1/done

curl localhost:8011/stats
# {"1":{"created":2,"done":1},"2":{"created":1,"done":0}}
```

Сервис задач ничего не знает об аналитике: он только пишет события в топик `task-events`.

### Производитель: публикуем событие

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

### Ключ и партиции

Топик разделён на **партиции** — независимые журналы. В примере их три (`KAFKA_NUM_PARTITIONS: 3`). Kafka выбирает партицию по хэшу ключа, поэтому все события пользователя 1 попадают в одну партицию:

```text
task.created, партиция 0, смещение 0    ← пользователь 1
task.created, партиция 0, смещение 1    ← пользователь 1
task.created, партиция 2, смещение 0    ← пользователь 2
task.done,    партиция 0, смещение 2    ← пользователь 1
```

Порядок Kafka гарантирует **только внутри партиции**. Благодаря ключу «создана» у задачи пользователя 1 никогда не обгонит «выполнена». Без ключа события разошлись бы по разным партициям, и потребитель мог бы получить их в другом порядке.

**Смещение** (offset) — номер события внутри партиции. Потребитель запоминает смещение, до которого дочитал.

### Потребитель: читаем в фоне

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

### Перечитать историю

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

- Нет ключа там, где важен порядок → события одной сущности попадают в разные партиции, и «выполнена» приходит раньше «создана» → передавать ключ (`key=task['owner_id']`), чтобы события одной сущности шли в одну партицию.
- Автоматическая фиксация смещений (`enable_auto_commit=True`) → смещение фиксируется до обработки, при падении посередине событие теряется → отключить автофиксацию и вызывать `commit()` после обработки.
- Неидемпотентная обработка → после перебалансировки группы или падения событие приходит повторно, счётчик `+1` завышает статистику → запоминать обработанные id событий или делать операции идемпотентными.
- Потребителей в группе больше, чем партиций → лишние потребители простаивают без партиций → помнить, что число партиций — потолок параллелизма группы, и заложить его заранее.
- Событие отправлено, а транзакция в базе откатилась (или задача сохранена, а событие не ушло) → данные сервисов расходятся → паттерн Outbox: событие сохраняется в таблицу той же транзакцией, а отдельный процесс публикует его в Kafka.

## Когда не использовать

Если событие нужно обработать ровно одному воркеру и забыть (отправить письмо, пересчитать отчёт), Kafka избыточна: придётся следить за партициями, группами и смещениями. Для таких задач проще классическая очередь — [RabbitMQ](../rabbitmq/README.md) или [NATS](../nats/README.md): сообщение подтвердили, оно удалилось.

Kafka не подходит и там, где сервису нужен ответ прямо сейчас: запрос «кто владелец задачи 1» — это обычный HTTP-вызов через [HTTPX](../../httpx/basics.md), а не событие в журнале. Kafka окупается, когда одно событие читают несколько независимых потребителей, важен порядок внутри сущности или нужна возможность перечитать историю.

## Связанные темы

- [Партиции и группы потребителей наглядно](partitions_visual.md)
- [Apache Kafka: основные понятия](README.md)
- [Kafka изнутри: надёжность и хранение](internals.md)
- [Простые примеры Kafka](examples/simple/README.md)
- [NATS](../nats/README.md) — более лёгкая альтернатива для событий
- [Брокеры сообщений: гарантии доставки](../README.md)
