"""
Producer отправляет задачи на обработку видео в очередь RabbitMQ
"""
import aio_pika
import asyncio
import json
import sys
from datetime import datetime

RABBIT_URL = "amqp://guest:guest@localhost:5672/"
QUEUE = "video_tasks"


async def send_task(channel: aio_pika.Channel, video_id: int) -> None:
    """Отправляет одну задачу в очередь"""
    message = {
        "video_id": video_id,
        "path": f"/uploads/video_{video_id}.mp4",
        "timestamp": datetime.now().isoformat()
    }

    try:
        # Отправляем сообщение в очередь RabbitMQ:
        # delivery_mode=PERSISTENT - сохраняет сообщение на диск
        # content_type="application/json" - указывает тип содержимого
        # routing_key=QUEUE - указывает очередь назначения
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(message).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
            ),
            routing_key=QUEUE,
        )
        print(f"Задача отправлена: video_id={video_id}")
    except Exception as e:
        print(f"Ошибка при отправке задачи {video_id}: {e}")
        raise


async def main():
    """Основная функция producer"""
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
            await channel.declare_queue(QUEUE, durable=True)
            print(f"Очередь '{QUEUE}' готова")

            # Отправляем задачи
            print("\nОтправка задач...")
            for video_id in range(1, 6):
                # Отправляем задачу с video_id
                await send_task(channel, video_id)
                # Небольшая пауза между отправками
                await asyncio.sleep(0.1)

            print(f"\nВсе задачи отправлены (5 шт.)")

    except aio_pika.exceptions.AMQPConnectionError as e:
        print(f"Ошибка подключения к RabbitMQ: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())