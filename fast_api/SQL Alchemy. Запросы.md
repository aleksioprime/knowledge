Конфигурация создания сессии:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker  # New


engine = create_engine('sqlite:///ecommerce.db', echo=True)
SessionLocal = sessionmaker(bind=engine)  # New
```

Зависимость для создания сессии:

```python
from app.backend.db import SessionLocal


async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Запросы создания записей в БД**

```python
# ... импорт других библиотек
from sqlalchemy import insert

@router.post('/', status_code=status.HTTP_201_CREATED)
async def create_category(
		db: Annotated[Session, Depends(get_db)], 
		create_category: CreateCategory,
	):
    db.execute(insert(Category).values(name=create_category.name,
                                       parent_id=create_category.parent_id,
                                       slug=slugify(create_category.name)))
    db.commit()
    return {
        'status_code': status.HTTP_201_CREATED,
        'transaction': 'Successful'
    }
```

В  функции создания записи мы подключаем зависимость сессии БД, и получаем нашу модель из POST запроса.

**Запросы получения записей из БД**

```python
# ... импорт других библиотек
from sqlalchemy import select

@router.get('/')
async def get_all_categories(db: Annotated[Session, Depends(get_db)]):
    categories = db.scalars(select(Category).where(Category.is_active == True)).all()
    return categories
```

В запросе мы выбираем таблицу `Category` и делаем выборку по полю `is_active`, чтобы получить только активные категории.

**Запросы удаления записей в БД**

```python
# ... импорт других библиотек
from sqlalchemy import update

@router.delete('/{category_slug}')
async def delete_category(db: Annotated[Session, Depends(get_db)], category_slug: str):
    category = db.scalar(select(Category).where(Category.slug == category_slug, Category.is_active == True))
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='There is no category found'
        )
    db.execute(update(Category).where(Category.slug == category_slug).values(is_active=False))
    db.commit()
    return {
        'status_code': status.HTTP_200_OK,
        'transaction': 'Category delete is successful'
    }
```

Первым делом мы получаем данные нашей категории из БД, это сделано для того, чтобы в случае отсутствия категории с введенным в запросе `category_id`, вызвать ошибку `404` с текстом "There is no category found". Далее мы выполняем запрос об изменении значения поля `is_active` на `False`, в таблице `Category` записи с `slug` равным введенному в запросе `category_slug.`  И возвращаем код ответа 200, с текстом об успешном удалении категории.

Если мы хотим удалять категории, то запрос будет выглядеть следующим образом.

```python
# ...
from sqlalchemy import delete
# ...
db.delete(category)
db.commit()
```

**Запросы редактирования записей в БД**

```python
# ... импорт других библиотек
from sqlalchemy import update

@router.put('/{category_slug}')
async def update_category(db: Annotated[Session, Depends(get_db)], category_slug: str, update_category: CreateCategory):
    category = db.scalar(select(Category).where(Category.slug == category_slug))
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='There is no category found'
        )

    db.execute(update(Category).where(Category.slug == category_slug).values(
            name=update_category.name,
            slug=slugify(update_category.name),
            parent_id=update_category.parent_id))

    db.commit()
    return {
        'status_code': status.HTTP_200_OK,
        'transaction': 'Category update is successful'
    }
```

Первым делом мы должны получить параметр `category_slug` из запроса, а также получим нашу `Pydantic` модель в виде переменной `update_category`. 

Далее, по аналогии с удалением категорий, мы должны получить категорию с полученным `category_slug`, и если ее не существует вызвать ошибку `404` с текстом 'There is no category found'. И уже после этой проверки, также через метод `update` в SQLAlchemy, изменяем значения полей, на значения из полученной Pydantic модели.