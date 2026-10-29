"""
Consumer для Dead Letter Queue (DLQ) паттерна.
Обрабатывает платежи. При ошибке сообщение отправляется в DLQ.
"""

import asyncio
import json
import sys
import aio_pika
from datetime import datetime

RABBIT_URL = "amqp://guest:guest@localhost:5672/"

QUEUE = "payments"          # Основная очередь
DLX = "payments_dlx"        # Dead Letter Exchange (обменник для мёртвых писем)
QUEUE_DLQ = "payments_dlq"  # Dead Letter Queue (очередь мёртвых писем)


async def process_payment(data: dict) -> None:
    """Обрабатывает платёж"""
    payment_id = data.get('payment_id')
    amount = data.get('amount', 0)
    user_id = data.get('user_id')

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ОБРАБОТКА ПЛАТЕЖА")
    print(f"ID платежа: {payment_id}")
    print(f"ID пользователя: {user_id}")
    print(f"Сумма: {amount}")

    # Валидация
    if amount > 10000:
        raise ValueError(f"Слишком большая сумма платежа: {amount}")

    if amount <= 0:
        raise ValueError(f"Некорректная сумма: {amount}")

    # Имитация обработки
    await asyncio.sleep(0.5)
    print(f"Платёж #{payment_id} успешно обработан")


async def callback(message: aio_pika.IncomingMessage) -> None:
    """Обработчик входящих сообщений о платежах"""
    try:
        # Декодируем JSON из сообщения
        data = json.loads(message.body.decode())
        # Обрабатываем платёж
        await process_payment(data)
        # Подтверждаем успешную обработку сообщения
        await message.ack()

    except ValueError as e:
        print(f"Ошибка валидации: {e}")
        print(f"Сообщение отправлено в DLQ")
        # Отправляем сообщение в DLQ, если возникла ошибка валидации
        # requeue - не пытаться повторно обработать
        await message.nack(requeue=False)

    except json.JSONDecodeError as e:
        print(f"Ошибка декодирования JSON: {e}")
        # Отправляем сообщение в DLQ, если возникла ошибка декодирования
        # requeue - не пытаться повторно обработать
        await message.nack(requeue=False)

    except Exception as e:
        print(f"Неожиданная ошибка обработки: {e}")
        # Отправляем сообщение в DLQ при неожиданной ошибке
        # requeue - не пытаться повторно обработать
        await message.nack(requeue=False)


async def main():
    """Основная функция consumer для обработки платежей с DLQ."""
    print(f"Подключение к RabbitMQ: {RABBIT_URL}")

    try:
        # Устанавливаем соединение с автоматическим переподключением (10 секунд таймаут)
        connection = await aio_pika.connect_robust(
            RABBIT_URL,
            timeout=10,
        )
        print("Соединение установлено")

        async with connection:
            # Создаём канал для общения с RabbitMQ
            channel = await connection.channel()

            # Объявляем DLX exchange
            # type=FANOUT - рассылает всем подписчикам
            # durable=True - переживёт перезагрузку RabbitMQ
            dlx = await channel.declare_exchange(
                DLX,
                type=aio_pika.ExchangeType.FANOUT,
                durable=True,
            )
            print(f"DLX exchange '{DLX}' готов")

            # Создаём DLQ очередь
            dlq_queue = await channel.declare_queue(QUEUE_DLQ, durable=True)
            await dlq_queue.bind(dlx)
            print(f"DLQ очередь '{QUEUE_DLQ}' готова")

            # Создаём основную очередь с DLX для обработки платежей
            main_queue = await channel.declare_queue(
                QUEUE,
                durable=True,                               # основная очередь должна быть устойчивой
                arguments={"x-dead-letter-exchange": DLX}   # указываем DLX для основной очереди
            )
            print(f"Main очередь '{QUEUE}' готова (с DLX)")

            # QoS для обработки по одному сообщению
            await channel.set_qos(prefetch_count=1)
            print("Payment Consumer готов к обработке платежей... (Ctrl+C для выхода)")

            # Начинаем слушать очередь
            await main_queue.consume(callback)

            # Держим соединение открытым
            await asyncio.Future()

    except aio_pika.exceptions.AMQPConnectionError as e:
        print(f"Ошибка подключения к RabbitMQ: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("Payment Consumer остановлен")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
