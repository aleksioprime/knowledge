Все CRUD-транзакции в SQLAlchemy управляются сеансами. Каждый сеанс управляет группой операций «записи» и «чтения» базы данных и проверяет, выполнять их или нет.

Например, он поддерживает группу вставленных, обновленных и удаленных объектов, проверяет, являются ли изменения действительными, а затем координирует свои действия с ядром SQLAlchemy, чтобы внести изменения в базу данных, если все транзакции были проверены. Это соответствует поведению шаблона проектирования _«Unit of Work»._

SQLAlchemy использует сеансы для обеспечения согласованности и целостности данных. Подключим`sessionmaker()` из модуля `sqlalchemy.orm`, и напишем следующий код в файле `db.py`, в котором вызовем `sessionmaker()`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


engine = create_engine('sqlite:///ecommerce.db', echo=True)
SessionLocal = sessionmaker(bind=engine)
```

Приложения могут создавать более одного сеанса с помощью вызова `SessionLocal`_,_ но рекомендуется иметь один сеанс для каждого `APIRouter`_._

Для создания моделей необходима базовая модель, от которой потом наследуются остальные модели. Начиная с версии SQLAlchemy 2.0 для создания базовой модели надо создать класс, унаследованный от DeclarativeBase.

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase  # New

engine = create_engine('sqlite:///ecommerce.db', echo=True)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):  # New
    pass
```

То есть в данном случае определяется класс Base - базовая модель.

