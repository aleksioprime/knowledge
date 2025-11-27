"""
Consumer (Worker): обрабатывает видео из очереди RabbitMQ
"""
import asyncio
import json
import sys
import aio_pika
from datetime import datetime

RABBIT_URL = "amqp://guest:guest@localhost:5672/"
QUEUE = "video_tasks"


async def process_video(message: dict) -> None:
    """Имитирует обработку видео"""
    video_id = message.get('video_id')
    path = message.get('path')
    timestamp = message.get('timestamp', 'unknown')

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Начало обработки:")
    print(f"ID: {video_id}")
    print(f"Путь: {path}")
    print(f"Создано: {timestamp}")

    try:
        # Имитация долгой операции (обработка видео)
        await asyncio.sleep(2)
        print(f"Видео {video_id} успешно обработано")
    except Exception as e:
        print(f"Ошибка при обработке видео {video_id}: {e}")
        raise


async def callback(message: aio_pika.IncomingMessage) -> None:
    """
    Обработчик входящих сообщений
    """
    async with message.process():
        try:
            payload = json.loads(message.body.decode())
            await process_video(payload)
        except json.JSONDecodeError as e:
            print(f"Ошибка декодирования JSON: {e}")
        except Exception as e:
            print(f"Ошибка обработки сообщения: {e}")
            raise


async def main():
    """Основная функция consumer"""
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

            # Объявляем очередь (durable=True - переживёт перезагрузку RabbitMQ)
            queue = await channel.declare_queue(QUEUE, durable=True)
            print(f"Очередь '{QUEUE}' готова")

            # QoS: worker получает только 1 задачу за раз
            # Новая задача придёт только после завершения текущей
            await channel.set_qos(prefetch_count=1)
            print("QoS настроен (prefetch_count=1)")

            print("\nОжидание задач... (Ctrl+C для выхода)\n")

            # Начинаем слушать очередь и обрабатывать сообщения с помощью callback
            await queue.consume(callback)

            # Держим соединение открытым пока не прервём его вручную
            await asyncio.Future()

    except aio_pika.exceptions.AMQPConnectionError as e:
        print(f"Ошибка подключения к RabbitMQ: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nConsumer остановлен")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())