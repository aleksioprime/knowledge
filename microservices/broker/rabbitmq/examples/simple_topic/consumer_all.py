"""
All Logs Consumer для Topic паттерна.
Получает абсолютно все логи (#).
"""

import asyncio
import json
import sys
import aio_pika
from datetime import datetime

EXCHANGE = "logs_topic"
RABBIT_URL = "amqp://guest:guest@localhost:5672/"


async def process_log(routing_key: str, log_data: dict) -> None:
    """Обрабатывает любое логовое сообщение"""
    message = log_data.get('message', '')
    timestamp = log_data.get('timestamp', 'unknown')

    parts = routing_key.split('.', 1)
    level = parts[0] if len(parts) > 0 else 'unknown'
    service = parts[1] if len(parts) > 1 else 'unknown'

    print(f"[{datetime.now().strftime('%H:%M:%S')}] [{level.upper():7}] {service:12} → {message} ({timestamp})")


async def callback(message: aio_pika.IncomingMessage) -> None:
    """Обработчик входящих сообщений"""
    async with message.process():
        try:
            # Декодируем JSON из тела сообщения
            log_data = json.loads(message.body.decode())
            # Обрабатываем логовое сообщение
            await process_log(message.routing_key, log_data)
        except json.JSONDecodeError as e:
            print(f"Ошибка декодирования JSON: {e}")
        except Exception as e:
            print(f"Ошибка обработки сообщения: {e}")
            raise


async def main():
    """Основная функция all logs consumer"""
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

            # Объявляем TOPIC exchange
            # type=TOPIC - маршрутизация по паттернам
            # durable=True - переживёт перезагрузку RabbitMQ
            exchange = await channel.declare_exchange(
                EXCHANGE,
                type=aio_pika.ExchangeType.TOPIC,
                durable=True,
            )
            print(f"Exchange '{EXCHANGE}' (TOPIC) готов")

            # Создаём эксклюзивную очередь (удалится при отключении consumer)
            # Каждому consumer создаётся своя уникальная очередь
            queue = await channel.declare_queue(
                name="",        # RabbitMQ сгенерирует уникальное имя
                exclusive=True, # Удалится при закрытии соединения
            )
            print(f"Создана эксклюзивная очередь: {queue.name}")

            # Подписываемся на ВСЕ логи (#)
            await queue.bind(exchange, routing_key="#")
            print("Подписка: # (все логи)")
            print("All Logs Consumer готов к приёму всех логов... (Ctrl+C для выхода)")

            # Начинаем слушать очередь и обрабатывать сообщения с помощью callback
            await queue.consume(callback)

            # Держим соединение открытым
            await asyncio.Future()

    except aio_pika.exceptions.AMQPConnectionError as e:
        print(f"Ошибка подключения к RabbitMQ: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("All Logs Consumer остановлен")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
