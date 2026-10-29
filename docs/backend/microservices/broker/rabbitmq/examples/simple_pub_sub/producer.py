"""
Producer для Pub/Sub паттерна.
Отправляет событие user_registered всем подписчикам через FANOUT exchange.
"""

import asyncio
import json
import sys
import aio_pika
from datetime import datetime

EXCHANGE = "user_events"
RABBIT_URL = "amqp://guest:guest@localhost:5672/"


async def publish_event(exchange: aio_pika.Exchange, event_type: str, user_id: int) -> None:
    """Публикует событие в exchange"""
    event = {
        "event": event_type,
        "user_id": user_id,
        "timestamp": datetime.now().isoformat()
    }

    try:
        # Отправляем сообщение в exchange RabbitMQ:
        # delivery_mode=aio_pika.DeliveryMode.PERSISTENT - сохраняет сообщение на диск
        # content_type="application/json" - указывает тип содержимого сообщения
        # FANOUT игнорирует routing_key (потому что рассылка идёт всем подписчикам)
        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(event).encode(),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key="",
        )
        print(f"Событие '{event_type}' отправлено для user_id={user_id}")
    except Exception as e:
        print(f"Ошибка при публикации события: {e}")
        raise


async def main():
    """Основная функция producer для Pub/Sub"""
    print(f"Подключение к RabbitMQ: {RABBIT_URL}")

    try:
        # Устанавливаем соединение с автоматическим переподключением (10 секунд таймаут)
        connection = await aio_pika.connect_robust(
            RABBIT_URL,
            timeout=10,
        )
        print("Соединение установлено")

        async with connection:
            channel = await connection.channel()

            # Объявляем обменник с типом FANOUT
            # type=FANOUT - рассылает всем подписчикам
            # durable=True - переживёт перезагрузку RabbitMQ
            exchange = await channel.declare_exchange(
                EXCHANGE,
                type=aio_pika.ExchangeType.FANOUT,
                durable=True,
            )
            print(f"Exchange '{EXCHANGE}' (FANOUT) готов")

            # Публикуем несколько событий для демонстрации
            print("Публикация событий...")

            events = [
                ("user_registered", 123),
                ("user_registered", 456),
                ("user_registered", 789),
            ]

            for event_type, user_id in events:
                await publish_event(exchange, event_type, user_id)
                # Небольшая пауза между событиями
                await asyncio.sleep(0.5)

            print(f"Все события отправлены ({len(events)} шт.)")
            print(" Все подключённые consumers получат эти события")

    except aio_pika.exceptions.AMQPConnectionError as e:
        print(f"Ошибка подключения к RabbitMQ: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())