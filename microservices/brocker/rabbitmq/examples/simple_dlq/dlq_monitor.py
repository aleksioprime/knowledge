"""
DLQ Monitor - мониторит Dead Letter Queue.
Показывает сообщения, которые не смогли быть обработаны.
"""

import asyncio
import json
import sys
import aio_pika
from datetime import datetime

QUEUE_DLQ = "payments_dlq"
RABBIT_URL = "amqp://guest:guest@localhost:5672/"


async def process_dead_letter(data: dict, message: aio_pika.IncomingMessage) -> None:
    """Обрабатывает сообщение из DLQ"""
    payment_id = data.get('payment_id')
    amount = data.get('amount', 0)
    user_id = data.get('user_id')
    timestamp = data.get('timestamp', 'unknown')

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] DEAD LETTER")
    print(f"ID платежа: {payment_id}")
    print(f"ID пользователя: {user_id}")
    print(f"Сумма: {amount}")
    print(f"Время отправки: {timestamp}")

    # Информация о причине попадания в DLQ
    if amount > 10000:
        print(f"  - причина: Превышен лимит (макс. 10000)")
    elif amount <= 0:
        print(f"  - причина: Некорректная сумма")
    else:
        print(f"  - причина: Неизвестная ошибка")

    # Здесь можно добавить:
    # - Отправку уведомления администратору
    # - Логирование в систему мониторинга
    # - Попытку ручной обработки
    # - Сохранение в отдельную БД для анализа

    print(f"Требуется ручная проверка!")


async def callback(message: aio_pika.IncomingMessage) -> None:
    """Обработчик сообщений из DLQ"""
    async with message.process():
        try:
            # Декодируем JSON из сообщения
            data = json.loads(message.body.decode())
            # Обрабатываем сообщение из DLQ
            await process_dead_letter(data, message)
        except json.JSONDecodeError as e:
            print(f"Ошибка декодирования JSON: {e}")
        except Exception as e:
            print(f"Ошибка обработки сообщения: {e}")
            raise


async def main():
    """Основная функция DLQ monitor."""
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

            # Объявляем DLQ очередь
            dlq_queue = await channel.declare_queue(QUEUE_DLQ, durable=True)
            print(f"DLQ очередь '{QUEUE_DLQ}' готова")

            # Проверяем количество сообщений в DLQ
            message_count = dlq_queue.declaration_result.message_count
            if message_count > 0:
                print(f"В DLQ уже есть {message_count} сообщений(е)!")

            print("DLQ Monitor запущен... (Ctrl+C для выхода)")

            # Начинаем слушать DLQ
            await dlq_queue.consume(callback)

            # Держим соединение открытым
            await asyncio.Future()

    except aio_pika.exceptions.AMQPConnectionError as e:
        print(f"Ошибка подключения к RabbitMQ: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("DLQ Monitor остановлен")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
