"""
Пример простого продюсера Kafka, который отправляет сообщение в топик "demo-topic
"""
# pip install kafka-python
from kafka import KafkaProducer
import json
import time

def serializer(value):
    """
    Обмен данными происходит в байтах, поэтому мы должны
    сначала перевести наше значение JSON, а затем в байты
    """
    return json.dumps(value).encode()

# Создание продюсера Kafka
producer = KafkaProducer(
    bootstrap_servers="localhost:9096",     # Адрес Kafka брокера
    value_serializer=serializer             # Сериализация сообщений
)

# Отправка нескольких сообщений в топик "demo-topic"
for i in range(10):
    msg = {"event": "loop-message", "value": i}
    producer.send("demo-topic", msg)
    producer.flush()
    print("Отправлено:", msg)
    time.sleep(1)

print("Готово!")
