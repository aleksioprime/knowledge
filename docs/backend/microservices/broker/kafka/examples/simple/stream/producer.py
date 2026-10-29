"""
Пример простого продюсера Kafka, который отправляет числа в топик "numbers"
"""
# pip install kafka-python
from kafka import KafkaProducer
import json
import time

producer = KafkaProducer(
    bootstrap_servers="localhost:9096",
    value_serializer=lambda v: json.dumps(v).encode()
)

print("Sending test numbers...")

for i in range(1, 6):
    print("Send:", i)
    producer.send("numbers", i)
    time.sleep(0.5)

producer.flush()