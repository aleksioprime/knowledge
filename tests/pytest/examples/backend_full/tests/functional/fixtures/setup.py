"""
Фикстуры для подготовки и очистки тестовой базы данных.

Этот модуль содержит фикстуры для автоматической загрузки тестовых данных
из JSON файлов в базу данных перед запуском тестов и их очистки после завершения.
"""
import pytest
from werkzeug.security import generate_password_hash

from core.settings import test_settings
from testdata import test_data_loader


@pytest.fixture(scope='session')
async def setup_test_data(db_session_maker):
    """
    Подготовка тестовых данных перед запуском тестов.
    Создает пользователей, группы, теги и items в БД.
    После завершения тестов очищает все данные.
    """
    async with db_session_maker() as session:
        # Импортируем модели здесь, чтобы избежать циклических импортов
        from sqlalchemy import text

        # Создаем пользователей
        users_data = test_data_loader.get_users()
        user_ids = {}

        for user_data in users_data:
            hashed_password = generate_password_hash(user_data['password'])
            query = text("""
                INSERT INTO users (username, hashed_password, email, first_name, last_name, is_admin)
                VALUES (:username, :hashed_password, :email, :first_name, :last_name, :is_admin)
                RETURNING id
            """)
            result = await session.execute(
                query,
                {
                    'username': user_data['username'],
                    'hashed_password': hashed_password,
                    'email': user_data['email'],
                    'first_name': user_data.get('first_name'),
                    'last_name': user_data.get('last_name'),
                    'is_admin': user_data.get('is_admin', False)
                }
            )
            user_id = result.scalar_one()
            user_ids[user_data['username']] = user_id

        # Создаем группы
        groups_data = test_data_loader.get_groups()
        group_ids = {}

        for group_data in groups_data:
            query = text("""
                INSERT INTO groups (name, description)
                VALUES (:name, :description)
                RETURNING id
            """)
            result = await session.execute(
                query,
                {
                    'name': group_data['name'],
                    'description': group_data.get('description')
                }
            )
            group_id = result.scalar_one()
            group_ids[group_data['name']] = group_id

        # Создаем теги
        tags_data = test_data_loader.get_tags()
        tag_ids = {}

        for tag_data in tags_data:
            query = text("""
                INSERT INTO tags (name)
                VALUES (:name)
                RETURNING id
            """)
            result = await session.execute(
                query,
                {'name': tag_data['name']}
            )
            tag_id = result.scalar_one()
            tag_ids[tag_data['name']] = tag_id

        # Создаем items
        items_data = test_data_loader.get_items()
        item_ids = {}

        for item_data in items_data:
            group_id = group_ids.get(item_data.get('group_name'))

            query = text("""
                INSERT INTO items (name, price, group_id)
                VALUES (:name, :price, :group_id)
                RETURNING id
            """)
            result = await session.execute(
                query,
                {
                    'name': item_data['name'],
                    'price': item_data['price'],
                    'group_id': group_id
                }
            )
            item_id = result.scalar_one()
            item_ids[item_data['name']] = item_id

            # Связываем item с тегами
            if 'tags' in item_data:
                for tag_name in item_data['tags']:
                    tag_id = tag_ids.get(tag_name)
                    if tag_id:
                        query = text("""
                            INSERT INTO item_tags (item_id, tag_id)
                            VALUES (:item_id, :tag_id)
                        """)
                        await session.execute(
                            query,
                            {'item_id': item_id, 'tag_id': tag_id}
                        )

        await session.commit()

    yield

    # Очистка данных после завершения всех тестов
    async with db_session_maker() as session:
        # Удаляем данные в правильном порядке (из-за внешних ключей)
        await session.execute(text("DELETE FROM item_tags"))
        await session.execute(text("DELETE FROM items"))
        await session.execute(text("DELETE FROM tags"))
        await session.execute(text("DELETE FROM groups"))
        await session.execute(text("DELETE FROM users"))
        await session.commit()
