"""
Error Consumer для Topic паттерна.
Получает только сообщения с routing key "error.*" (любые ошибки).
"""

import asyncio
import json
import sys
import aio_pika
from datetime import datetime

EXCHANGE = "logs_topic"
RABBIT_URL = "amqp://guest:guest@localhost:5672/"


async def process_error(routing_key: str, log_data: dict) -> None:
    """Обрабатывает сообщение об ошибке"""
    message = log_data.get('message', '')
    timestamp = log_data.get('timestamp', 'unknown')
    service = routing_key.split('.', 1)[1] if '.' in routing_key else 'unknown'

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] КРИТИЧЕСКАЯ ОШИБКА")
    print(f"Сервис: {service}")
    print(f"Сообщение: {message}")
    print(f"Время: {timestamp}")
    print(f"Routing key: {routing_key}")

    # Здесь можно добавить отправку в систему мониторинга, PagerDuty и т.д.
    await asyncio.sleep(0.1)


async def callback(message: aio_pika.IncomingMessage) -> None:
    """Обработчик входящих сообщений об ошибках"""
    async with message.process():
        try:
            # Декодируем JSON из тела сообщения
            log_data = json.loads(message.body.decode())
            # Обрабатываем сообщение об ошибке
            await process_error(message.routing_key, log_data)
        except json.JSONDecodeError as e:
            print(f"Ошибка декодирования JSON: {e}")
        except Exception as e:
            print(f"Ошибка обработки сообщения: {e}")
            raise


async def main():
    """Основная функция error consumer."""
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

            # Подписываемся на все ошибки (error.*)
            await queue.bind(exchange, routing_key="error.*")
            print("Подписка: error.* (все ошибки)")

            print("Error Consumer готов к приёму ошибок... (Ctrl+C для выхода)")

            # Начинаем слушать очередь и обрабатывать сообщения с помощью callback
            await queue.consume(callback)

            # Держим соединение открытым
            await asyncio.Future()

    except aio_pika.exceptions.AMQPConnectionError as e:
        print(f"Ошибка подключения к RabbitMQ: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("Error Consumer остановлен")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())