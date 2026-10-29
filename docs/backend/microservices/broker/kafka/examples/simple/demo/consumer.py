"""
Пример простого потребителя Kafka, который читает сообщения из топика "demo-topic"
и выводит их на консоль, начиная с самого первого сообщения
"""
# pip install kafka-python
from kafka import KafkaConsumer
import json

def deserializer(serialized):
    """
    Десериализатор получаемых данных
    """
    return json.loads(serialized)

def event_handler(value):
    """
    Обработчик события. Как только мы получаем новое сообщение,
    будет отрабатывать данная функция
    """
    print(f"Event: {value['event']}, value: {value['value']}")

# Создание потребителя Kafka
consumer = KafkaConsumer(
    "demo-topic",                        # Топик для подписки
    bootstrap_servers="localhost:9096",  # Адрес Kafka брокера
    auto_offset_reset="earliest",        # Начинать чтение с начала топика
    enable_auto_commit=True,             # Автоматически подтверждать смещения
    value_deserializer=deserializer      # Десериализация сообщений
)

print("Слушаю сообщения...")

# Чтение сообщений из топика и их обработка с помощью event_handler
for message in consumer:
    event_handler(message.value)
