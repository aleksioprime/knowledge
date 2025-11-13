"""
Скрипт для инициализации базы данных тестовыми данными.
Создает тестового пользователя для нагрузочного тестирования
"""

from sqlalchemy import select
from .db import AsyncSessionLocal
from . import models


async def init_test_data():
    """
    Создает тестовые данные в базе данных.
    Добавляет тестового пользователя с учетными данными для Locust.
    """
    async with AsyncSessionLocal() as db:
        try:
            # Проверяем, существует ли уже тестовый пользователь
            result = await db.execute(
                select(models.User).where(models.User.username == "user_test")
            )
            existing_user = result.scalar_one_or_none()

            if not existing_user:
                # Создаем тестового пользователя
                test_user = models.User(
                    username="user_test",
                    full_name="Test User",
                    hashed_password="password",  # В учебном примере пароль в открытом виде
                    disabled=False
                )
                db.add(test_user)
                await db.commit()
                print("Тестовый пользователь создан: username=user_test, password=password")
            else:
                print("Тестовый пользователь уже существует")

        except Exception as e:
            print(f"Ошибка при инициализации данных: {e}")
            await db.rollback()
