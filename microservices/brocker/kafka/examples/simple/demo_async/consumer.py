"""
Пример простого потребителя Kafka, который читает сообщения из топика "demo-topic"
и выводит их на консоль, начиная с самого первого сообщения
(асинхронный вариант с использованием confluent-kafka)
"""
# pip install confluent-kafka
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from confluent_kafka import Consumer


def deserializer(serialized):
    """
    Десериализатор получаемых данных
    """
    return json.loads(serialized.decode())


def event_handler(value):
    """
    Обработчик события. Как только мы получаем новое сообщение,
    будет отрабатывать данная функция
    """
    print(f"Event: {value['event']}, value: {value['value']}")


# Создание потребителя Kafka
consumer = Consumer({
    "bootstrap.servers": "localhost:9096",   # Адрес Kafka брокера
    "group.id": "demo-group-1",                # Группа консьюмера
    "auto.offset.reset": "earliest",         # Начинать чтение с начала топика
    "enable.auto.commit": True               # Автоматически подтверждать смещения
})


async def main():
    consumer.subscribe(["demo-topic"])
    print("Слушаю сообщения...")

    while True:
        msg = consumer.poll(timeout=0.1)

        if msg is None:
            await asyncio.sleep(0.1)
            continue

        if msg.error():
            print("Ошибка:", msg.error())
            continue

        value = deserializer(msg.value())
        event_handler(value)


if __name__ == "__main__":
    asyncio.run(main())
