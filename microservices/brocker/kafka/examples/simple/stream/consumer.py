"""
Пример простого консюмера Kafka, который слушает топик "numbers_processed" и выводит обработанные числа
"""
# pip install kafka-python
from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    "numbers_processed",
    bootstrap_servers="localhost:9096",
    auto_offset_reset="earliest",
    value_deserializer=lambda v: json.loads(v.decode())
)

print("Waiting for processed numbers...")

for msg in consumer:
    print("[RESULT]:", msg.value)
