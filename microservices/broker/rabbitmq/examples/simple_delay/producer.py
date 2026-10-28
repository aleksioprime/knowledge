"""
Producer для Delayed Messages паттерна.
Отправляет уведомления, которые будут обработаны через заданную задержку.
Использует TTL + Dead Letter Exchange (DLX).
"""

import asyncio
import json
import sys
import aio_pika
from datetime import datetime

RABBIT_URL = "amqp://guest:guest@localhost:5672/"

EX_MAIN = "main_exchange"   # Основной exchange
QUEUE_DELAY = "delay_queue" # Delay очередь
QUEUE_MAIN = "main_queue"   # Основная очередь
DELAY_MS = 5000             # Задержка в миллисекундах


async def send_delayed_notification(channel: aio_pika.Channel, user_id: int, delay_sec: int = 5) -> None:
    """Отправляет отложенное уведомление"""
    notification = {
        "event": "send_reminder",
        "user_id": user_id,
        "sent_at": datetime.now().isoformat(),
        "delay_seconds": delay_sec
    }

    try:
        # Отправляем сообщение в delay очередь RabbitMQ:
        # delivery_mode=PERSISTENT - сохраняет сообщение на диск
        # content_type="application/json" - указывает тип содержимого
        # routing_key=QUEUE_DELAY - указывает очередь назначения
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(notification).encode(),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=QUEUE_DELAY,
        )
        print(f"Напоминание для user_id={user_id} отправлено (задержка {delay_sec}с)")
    except Exception as e:
        print(f"Ошибка при отправке уведомления: {e}")
        raise


async def main():
    """Основная функция producer для delayed messages"""
    print(f"Подключение к RabbitMQ: {RABBIT_URL}")

    try:
        # Устанавливаем соединение с автоматическим переподключением (10 секунд таймаут)
        connection = await aio_pika.connect_robust(RABBIT_URL, timeout=10)
        print("Соединение установлено")

        async with connection:
            channel = await connection.channel()

            # Основной exchange для обработки сообщений после задержки
            # type=DIRECT - маршрутизация по точному совпадению routing key
            # durable=True - переживёт перезагрузку RabbitMQ
            main_exchange = await channel.declare_exchange(
                EX_MAIN,
                type=aio_pika.ExchangeType.DIRECT,
                durable=True,
            )
            print(f"Exchange '{EX_MAIN}' готов")

            # Delay очередь с TTL и DLX
            # Сообщение кладётся в QUEUE_DELAY очередь, лежит там заданное время (TTL) и умирает
            # DLX перехватывает "мёртвое" сообщение и перенаправляет его в EX_MAIN c routing_key="notify"
            await channel.declare_queue(
                QUEUE_DELAY,
                durable=True,
                arguments={
                    "x-message-ttl": DELAY_MS,              # Задержка в мс
                    "x-dead-letter-exchange": EX_MAIN,      # Куда отправить после TTL
                    "x-dead-letter-routing-key": "notify"   # Routing key для DLX
                }
            )
            print(f"Delay очередь '{QUEUE_DELAY}' готова (TTL={DELAY_MS}ms)")

            # Основная очередь для обработки
            main_queue = await channel.declare_queue(QUEUE_MAIN, durable=True)
            # Привязываем основную очередь к основному exchange с routing_key "notify"
            await main_queue.bind(main_exchange, routing_key="notify")
            print(f"Main очередь '{QUEUE_MAIN}' готова")

            # Отправляем несколько отложенных уведомлений
            print("Отправка отложенных уведомлений...\n")
            users = [123, 456, 789]

            for user_id in users:
                await send_delayed_notification(channel, user_id, DELAY_MS // 1000)
                await asyncio.sleep(0.5)

            print(f"Все уведомления отправлены ({len(users)} шт.)")
            print(f"Они будут доставлены в очередь '{QUEUE_MAIN}' через {DELAY_MS // 1000} секунд")

    except aio_pika.exceptions.AMQPConnectionError as e:
        print(f"Ошибка подключения к RabbitMQ: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())