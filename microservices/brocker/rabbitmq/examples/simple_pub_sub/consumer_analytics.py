"""
Analytics сервис (Consumer) для Pub/Sub паттерна.
Получает события о регистрации пользователей и сохраняет статистику.
"""

import asyncio
import json
import sys
import aio_pika
from datetime import datetime

EXCHANGE = "user_events"
RABBIT_URL = "amqp://guest:guest@localhost:5672/"


async def save_analytics(user_id: int, timestamp: str) -> None:
    """Имитирует сохранение аналитики по регистрации пользователя"""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Обработка события:")
    print(f"ID пользователя: {user_id}")
    print(f"Время события: {timestamp}")
    print(f"Сохраняем данные в аналитику...")

    # Имитация сохранения в БД
    await asyncio.sleep(0.5)
    print(f"Аналитика по пользователю {user_id} сохранена")


async def callback(message: aio_pika.IncomingMessage) -> None:
    """Обработчик входящих событий"""
    async with message.process():
        try:
            # Разбираем JSON из тела сообщения
            data = json.loads(message.body.decode())
            event_type = data.get('event', 'unknown')
            user_id = data.get('user_id')
            timestamp = data.get('timestamp', 'unknown')

            # Обрабатываем событие регистрации пользователя
            if event_type == 'user_registered' and user_id:
                await save_analytics(user_id, timestamp)
            else:
                print(f"Неизвестное событие: {event_type}")

        except json.JSONDecodeError as e:
            print(f"Ошибка декодирования JSON: {e}")
        except Exception as e:
            print(f"Ошибка обработки сообщения: {e}")
            raise


async def main():
    """Основная функция analytics consumer."""
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

            # Объявляем обменник с типом FANOUT
            # type=FANOUT - рассылает всем подписчикам
            # durable=True - переживёт перезагрузку RabbitMQ
            exchange = await channel.declare_exchange(
                EXCHANGE,
                type=aio_pika.ExchangeType.FANOUT,
                durable=True,
            )
            print(f"Exchange '{EXCHANGE}' (FANOUT) готов")

            # Создаём эксклюзивную очередь (удалится при отключении)
            # Каждому consumer создаётся своя уникальная очередь
            queue = await channel.declare_queue(
                name="",        # RabbitMQ сгенерирует уникальное имя
                exclusive=True, # Удалится при закрытии соединения
            )
            print(f"Создана эксклюзивная очередь: {queue.name}")

            # Привязываем очередь к exchange
            await queue.bind(exchange)
            print(f"Очередь привязана к exchange '{EXCHANGE}'")
            print("\nAnalytics сервис готов к приёму событий... (Ctrl+C для выхода)\n")

            # Начинаем слушать очередь и обрабатывать сообщения с помощью callback
            await queue.consume(callback)

            # Держим соединение открытым
            await asyncio.Future()

    except aio_pika.exceptions.AMQPConnectionError as e:
        print(f"Ошибка подключения к RabbitMQ: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("Analytics сервис остановлен")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
