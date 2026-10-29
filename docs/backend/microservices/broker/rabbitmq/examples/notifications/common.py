"""Настройки и топология брокера, общие для API, воркера и планировщика."""

import os

import aio_pika

RABBIT_URL = os.getenv('RABBIT_URL', 'amqp://notify:notify@localhost:45672/')
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://notify:notify@localhost:45433/notify')
SMTP_HOST = os.getenv('SMTP_HOST', 'localhost')
SMTP_PORT = int(os.getenv('SMTP_PORT', '42025'))

EXCHANGE = 'notifications.events'
QUEUE = 'notifications.send-email'
DLQ = 'notifications.send-email.dlq'
# Своя очередь на каждую ступень: у всех сообщений в очереди одинаковый TTL
RETRY_DELAYS_MS = [2_000, 5_000, 10_000]
MAX_ATTEMPTS = len(RETRY_DELAYS_MS) + 1

# Тип события → категория подписки и обход тихих часов
EVENT_TYPES = {
    'task.assigned': {'category': 'tasks', 'urgent': False},
    'comment.created': {'category': 'comments', 'urgent': False},
    'digest.weekly': {'category': 'digest', 'urgent': False},
}


def routing_key(event_type: str, version: int = 1) -> str:
    """task.assigned → task.v1.assigned: сущность, версия контракта, событие."""
    entity, action = event_type.split('.')
    return f'{entity}.v{version}.{action}'


def retry_queue(attempt: int) -> str:
    return f'{QUEUE}.retry.{attempt}'


async def declare_topology(channel: aio_pika.abc.AbstractChannel) -> aio_pika.abc.AbstractExchange:
    exchange = await channel.declare_exchange(EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True)

    await channel.declare_queue(DLQ, durable=True)

    queue = await channel.declare_queue(
        QUEUE,
        durable=True,
        arguments={
            'x-queue-type': 'quorum',
            # страховка от сообщения, на котором воркер падает целиком и не успевает ответить
            'x-delivery-limit': 10,
            'x-dead-letter-exchange': '',
            'x-dead-letter-routing-key': DLQ,
        },
    )
    await queue.bind(exchange, routing_key='*.v1.*')

    for attempt, delay in enumerate(RETRY_DELAYS_MS, start=1):
        # Сообщение лежит delay мс, «умирает» и через DLX возвращается в основную очередь
        await channel.declare_queue(
            retry_queue(attempt),
            durable=True,
            arguments={
                'x-message-ttl': delay,
                'x-dead-letter-exchange': '',
                'x-dead-letter-routing-key': QUEUE,
            },
        )
    return exchange
