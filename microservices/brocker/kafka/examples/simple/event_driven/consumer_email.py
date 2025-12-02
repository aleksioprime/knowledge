"""
Пример простого консюмера Kafka, который слушает топик "users.registered" и имитирует отправку приветственного email
"""
# pip install kafka-python
from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    "users.registered",
    bootstrap_servers="localhost:9096",
    group_id="email-service",
    auto_offset_reset="earliest",
    value_deserializer=lambda v: json.loads(v.decode("utf-8"))
)

print("[EmailService] Listening for events...")

for msg in consumer:
    event = msg.value
    print(f"[EmailService] Отправляем приветственное письмо на {event['email']}")
