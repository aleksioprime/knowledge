"""
Скрипт для создания демонстрационных данных в базе данных.
Заполняет БД тестовыми пользователями, группами, элементами и тегами.

Запуск:
    python -m scripts.create_test_data
"""
import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from werkzeug.security import generate_password_hash
from sqlalchemy import select

from src.db.postgres import async_session_maker, engine, Base
from src.models.user import User
from src.models.item import Group, Item, Tag


async def create_tables():
    """
    Создает все таблицы в базе данных.
    Если таблицы уже существуют, они не будут пересозданы.
    """
    async with engine.begin() as conn:
        # Удаляем существующие таблицы (осторожно!)
        # await conn.run_sync(Base.metadata.drop_all)
        # Создаем все таблицы
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Таблицы созданы")


async def create_users():
    """
    Создает тестовых пользователей:
    - Администратора
    - Обычных пользователей
    """
    async with async_session_maker() as session:
        # Проверяем, есть ли уже пользователи
        result = await session.execute(select(User).limit(1))
        if result.scalar_one_or_none():
            print("⚠ Пользователи уже существуют, пропускаем создание")
            return

        users = [
            User(
                username="admin",
                email="admin@example.com",
                hashed_password=generate_password_hash("admin123"),
                first_name="Администратор",
                last_name="Системы",
                is_admin=True,
            ),
            User(
                username="user1",
                email="user1@example.com",
                hashed_password=generate_password_hash("password123"),
                first_name="Иван",
                last_name="Иванов",
                is_admin=False,
            ),
            User(
                username="user2",
                email="user2@example.com",
                hashed_password=generate_password_hash("password123"),
                first_name="Мария",
                last_name="Петрова",
                is_admin=False,
            ),
            User(
                username="testuser",
                email="test@example.com",
                hashed_password=generate_password_hash("test123"),
                first_name="Тестовый",
                last_name="Пользователь",
                is_admin=False,
            ),
        ]

        session.add_all(users)
        await session.commit()
        print(f"✓ Создано {len(users)} пользователей")
        print("  Логины: admin (пароль: admin123), user1/user2 (пароль: password123)")


async def create_groups():
    """
    Создает группы элементов
    """
    async with async_session_maker() as session:
        # Проверяем, есть ли уже группы
        result = await session.execute(select(Group).limit(1))
        if result.scalar_one_or_none():
            print("⚠ Группы уже существуют, пропускаем создание")
            return []

        groups = [
            Group(
                name="Электроника",
                description="Электронные устройства и гаджеты"
            ),
            Group(
                name="Одежда",
                description="Одежда и аксессуары"
            ),
            Group(
                name="Книги",
                description="Книги различных жанров"
            ),
            Group(
                name="Продукты",
                description="Продукты питания"
            ),
            Group(
                name="Спорт",
                description="Товары для спорта и активного отдыха"
            ),
        ]

        session.add_all(groups)
        await session.commit()

        # Обновляем объекты, чтобы получить их ID
        for group in groups:
            await session.refresh(group)

        print(f"✓ Создано {len(groups)} групп")
        return groups


async def create_tags():
    """
    Создает теги для элементов
    """
    async with async_session_maker() as session:
        # Проверяем, есть ли уже теги
        result = await session.execute(select(Tag).limit(1))
        if result.scalar_one_or_none():
            print("⚠ Теги уже существуют, пропускаем создание")
            # Загружаем существующие теги
            result = await session.execute(select(Tag))
            return result.scalars().all()

        tags = [
            Tag(name="новинка"),
            Tag(name="скидка"),
            Tag(name="популярное"),
            Tag(name="премиум"),
            Tag(name="эко"),
            Tag(name="распродажа"),
            Tag(name="лимитированная серия"),
            Tag(name="бестселлер"),
        ]

        session.add_all(tags)
        await session.commit()

        # Обновляем объекты
        for tag in tags:
            await session.refresh(tag)

        print(f"✓ Создано {len(tags)} тегов")
        return tags


async def create_items(groups: list[Group], tags: list[Tag]):
    """
    Создает элементы с привязкой к группам и тегам
    """
    async with async_session_maker() as session:
        # Проверяем, есть ли уже элементы
        result = await session.execute(select(Item).limit(1))
        if result.scalar_one_or_none():
            print("⚠ Элементы уже существуют, пропускаем создание")
            return

        # Если группы или теги не переданы, загружаем их из БД
        if not groups:
            result = await session.execute(select(Group))
            groups = result.scalars().all()

        if not tags:
            result = await session.execute(select(Tag))
            tags = result.scalars().all()

        items = [
            # Электроника
            Item(
                name="Смартфон Samsung Galaxy",
                price=45999.99,
                group_id=groups[0].id,
                tags=[tags[0], tags[2]],  # новинка, популярное
            ),
            Item(
                name="Ноутбук MacBook Pro",
                price=189999.99,
                group_id=groups[0].id,
                tags=[tags[3], tags[7]],  # премиум, бестселлер
            ),
            Item(
                name="Наушники Sony WH-1000XM4",
                price=24999.99,
                group_id=groups[0].id,
                tags=[tags[1], tags[2]],  # скидка, популярное
            ),
            Item(
                name="Умные часы Apple Watch",
                price=34999.99,
                group_id=groups[0].id,
                tags=[tags[0], tags[3]],  # новинка, премиум
            ),

            # Одежда
            Item(
                name="Джинсы Levi's 501",
                price=5999.99,
                group_id=groups[1].id,
                tags=[tags[2], tags[7]],  # популярное, бестселлер
            ),
            Item(
                name="Куртка North Face",
                price=15999.99,
                group_id=groups[1].id,
                tags=[tags[4], tags[6]],  # эко, лимитированная серия
            ),
            Item(
                name="Кроссовки Nike Air Max",
                price=8999.99,
                group_id=groups[1].id,
                tags=[tags[1], tags[5]],  # скидка, распродажа
            ),

            # Книги
            Item(
                name="Python для анализа данных",
                price=1299.99,
                group_id=groups[2].id,
                tags=[tags[0], tags[7]],  # новинка, бестселлер
            ),
            Item(
                name="Чистый код - Роберт Мартин",
                price=999.99,
                group_id=groups[2].id,
                tags=[tags[2]],  # популярное
            ),
            Item(
                name="1984 - Джордж Оруэлл",
                price=599.99,
                group_id=groups[2].id,
                tags=[tags[7]],  # бестселлер
            ),

            # Продукты
            Item(
                name="Органический мёд",
                price=899.99,
                group_id=groups[3].id,
                tags=[tags[4], tags[3]],  # эко, премиум
            ),
            Item(
                name="Кофе арабика премиум",
                price=1299.99,
                group_id=groups[3].id,
                tags=[tags[3], tags[0]],  # премиум, новинка
            ),

            # Спорт
            Item(
                name="Йога-мат премиум",
                price=2499.99,
                group_id=groups[4].id,
                tags=[tags[4], tags[2]],  # эко, популярное
            ),
            Item(
                name="Гантели 10 кг (пара)",
                price=3499.99,
                group_id=groups[4].id,
                tags=[tags[1]],  # скидка
            ),
            Item(
                name="Велосипед горный",
                price=45999.99,
                group_id=groups[4].id,
                tags=[tags[0], tags[6]],  # новинка, лимитированная серия
            ),
        ]

        session.add_all(items)
        await session.commit()
        print(f"✓ Создано {len(items)} элементов")


async def main():
    """
    Главная функция для создания всех тестовых данных
    """
    print("\n" + "="*60)
    print("Создание демонстрационных данных")
    print("="*60 + "\n")

    try:
        # Создаем таблицы
        await create_tables()

        # Создаем данные
        await create_users()
        groups = await create_groups()
        tags = await create_tags()
        await create_items(groups, tags)

        print("\n" + "="*60)
        print("✓ Демонстрационные данные успешно созданы!")
        print("="*60)
        print("\nТеперь вы можете:")
        print("  • Войти как admin (admin123)")
        print("  • Войти как user1 или user2 (password123)")
        print("  • Просмотреть элементы через API")
        print("  • Протестировать фильтрацию и пагинацию\n")

    except Exception as e:
        print(f"\n❌ Ошибка при создании данных: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
