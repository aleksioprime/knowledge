Установка асинхронного драйвера:

```sh
pip install asyncpg
```

Настройки подключения к базе данных:

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase


engine = create_async_engine('postgresql+asyncpg://ecommerce:xxxxxx@localhost:5432/ecommerce', echo=True)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class Base(DeclarativeBase):
    pass
```

Как и в синхронной версии, директива `sessionmaker()` используется для создания фабрики сессий с некоторыми новыми параметрами, установленными для включения `AsyncSession`. Во-первых, для его параметра `expire_on_commit` установлено значение `False`, чтобы экземпляры этой модели и значения ее атрибутов были доступны на время транзакции, даже после вызова `commit()`.

В отличие от синхронной среды, все классы сущностей и их объекты столбцов по-прежнему доступны другим процессам даже после фиксации транзакции. Затем его параметр `class_` будет иметь имя класса `AsyncSession`, объекта, который будет управлять транзакциями.

Для создания среды миграций в каталоге `app/migrations/` нужно запустить команду

```csharp
alembic init -t async app/migrations
```

Мы используем флаг `-t async` для асинхронной поддержки.

Изменим настройки подключения к БД PostgreSQL  в файле `alembic.ini`:

```python
sqlalchemy.url = postgresql+asyncpg://ecommerce:XXXXXX@localhost:5432/ecommerce
```

**Внимание**: пароль `XXXXXX` в данной строке необходимо заменить на тот, что использовали при создании пользователя БД `ecommerce`.

*Файл `env.py` настраивается стандартным способом*

Зависимость для работы с асинхронными запросами:

```python
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from app.backend.db import async_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
```

### Работа с запросами

Вывод записей:

```python
from sqlalchemy.ext.asyncio import AsyncSession


@router.get('/')
async def get_all_categories(db: Annotated[AsyncSession, Depends(get_db)]):
    categories = await db.scalars(select(Category).where(Category.is_active == True))
    return categories.all()
```

При использовании асинхронного подключения метод `scalars` становится корутиной и для получения объекта результата `ScalarResult` необходимо дождаться её выполнения с помощью выражения `await`, только после этого, мы можем задействовать метод `all()` у полученного объекта `ScalarResult`

Создание записи:

```python
@router.post('/')
async def create_category(db: Annotated[AsyncSession, Depends(get_db)], create_category: CreateCategory):
    await db.execute(insert(Category).values(name=create_category.name,
                                       parent_id=create_category.parent_id,
                                       slug=slugify(create_category.name)))
    await db.commit()
    return {
        'status_code': status.HTTP_201_CREATED,
        'transaction': 'Successful'
    }
```

В данном случе мы добавляем выражение `await` для самого запроса и метода `commit`, для подтверждения изменений. Обратите внимание, что PostgreSQL не пропустит запрос создания родительской категории, где `"parent_id": 0`, теперь нам необходимо использовать в запросе `"parent_id": null`

Редактирование записей:

```python
@router.put('/{category_slug}')
async def update_category(db: Annotated[AsyncSession, Depends(get_db)], category_slug: str, update_category: CreateCategory):
    category = await db.scalar(select(Category).where(Category.slug == category_slug))
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='There is no category found'
        )

    category.name = update_category.name
    category.slug = slugify(update_category.name)
    category.parent_id = update_category.parent_id

    await db.commit()

    return {
        'status_code': status.HTTP_200_OK,
        'transaction': 'Category update is successful'
    }
    ```

Удаление записей:

```python
@router.delete('/{category_slug}')
async def delete_category(db: Annotated[AsyncSession, Depends(get_db)], category_slug: str):
    category = await db.scalar(select(Category).where(Category.slug == category_slug))
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='There is no category found'
        )
    category.is_active = False
    await db.commit()

    return {
        'status_code': status.HTTP_200_OK,
        'transaction': 'Category delete is successful'
    }
```