"""
Пример простого продюсера Kafka, который отправляет сообщения в топик "demo-topic"
(асинхронный вариант с использованием confluent-kafka)
"""
# pip install confluent-kafka
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from confluent_kafka import Producer


def serializer(value):
    """
    Обмен данными происходит в байтах, поэтому мы должны
    сначала перевести наше значение JSON, а затем в байты
    """
    return json.dumps(value).encode()


def delivery_callback(err, msg):
    """
    Callback для проверки успешной доставки сообщения
    """
    if err:
        print(f'Ошибка доставки: {err}')
    else:
        print(f'Сообщение доставлено в {msg.topic()} [партиция {msg.partition()}]')


# Создание продюсера Kafka
producer = Producer({
    "bootstrap.servers": "localhost:9096"    # Адрес Kafka брокера
})

executor = ThreadPoolExecutor(max_workers=4)


def sync_send(topic, value):
    """
    Синхронная отправка сообщения.
    Используется внутри ThreadPoolExecutor, чтобы не блокировать asyncio.
    """
    producer.produce(topic, serializer(value))
    producer.poll(0)  # обработка очереди callback’ов


async def async_send(topic, value):
    """
    Асинхронная обёртка, отправляющая сообщения не блокируя event loop.
    """
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(executor, sync_send, topic, value)


async def main():
    # Отправка нескольких сообщений в топик "demo-topic"
    for i in range(10):
        msg = {"event": "loop-message", "value": i}
        await async_send("demo-topic", msg)
        print("Отправлено:", msg)
        await asyncio.sleep(1)

    producer.flush()
    print("Готово!")


if __name__ == "__main__":
    asyncio.run(main())
