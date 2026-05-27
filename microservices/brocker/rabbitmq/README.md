# Работа с RabbitMQ

## Терминология

RabbitMQ — это брокер сообщений с открытым исходным кодом (message broker), написанный на языке Erlang. Его основная задача — принимать, хранить и доставлять сообщения между различными приложениями или компонентами одного приложения.

Ключевые концепции и компоненты:
- Сообщения (Messages)
    Сообщение — это блок информации, который отправляется от производителя (producer) к потребителю(consumer). Сообщение состоит из:
    - Тела (Body): Сами данные, которые нужно передать (например, JSON-объект, XML, бинарные данные).
    - Заголовков (Headers): Произвольные атрибуты, такие как тип контента, кодировка, ID корреляции (для RPC), ID ответа и т.д.
    - Свойств (Properties): Метаданные сообщения (например, приоритет, время жизни, флаг персистентности)

- Производители (Producers)
    Производитель — это приложение, которое создает сообщения и отправляет их в RabbitMQ. Производитель не знает, кто будет потреблять сообщение или куда оно в конечном итоге попадет. Он просто "публикует" его.

- Потребители (Consumers)
    Потребитель — это приложение, которое подключается к RabbitMQ, подписывается на очередь и получает сообщения для обработки. Потребитель может быть один или их может быть много.

- Очереди (Queues)
    Очередь — это буфер, который хранит сообщения, пока они не будут забраны потребителями. Это центральная часть RabbitMQ, своего рода почтовый ящик. Сообщения поступают в очередь и ожидают обработки. Очереди могут быть:
    - Надежными (Durable): Сообщения сохраняются на диске и не теряются при перезагрузке RabbitMQ.
    - Эксклюзивными (Exclusive): Доступны только для одного соединения и удаляются при его закрытии. Идеально подходят для RPC-ответов.
    - Автоматически удаляемыми (Auto-delete): Удаляются, когда от них отписывается последний потребитель.

- Обменники (Exchanges)
    Обменник — это компонент RabbitMQ, который принимает сообщения от производителей и маршрутизирует их в одну или несколько очередей. Производитель отправляет сообщение в обменник, а не напрямую в очередь. Это позволяет гибко управлять маршрутизацией.


## Основные команды RabbitMQ:

### Подключение:

- `connection = await aio_pika.connect_robust(RABBIT_URL)` - установка надёжного соединения по указанному URL (автоматически пытается переподключиться в случае разрыва и пересоздаёт каналы/очереди/консьюмеров).
  Далее в соединении нужно работать через контекстный менеджер:
  ```python
  async with connection:
    # Создание канала подключения
    channel = await connection.channel()
  ```
- `await channel.set_qos(prefetch_count=1)` - потребитель будет брать не более 1 сообщения из очереди за раз, пока оно не будет обработано

### Объявление очереди:

- `queue = await channel.declare_queue("tasks")` - простое объявление, аовторный вызов не создаёт новую очередь
- `queue = await channel.declare_queue("tasks", durable=True)` - очередь cохраняется после перезапуска RabbitMQ
- `queue = await channel.declare_queue("temp", auto_delete=True)` - очередь удаляется, когда перестают использовать
- дополнительные аргументы (TTL, DLQ, etc.):
  ```python
  queue = await channel.declare_queue(
    "events",
    arguments={
        "x-message-ttl": 60000,  # TTL в мс на очередь
        "x-dead-letter-exchange": "dlx",
        "x-dead-letter-routing-key": "events.dlq",
      }
  )
  ```

### Чтение сообщений:

- `await queue.consume(on_message)` - основной способ чтения сообщений через callback
  ```python
  # callback с автоматической обработкой
  async def on_message(message: aio_pika.IncomingMessage):
    # контекстный менеджер автоматически отправляет ack (подтверждение чтения) при выходе
    async with message.process():
        print(message.body)
  ```
  ```python
  # ручная обработка
  try:
      ...
      # положительное подтверждение обработки
      await message.ack()
  except ValueError as e:
      # отрицательное подтверждение обработки c выбрасывания сообщения в DLQ
      await message.nack(requeue=False)
  except Exception:
      # отрицательное подтверждение обработки c возвращением в очередь
      await message.nack(requeue=True)
      raise
  ```

### Работа с обменниками

- `exchange = await channel.declare_exchange("logs", type=ExchangeType.DIRECT)` - объявление обменника

  Типы обменника:
  - ExchangeType.DIRECT - маршрутизация по точному совпадению routing_key
  - ExchangeType.FANOUT - отправляет сообщения во все очереди, привязанные к этому обменнику
  - ExchangeType.TOPIC - маршрутизация по шаблонам (например, Маршрутизация по шаблонам: user.*, order.#, log.error.*)
  - ExchangeType.HEADERS - маршрутизация по заголовкам (headers)

  Дополнительные параметры:
  - passive=True - не создаёт exchange, а только проверяет, что он существует
  - durable=True - exchange будет переживать перезапуск RabbitMQ
  - auto_delete=True - удалить exchange автоматически, когда все очереди отвязаны и нет активных каналов, использующих его
  - arguments - словарь дополнительных аргументов AMQP

- `default_exchange = channel.default_exchange` - получение ссылки на обменник по-умолчанию (обменник отправляет сообщения в очередь, указанную в routing_key)
  ```python
  await default_exchange.publish(
      Message(b"hi"),
      routing_key="queue_name"
  )
  ```
  Каждая очередь автоматически привязывается к обмену по умолчанию с ключом маршрутизации, который совпадает с именем очереди

### Bindings (связывание очередей и обменников)

- `await queue.bind(exchange, routing_key="user.created")` - создать привязку очереди к обменника
- `await queue.unbind(exchange, routing_key="user.created")` - удалить привязку очереди от обменника

### Message: создание и свойства

```python
message = Message(
    body=b"hello",
    delivery_mode=DeliveryMode.PERSISTENT,
    headers={"service": "billing"},
    content_type="application/json",
)
```

Параметры:
- body: данные сообщения
- headers: произвольные метаданные
- content_type: MIME-тип
- reply_to: очередь ответа (для RPC)
- correlation_id: ID вызова (для RPC)
- expiration: TTL сообщения
- delivery_mode=2: хранить на диске

Пример TTL-сообщения: `Message(body=b"data", expiration=5000)`


## Советы

- Все создаваемые очереди должны быть долговременными (англ. durable). То есть в настройках очереди должен стоять флаг durable. Это позволит не потерять данные при перезагрузке сервера.
- Сообщения должны отправляться с delivery_mode=2 (то есть persistent). Этот параметр указывает серверу сохранять полученное сообщение на диск.
- Если отправка сообщения не удалась, его лучше записать во временное хранилище, а через некоторое время попытаться отправить заново.
- В заголовках сообщений обязательно передавать параметр X-Request-Id — тот самый, который генерируется при любом входящем HTTP-запросе от пользователя и прокидывается во все зависимые запросы.
- Не должно быть очередей, которые долго не разгребаются и бесконтрольно растут. Очереди должны мониториться на возраст самого старого сообщения: нужно алертить, если этот возраст больше допустимого.

## Cценарий Remote Procedure Call (RPC)

RPC позволяет одному сервису (Клиенту) вызывать функцию или процедуру в другом сервисе (Сервере), как если бы эта функция выполнялась локально, но на самом деле вызов происходит через сеть с помощью обмена сообщениями

1. Подготовка
    - Cервис "Исполнитель" (Server) подключается к RabbitMQ, cоздаёт очередь запросов (например, `rpc_queue`), начинает слушать её, ожидая входящие задания.
    - Сервис "Заказчик" (Client): подключается к RabbitMQ, создаёт личную временную очередь (`callback queue`) для получения ответов (в RabbitMQ такие очереди обычно анонимные и удаляются автоматически), начинает слушать её, ожидая ответы от сервера

2. Клиент отправляет вопрос
    - Клиент формирует запрос, например, «Верни имя пользователя по ID = 33».
    - Генерируется уникальный `correlation_id`. Он нужен, чтобы понять, какое сообщение является ответом именно на его конкретный запрос.
    - Сообщение отправляется в очередь rpc_queue. В сообщение добавляются два важных свойства: `correlation_id` — идентификатор запроса, `reply_to` — название личной очереди, куда прислать ответ
    - Клиент начинает ждать ответ в своей `callback queue`

3. Сервер получает запрос и выполняет работу
    - RabbitMQ доставляет запрос серверу, который читает сообщение, извлекает `correlation_id` и `reply_to`.
    - Далее сервер выполняет задачу, например, обращается к базе данных, и затем формирует ответ, указывая тот же `correlation_id` и тело ответа (например, имя пользователя)
    - Ответ отправляется в очередь, указанную в `reply_to`.
    - Сервер подтверждает обработку запроса (ACK) → сообщение удаляется из `rpc_queue`.

4. Клиент получает ответ
    - RabbitMQ помещает ответ в `callback queue` клиента.
    - Клиент получает сообщение и сравнивает `correlation_id` ответа с тем, что он отправлял: если совпадает — это ответ на его конкретный запрос, если нет — игнорирует (в случае нескольких параллельных RPC-вызовов)
    - Клиент обрабатывает полученный результат и отправляет подтверждение (ACK), а RabbitMQ удаляет сообщение из `callback queue`.

## Библиотека

Установка библиотеки для работы с RabbitMQ:
```sh
# установка синхронной библиотеки
pip install pika
# установка асинхронной библиотеки
pip install aio-pika
```

## Контейнеры

Запуск в `docker`:
```sh
docker run -d \
  --name rabbit \
  --platform linux/arm64 \
  -p 5672:5672 \
  -p 15672:15672 \
  -e RABBITMQ_DEFAULT_USER=guest \
  -e RABBITMQ_DEFAULT_PASS=guest \
  rabbitmq:4.1.1-management
```

Запуск в `docker-compose.yaml`:
```yaml
services:
  rabbitmq:
    image: rabbitmq:4.1.1-management
    container_name: rabbitmq
    restart: unless-stopped
    platform: linux/amd64

    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASS: guest
      RABBITMQ_DEFAULT_VHOST: "/"

      TZ: Europe/Moscow

    ports:
      - "5672:5672"     # AMQP port
      - "15672:15672"   # Management UI

    volumes:
      - rabbitmq_data:/var/lib/rabbitmq      # persisted queues
      - rabbitmq_log:/var/log/rabbitmq       # logs (опционально)

    healthcheck:
      test: ["CMD-SHELL", "rabbitmq-diagnostics -q check_running"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s

    # Опционально: ограничиваем ресурсы, чтобы Rabbit не съел всю RAM
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 128M

volumes:
  rabbitmq_data:
  rabbitmq_log:
```
## Содержание

- [Пример: simple_queue (точка-точка)](examples/simple_queue/README.md)
- [Пример: simple_pub_sub (fanout)](examples/simple_pub_sub/README.md)
- [Пример: simple_topic (topic exchange)](examples/simple_topic/README.md)
- [Пример: simple_rpc (RPC pattern)](examples/simple_rpc/README.md)
- [Пример: simple_delay (отложенная доставка)](examples/simple_delay/README.md)
- [Пример: simple_dlq (Dead Letter Queue)](examples/simple_dlq/README.md)
- [Пример: fastapi_rpc (интеграция с FastAPI)](examples/fastapi_rpc/README.md)
