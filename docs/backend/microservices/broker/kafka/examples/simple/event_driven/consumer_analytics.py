"""
Пример простого консюмера Kafka, который слушает топик "users.registered" и записывает событие регистрации в аналитику
"""
# pip install kafka-python
from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    "users.registered",
    bootstrap_servers="localhost:9096",
    group_id="analytics-service",
    auto_offset_reset="earliest",
    value_deserializer=lambda v: json.loads(v.decode("utf-8"))
)

print("[AnalyticsService] Listening for events...")

for msg in consumer:
    event = msg.value
    print(f"[AnalyticsService] Записываем регистрацию пользователя #{event['user_id']} в аналитику")
