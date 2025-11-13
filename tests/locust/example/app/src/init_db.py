"""
Скрипт для инициализации базы данных тестовыми данными.
Создает тестового пользователя для нагрузочного тестирования
"""

from .db import SessionLocal
from . import models


def init_test_data():
    """
    Создает тестовые данные в базе данных.
    Добавляет тестового пользователя с учетными данными для Locust
    """
    db = SessionLocal()

    try:
        # Проверяем, существует ли уже тестовый пользователь
        existing_user = db.query(models.User).filter(
            models.User.username == "user_test"
        ).first()

        if not existing_user:
            # Создаем тестового пользователя
            test_user = models.User(
                username="user_test",
                full_name="Test User",
                hashed_password="password",  # В учебном примере пароль в открытом виде
                disabled=False
            )
            db.add(test_user)
            db.commit()
            print("Тестовый пользователь создан: username=user_test, password=password")
        else:
            print("Тестовый пользователь уже существует")

    except Exception as e:
        print(f"Ошибка при инициализации данных: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    # Запускаем инициализацию при прямом вызове скрипта
    init_test_data()
