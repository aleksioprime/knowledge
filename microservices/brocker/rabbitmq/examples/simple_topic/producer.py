"""
Producer отправляет логи разных уровней через TOPIC exchange.
Использует routing keys в формате: <level>.<service>
"""

import asyncio
import json
import sys
import aio_pika
from datetime import datetime

EXCHANGE = "logs_topic"
RABBIT_URL = "amqp://guest:guest@localhost:5672/"


async def send_log(exchange: aio_pika.Exchange, routing_key: str, message: str) -> None:
    """Отправляет лог-сообщение с указанным routing key"""
    log_entry = {
        "message": message,
        "routing_key": routing_key,
        "timestamp": datetime.now().isoformat()
    }

    try:
        # Отправляем сообщение в exchange RabbitMQ:
        # delivery_mode=aio_pika.DeliveryMode.PERSISTENT - сохраняет сообщение на диск
        # content_type="application/json" - указывает тип содержимого сообщения
        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(log_entry).encode(),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=routing_key,
        )
        level, service = routing_key.split('.', 1)
        print(f"[{level.upper():7}] {service:12} → {message}")
    except Exception as e:
        print(f"Ошибка при отправке лога: {e}")
        raise


async def main():
    """Основная функция producer для Topic паттерна"""
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

            # Отправляем разнообразные логи для демонстрации
            print("Отправка логов...")
            logs = [
                ("error.payment", "Ошибка обработки платежа #12345"),
                ("error.database", "Потеряно соединение с БД"),
                ("warning.payment", "Медленный ответ платёжного шлюза"),
                ("warning.system", "Нагрузка на CPU 85%"),
                ("info.user", "Пользователь user@example.com авторизован"),
                ("info.system", "Система запущена успешно"),
                ("debug.payment", "Запрос к API payment gateway"),
            ]

            for routing_key, message in logs:
                await send_log(exchange, routing_key, message)
                # Небольшая пауза для читаемости
                await asyncio.sleep(0.3)

            print(f"Все логи отправлены ({len(logs)} шт.)")
            print("Consumers получат только логи по своим паттернам")

    except aio_pika.exceptions.AMQPConnectionError as e:
        print(f"Ошибка подключения к RabbitMQ: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())