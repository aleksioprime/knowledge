"""
Пример простого продюсера Kafka, который отправляет событие регистрации пользователя в топик "users.registered""
"""
# pip install kafka-python
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers="localhost:9096",
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

def register_user(user_id, email):
    event = {
        "user_id": user_id,
        "email": email,
        "event_type": "USER_REGISTERED"
    }

    producer.send("users.registered", event)
    producer.flush()
    print(f"[UserService] Пользователь зарегистрирован → событие отправлено: {event}")


if __name__ == "__main__":
    # имитация регистрации
    register_user(1, "hello@world.com")
