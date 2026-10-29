# SQLAlchemy: модели и сессия

Писать SQL строками внутри Python-кода неудобно: опечатку в имени колонки видно только при запуске, результат приходит кортежами, а значения легко подставить небезопасно. SQLAlchemy ORM описывает таблицы классами Python, а запросы собирает из выражений. Вы работаете с объектами `Task` и `User`, а SQL библиотека пишет сама.

```bash
pip install sqlalchemy "psycopg[binary]"
```

## Минимальный пример

```python
from sqlalchemy import String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class Task(Base):
    __tablename__ = 'tasks'

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    done: Mapped[bool] = mapped_column(default=False)
    note: Mapped[str | None]


engine = create_engine('postgresql+psycopg://tasker:tasker@localhost:5432/tasker')
Base.metadata.create_all(engine)

with Session(engine) as session:
    session.add_all([Task(title='Купить хлеб'), Task(title='Сдать отчёт', done=True)])
    session.commit()

    active = session.scalars(select(Task).where(Task.done == False)).all()
    print([task.title for task in active])  # ['Купить хлеб']
```

## Как это работает

**Модель — это таблица.** Класс-наследник `Base` описывает таблицу `tasks`, а каждый атрибут `Mapped[...]` — колонку. Тип колонки и `NULL` выводятся из подсказки типа:

| Подсказка | Колонка |
|---|---|
| `Mapped[int]` | `INTEGER NOT NULL` |
| `Mapped[str]` + `String(200)` | `VARCHAR(200) NOT NULL` |
| `Mapped[bool]` | `BOOLEAN NOT NULL` |
| `Mapped[str \| None]` | `VARCHAR`, допускает `NULL` |

`mapped_column(...)` нужен, когда требуется что-то кроме типа: первичный ключ, длина строки, значение по умолчанию, индекс, внешний ключ.

**Движок (`engine`) — это подключение.** Строка вида `драйвер://пользователь:пароль@хост:порт/база` говорит, к какой базе и через какой драйвер подключаться. Движок держит пул соединений, создают его один раз на всё приложение.

**Сессия — это «рабочая тетрадь».** Через неё загружают объекты и копят изменения: добавленные, изменённые и удалённые объекты. Пока не вызван `commit()`, всё это остаётся внутри одной транзакции. `commit()` отправляет изменения в базу одной транзакцией, а при ошибке их можно отменить `rollback()`. `with Session(engine)` сам закроет сессию в конце блока.

`create_all` создаёт таблицы, которых ещё нет. Это удобно для экспериментов и тестов. В настоящем проекте схему меняют миграциями [Alembic](../alembic/README.md).

## Основные операции

```python
from sqlalchemy import delete, func, select, update

with Session(engine) as session:
    # Получить по первичному ключу
    session.get(Task, 2)  # Task(id=2, title='Сдать отчёт', done=True) или None

    # Список с условием и сортировкой
    session.scalars(select(Task).where(Task.done == False).order_by(Task.id)).all()

    # Один объект или None
    session.scalar(select(Task).where(Task.title == 'Купить хлеб'))

    # Количество
    session.scalar(select(func.count()).select_from(Task))  # 2

    # Изменить объект: достаточно поменять атрибут и сделать commit
    task = session.get(Task, 1)
    task.done = True
    session.commit()

    # Массовое изменение без загрузки объектов
    session.execute(update(Task).where(Task.done == True).values(done=False))

    # Удалить
    session.delete(session.get(Task, 2))
    session.commit()
```

`scalars` возвращает объекты моделей, а `execute` — строки (`Row`). Он нужен, когда в `select` перечислены отдельные колонки: `select(Task.id, Task.title)`.

Для получения результата есть три метода с разной строгостью:

- `.all()` — список, возможно пустой;
- `.first()` — первый объект или `None`;
- `.one()` — ровно один объект, иначе исключение: `NoResultFound: No row was found when one was required`.

## Посмотреть, какой SQL выполняется

Параметр `echo=True` выводит в лог каждый запрос. Без него трудно понять, почему код работает медленно:

```python
engine = create_engine(url, echo=True)
```

```text
INFO sqlalchemy.engine.Engine INSERT INTO users (email) VALUES (%(email)s::VARCHAR) RETURNING users.id
```

Значения передаются параметрами (`%(email)s`), а не подставляются в строку. Поэтому SQL-инъекции через такие запросы невозможны: что бы ни прислал пользователь, база получит это как значение, а не как часть SQL.

## Частые ошибки

- **Забытый `commit()`.** Объекты добавлены в сессию, но при её закрытии изменения откатятся. Запросы `select` в той же сессии их при этом видят, что сбивает с толку.
- **`not`, `and`, `or` в условиях.** Эти операторы Python не превращаются в SQL и ломают запрос молча: `where(not Task.done)` становится `WHERE false`, а `where(Task.done == False and Task.id > 1)` теряет первое условие. Пишите `where(~Task.done)`, `where(Task.done == False, Task.id > 1)` или используйте `and_()` и `or_()`.
- **Один движок на каждый запрос.** Движок дорогой: он держит пул соединений. Создайте его один раз при старте приложения.
- **Старый стиль `session.query(Task).filter(...)`.** Он ещё работает, но в SQLAlchemy 2.0 основной способ — `select()`, как в этой заметке.

## Связанные темы

- [Связи и проблема N+1](relationships.md)
- [Асинхронный SQLAlchemy](async.md)
- [Основы SQL](../sql/basics.md)
