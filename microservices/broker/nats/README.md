# NATS

Когда в «Задачнике» создаётся задача, об этом хотят знать сразу несколько сервисов: аналитика, уведомления, поиск. Вызывать каждый по HTTP значит связать их жёстко: сервис задач должен знать адреса всех и ждать, пока ответят. NATS — лёгкий брокер сообщений: сервис задач публикует событие `tasks.created`, а кому оно нужно, тот подписывается. Сервер — один бинарный файл на несколько мегабайт, задержки — доли миллисекунды.

```bash
docker run -d --name nats -p 4222:4222 nats:2.10 -js   # -js включает JetStream
pip install nats-py
```

## Минимальный пример

```python
import asyncio
import json

import nats


async def main():
    nc = await nats.connect('nats://localhost:4222')

    async def on_created(msg):
        print('аналитика получила', msg.subject, json.loads(msg.data))

    await nc.subscribe('tasks.created', cb=on_created)
    await nc.publish('tasks.created', json.dumps({'id': 42, 'title': 'Сдать отчёт'}).encode())

    await nc.flush()
    await asyncio.sleep(0.2)
    await nc.close()


asyncio.run(main())
# аналитика получила tasks.created {'id': 42, 'title': 'Сдать отчёт'}
```

## Как это работает

Сообщения отправляются на **тему** (subject) — строку с точками: `tasks.created`, `tasks.done`, `users.created`. Очередей и обменников, как в RabbitMQ, создавать не нужно: тема существует, пока на неё кто-то подписан.

Подписываться можно по шаблону:

- `*` — ровно одно слово: `tasks.*` получит `tasks.created` и `tasks.done`, но не `users.created`;
- `>` — одно и больше слов в конце: `tasks.>` получит и `tasks.created`, и `tasks.comments.added`.

```python
await nc.subscribe('tasks.*', cb=audit)

await nc.publish('tasks.created', ...)  # получит
await nc.publish('tasks.done', ...)     # получит
await nc.publish('users.created', ...)  # не получит
```

Сообщение — просто байты. Формат (JSON, Protobuf) выбирает приложение.

## Три режима

**Pub/Sub** — каждое сообщение получают **все** подписчики темы. Пример выше.

**Группы очередей** — несколько копий одного сервиса делят сообщения между собой: каждое сообщение достаётся **одному** члену группы. Так масштабируют обработчики без настройки балансировщика:

```python
for name in ['worker-1', 'worker-2', 'worker-3']:
    await nc.subscribe('emails.send', queue='email-workers', cb=handler)

for i in range(30):
    await nc.publish('emails.send', f'письмо {i}'.encode())
# распределение: {'worker-1': 14, 'worker-2': 12, 'worker-3': 4}, всего 30
```

Распределение случайное, но каждое письмо обработано ровно одним воркером.

**Запрос-ответ** — как HTTP-вызов, только через брокер. Отправителю не нужно знать адрес сервиса, а копии сервиса автоматически делят запросы:

```python
async def users_service(msg):
    user_id = int(msg.data)
    await msg.respond(json.dumps({'id': user_id, 'name': 'Анна'}).encode())


await nc.subscribe('users.get', cb=users_service)

reply = await nc.request('users.get', b'1', timeout=1)
json.loads(reply.data)  # {'id': 1, 'name': 'Анна'}
```

Если на тему никто не подписан, ответ приходит сразу, без ожидания таймаута:

```python
await nc.request('billing.get', b'1', timeout=1)
# NoRespondersError: nats: no responders available for request
```

А если сервис есть, но не успел — `TimeoutError: nats: timeout`.

## JetStream: сообщения, которые не теряются

Обычный NATS ничего не хранит: сообщение получают те, кто подписан **в момент публикации**.

```python
await nc.publish('tasks.created', b'{"id": 1}')
await nc.subscribe('tasks.created', cb=late)
# опоздавший подписчик получил: 0
```

Если аналитика перезапускалась и пропустила события, они потеряны. Для таких случаев есть **JetStream** — встроенное хранилище. Поток (stream) сохраняет сообщения на выбранные темы, а потребитель читает их в своём темпе и подтверждает:

```python
js = nc.jetstream()
await js.add_stream(name='TASKS', subjects=['tasks.>'])

ack = await js.publish('tasks.created', json.dumps({'id': 42}).encode())
# сохранено: TASKS 1  — имя потока и номер сообщения

subscription = await js.pull_subscribe('tasks.>', durable='analytics')
for msg in await subscription.fetch(10, timeout=1):
    print('аналитика прочитала', msg.subject, msg.metadata.sequence.stream)
    await msg.ack()
# аналитика прочитала tasks.created 1
# аналитика прочитала tasks.done 2
```

`durable='analytics'` — именованный потребитель: сервер помнит, до какого сообщения он дочитал. После перезапуска аналитика продолжит с того же места, а подтверждённые сообщения повторно не получит. Если не вызвать `ack()`, сообщение придёт снова — это гарантия «хотя бы один раз».

## NATS, RabbitMQ или Kafka

| | NATS | [RabbitMQ](../rabbitmq/README.md) | [Kafka](../kafka/README.md) |
|---|---|---|---|
| Главная сила | простота, скорость, запрос-ответ | гибкая маршрутизация, классические очереди | журнал событий, перечитывание, огромные потоки |
| Хранение | только с JetStream | очереди до подтверждения | всегда, по сроку или объёму |
| Эксплуатация | один бинарный файл | средняя сложность | сложная |

## Частые ошибки

- **Обычный callback вместо корутины.** `nc.subscribe('tasks.created', cb=lambda m: ...)` упадёт с `nats: must use coroutine for subscriptions`. Обработчик должен быть `async def`.
- **Ждать доставки без JetStream.** Базовый NATS работает по принципу «не больше одного раза»: нет подписчика или он упал — сообщение потеряно.
- **Выход до отправки.** `publish` кладёт сообщение в буфер клиента. Если сразу закрыть программу, оно может не уйти. Вызывайте `await nc.flush()` или `await nc.drain()` перед выходом.
- **Тяжёлая работа в обработчике.** Обработчики одной подписки вызываются по очереди: долгая обработка задерживает следующие сообщения. Выносите работу в отдельные задачи или используйте группу очередей.

## Связанные темы

- [Брокеры сообщений: общие понятия](../README.md)
- [Kafka](../kafka/README.md)
- [RabbitMQ](../rabbitmq/README.md)
