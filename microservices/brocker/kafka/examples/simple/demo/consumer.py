"""
Пример простого потребителя Kafka, который читает сообщения из топика "demo-topic"
и выводит их на консоль, начиная с самого первого сообщения
"""
# pip install kafka-python
from kafka import KafkaConsumer
import json

# Создание потребителя Kafka
consumer = KafkaConsumer(
    "demo-topic",                        # Топик для подписки
    bootstrap_servers="localhost:9096",  # Адрес Kafka брокера
    auto_offset_reset="earliest",        # Начинать чтение с начала топика
    enable_auto_commit=True,             # Автоматически подтверждать смещения
    value_deserializer=lambda v: json.loads(v.decode("utf-8")) # Десериализация сообщений
)

print("Слушаю сообщения...")

for message in consumer:
    print("Получено:", message.value)
