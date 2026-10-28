"""
Payment Consumer для Topic паттерна.
Получает все сообщения, связанные с платежами (*.payment).
"""

import asyncio
import json
import sys
import aio_pika
from datetime import datetime

EXCHANGE = "logs_topic"
RABBIT_URL = "amqp://guest:guest@localhost:5672/"


async def process_payment_log(routing_key: str, log_data: dict) -> None:
    """Обрабатывает сообщение о событии платежной системы"""
    message = log_data.get('message', '')
    timestamp = log_data.get('timestamp', 'unknown')
    level = routing_key.split('.', 1)[0] if '.' in routing_key else 'unknown'

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] PAYMENT [{level.upper()}]")
    print(f"Сообщение: {message}")
    print(f"Время: {timestamp}")
    print(f"Routing key: {routing_key}")

    # Здесь можно добавить специфичную обработку для платёжной системы
    await asyncio.sleep(0.1)


async def callback(message: aio_pika.IncomingMessage) -> None:
    """Обработчик входящих сообщений о платежах"""
    async with message.process():
        try:
            # Декодируем JSON из тела сообщения
            log_data = json.loads(message.body.decode())
            # Обрабатываем лог платежной системы
            await process_payment_log(message.routing_key, log_data)
        except json.JSONDecodeError as e:
            print(f"Ошибка декодирования JSON: {e}")
        except Exception as e:
            print(f"Ошибка обработки сообщения: {e}")
            raise


async def main():
    """Основная функция payment consumer"""
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

            # Подписываемся на все события платежей (*.payment)
            await queue.bind(exchange, routing_key="*.payment")
            print("Подписка: *.payment (все уровни для платежей)")
            print("Payment Consumer готов к приёму событий... (Ctrl+C для выхода)")

            # Начинаем слушать очередь и обрабатывать сообщения с помощью callback
            await queue.consume(callback)

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
