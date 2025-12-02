"""
Пример простого продюсера Kafka, который отправляет сообщение в топик "demo-topic
"""
# pip install kafka-python
from kafka import KafkaProducer
import json

# Создание продюсера Kafka
producer = KafkaProducer(
    bootstrap_servers="localhost:9096",                      # Адрес Kafka брокера
    value_serializer=lambda v: json.dumps(v).encode("utf-8") # Сериализация сообщений
)

# Отправка сообщения в топик "demo-topic"
msg = {"event": "hello", "value": 42}
producer.send("demo-topic", msg)
producer.flush()

print("Отправлено:", msg)
