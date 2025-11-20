"""
Фикстуры для подготовки и очистки тестовой базы данных.

Этот модуль содержит фикстуры для автоматической загрузки тестовых данных
из JSON файлов в базу данных перед запуском тестов и их очистки после завершения.
"""
import uuid
import pytest
from sqlalchemy import text
from werkzeug.security import generate_password_hash

from testdata.loader import load_test_data


@pytest.fixture(scope='session', autouse=True)
async def setup_test_data(db_session_maker):
    """
    Подготовка тестовых данных перед запуском тестов.
    Создает пользователей, группы, теги и items в БД из JSON файлов.
    После завершения тестов очищает все данные.
    """
    async with db_session_maker() as session:
        # Загружаем данные из JSON
        users_data = load_test_data('users.json')['users']
        items_file = load_test_data('items.json')
        groups_data = items_file.get('groups', [])
        tags_data = items_file.get('tags', [])
        items_data = items_file.get('items', [])

        # Создаем пользователей
        user_ids = {}

        for user_data in users_data:
            hashed_password = generate_password_hash(user_data['password'])
            query = text("""
                INSERT INTO users (id, username, hashed_password, email, first_name, last_name, is_admin)
                VALUES (:id, :username, :hashed_password, :email, :first_name, :last_name, :is_admin)
                RETURNING id
            """)
            result = await session.execute(
                query,
                {
                    'id': uuid.uuid4(),
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
        group_ids = {}

        for group_data in groups_data:
            query = text("""
                INSERT INTO groups (id, name, description)
                VALUES (:id, :name, :description)
                RETURNING id
            """)
            result = await session.execute(
                query,
                {
                    'id': uuid.uuid4(),
                    'name': group_data['name'],
                    'description': group_data.get('description')
                }
            )
            group_id = result.scalar_one()
            group_ids[group_data['name']] = group_id

        # Создаем теги
        tag_ids = {}

        for tag_data in tags_data:
            query = text("""
                INSERT INTO tags (id, name)
                VALUES (:id, :name)
                RETURNING id
            """)
            result = await session.execute(
                query,
                {
                    'id': uuid.uuid4(),
                    'name': tag_data['name']
                }
            )
            tag_id = result.scalar_one()
            tag_ids[tag_data['name']] = tag_id

        # Создаем items
        for item_data in items_data:
            group_id = group_ids.get(item_data.get('group_name'))

            query = text("""
                INSERT INTO items (id, name, price, group_id)
                VALUES (:id, :name, :price, :group_id)
                RETURNING id
            """)
            result = await session.execute(
                query,
                {
                    'id': uuid.uuid4(),
                    'name': item_data['name'],
                    'price': item_data['price'],
                    'group_id': group_id
                }
                )
            item_id = result.scalar_one()

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
        print(f"Тестовые данные загружены: {len(users_data)} пользователей, "
              f"{len(groups_data)} групп, {len(tags_data)} тегов, {len(items_data)} items")

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
        print("Тестовые данные очищены")

    # Удаление таблиц
    async with db_session_maker() as session:
        await session.execute(text("DROP TABLE IF EXISTS item_tags"))
        await session.execute(text("DROP TABLE IF EXISTS items"))
        await session.execute(text("DROP TABLE IF EXISTS tags"))
        await session.execute(text("DROP TABLE IF EXISTS groups"))
        await session.execute(text("DROP TABLE IF EXISTS users"))
        await session.execute(text("DROP TABLE IF EXISTS alembic_version"))
        await session.commit()
        print("Таблицы удалены")
