"""
Producer для Dead Letter Queue (DLQ) паттерна.
Отправляет платежи на обработку, включая невалидные для демонстрации DLQ.
"""

import asyncio
import json
import sys
import aio_pika
from datetime import datetime

RABBIT_URL = "amqp://guest:guest@localhost:5672/"

QUEUE = "payments"          # Основная очередь
DLX = "payments_dlx"        # Dead Letter Exchange (обменник для мёртвых писем)


async def send_payment(channel: aio_pika.Channel, payment_id: int, amount: float, user_id: int) -> None:
    """Отправляет платёж на обработку"""
    payment = {
        "payment_id": payment_id,
        "amount": amount,
        "user_id": user_id,
        "timestamp": datetime.now().isoformat()
    }

    try:
        # Отправляем сообщение в очередь RabbitMQ:
        # delivery_mode=PERSISTENT - сохраняет сообщение на диск
        # content_type="application/json" - указывает тип содержимого
        # routing_key=QUEUE - указывает очередь назначения
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(payment).encode(),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=QUEUE,
        )

        status = "невалидный" if amount > 10000 or amount <= 0 else "валидный"
        print(f"{status} Платёж #{payment_id}: {amount} ₽ (user {user_id})")
    except Exception as e:
        print(f"Ошибка при отправке платежа: {e}")
        raise


async def main():
    """Основная функция producer для отправки платежей."""
    print(f"Подключение к RabbitMQ: {RABBIT_URL}")

    try:
        # Устанавливаем соединение с автоматическим переподключением (10 секунд таймаут)
        connection = await aio_pika.connect_robust(
            RABBIT_URL,
            timeout=10,
        )
        print("Cоединение установлено")

        async with connection:
            channel = await connection.channel()

            # Объявляем очередь (должна совпадать с consumer)
            # x-dead-letter-exchange - куда отправлять отклонённые сообщения
            await channel.declare_queue(
                QUEUE,
                durable=True,
                arguments={"x-dead-letter-exchange": DLX}
            )
            print(f"Очередь '{QUEUE}' готова")

            # Отправляем разные платежи для демонстрации
            print("Отправка платежей...")
            payments = [
                (1001, 5000, 123),    # Валидный
                (1002, 15000, 456),   # Превышает лимит -> DLQ
                (1003, 3500, 789),    # Валидный
                (1004, -100, 111),    # Отрицательная сумма -> DLQ
                (1005, 8000, 222),    # Валидный
                (1006, 20000, 333),   # Превышает лимит -> DLQ
            ]

            for payment_id, amount, user_id in payments:
                await send_payment(channel, payment_id, amount, user_id)
                await asyncio.sleep(0.5)

            print(f"Все платежи отправлены ({len(payments)} шт.)")
            print("Невалидные платежи будут отправлены в DLQ")

    except aio_pika.exceptions.AMQPConnectionError as e:
        print(f"Ошибка подключения к RabbitMQ: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
