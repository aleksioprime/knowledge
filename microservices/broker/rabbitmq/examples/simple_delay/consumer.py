"""
Consumer для Delayed Messages паттерна.
Обрабатывает уведомления, которые были отложены producer'ом.
"""

import asyncio
import json
import sys
import aio_pika
from datetime import datetime, timedelta

QUEUE_MAIN = "main_queue"
RABBIT_URL = "amqp://guest:guest@localhost:5672/"


async def process_reminder(data: dict) -> None:
    """Обрабатывает отложенное уведомление"""
    user_id = data.get('user_id')
    sent_at = data.get('sent_at', 'unknown')
    delay_seconds = data.get('delay_seconds', 0)

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] НАПОМИНАНИЕ")
    print(f"ID пользователя: {user_id}")
    print(f"Отправлено: {sent_at}")
    print(f"Задержка: {delay_seconds}s")

    # Вычисляем фактическую задержку
    try:
        if sent_at != 'unknown':
            sent_time = datetime.fromisoformat(sent_at)
            actual_delay = (datetime.now() - sent_time).total_seconds()
            print(f"Фактическая задержка: {actual_delay:.2f}s")
    except:
        pass

    # Имитация обработки
    print(f"Отправляем напоминание пользователю {user_id}...")
    await asyncio.sleep(0.5)
    print(f"Напоминание успешно отправлено")


async def callback(message: aio_pika.IncomingMessage) -> None:
    """Обработчик входящих отложенных сообщений"""
    async with message.process():
        try:
            # Декодируем JSON из тела сообщения
            data = json.loads(message.body.decode())
            # Обрабатываем уведомление
            await process_reminder(data)
        except json.JSONDecodeError as e:
            print(f"Ошибка декодирования JSON: {e}")
        except Exception as e:
            print(f"Ошибка обработки сообщения: {e}")
            raise


async def main():
    """Основная функция consumer для delayed messages."""
    print(f"Подключение к RabbitMQ: {RABBIT_URL}")

    try:
        # Устанавливаем соединение с автоматическим переподключением (10 секунд таймаут)
        connection = await aio_pika.connect_robust(RABBIT_URL, timeout=10)
        print("Соединение установлено")

        async with connection:
            channel = await connection.channel()

            # Объявляем основную очередь (должна совпадать с producer)
            queue = await channel.declare_queue(QUEUE_MAIN, durable=True)
            print(f"Очередь '{QUEUE_MAIN}' готова")

            print("Ожидание отложенных уведомлений... (Ctrl+C для выхода)\n")

            # Начинаем слушать очередь
            await queue.consume(callback)

            # Держим соединение открытым
            await asyncio.Future()

    except aio_pika.exceptions.AMQPConnectionError as e:
        print(f"Ошибка подключения к RabbitMQ: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("Consumer остановлен")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())