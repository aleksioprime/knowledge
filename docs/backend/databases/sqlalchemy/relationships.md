# Связи и проблема N+1

Задачи принадлежат пользователям, а у задач есть метки «дом», «работа». В базе это внешние ключи и промежуточные таблицы. SQLAlchemy позволяет работать с такими связями как с обычными атрибутами: `user.tasks`, `task.owner`, `task.tags`. Удобство даёт и риск: если не знать, *когда* библиотека загружает связанные объекты, страница со списком из 100 пользователей незаметно выполнит 101 запрос.

## Минимальный пример

```python
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)

    tasks: Mapped[list['Task']] = relationship(back_populates='owner')


class Task(Base):
    __tablename__ = 'tasks'

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id'))

    owner: Mapped[User] = relationship(back_populates='tasks')


with Session(engine) as session:
    anna = User(email='anna@example.com', tasks=[Task(title='Купить хлеб'), Task(title='Сдать отчёт')])
    session.add(anna)
    session.commit()

    task = session.get(Task, 1)
    print(task.owner.email)  # anna@example.com
```

## Как это работает

Связь описывается в двух местах:

- `ForeignKey('users.id')` — **колонка** в таблице `tasks`, которая хранит id владельца. Это то, что реально лежит в базе;
- `relationship(...)` — **атрибут** Python, через который удобно ходить по связи. В базе его нет.

`back_populates` связывает две стороны: добавили задачу в `anna.tasks`, и у задачи сам заполнился `owner`.

Тип подсказывает, сколько объектов на той стороне: `Mapped[list['Task']]` — много, `Mapped[User]` — один.

## Проблема N+1

По умолчанию связанные объекты загружаются **лениво**: в момент первого обращения к атрибуту. Для одного объекта это незаметно. А в цикле получается беда:

```python
users = session.scalars(select(User)).all()
for user in users:
    print(user.email, len(user.tasks))
```

Для трёх пользователей выполнится 4 запроса: один за пользователями и по одному за задачами каждого.

```text
SELECT users.id, users.email FROM users ORDER BY users.id
SELECT tasks.id, tasks.title, tasks.owner_id FROM tasks WHERE %(param_1)s = tasks.owner_id
SELECT tasks.id, tasks.title, tasks.owner_id FROM tasks WHERE %(param_1)s = tasks.owner_id
SELECT tasks.id, tasks.title, tasks.owner_id FROM tasks WHERE %(param_1)s = tasks.owner_id
```

Это и есть «N+1»: один запрос плюс по запросу на каждый из N объектов. На 100 пользователях — 101 запрос и заметная задержка.

## Решение: загрузить заранее

Связи, которые точно понадобятся, указывают в запросе через `options`:

```python
from sqlalchemy.orm import joinedload, selectinload

# 2 запроса: пользователи, затем задачи всех сразу через WHERE owner_id IN (...)
users = session.scalars(select(User).options(selectinload(User.tasks))).all()

# 1 запрос: пользователи и задачи через LEFT JOIN
users = session.scalars(select(User).options(joinedload(User.tasks))).unique().all()
```

```text
selectinload:
  SELECT users.id, users.email FROM users ORDER BY users.id
  SELECT tasks.owner_id, tasks.id, tasks.title FROM tasks WHERE tasks.owner_id IN (...)

joinedload:
  SELECT users.id, users.email, tasks_1.id, ... FROM users LEFT OUTER JOIN tasks AS tasks_1 ON users.id = tasks_1.owner_id
```

Какой выбрать:

- **`selectinload`** — для связей «один ко многим» (`user.tasks`). Строки не дублируются, и это хороший выбор по умолчанию;
- **`joinedload`** — для связей «многие к одному» (`task.owner`): владелец у каждой задачи один, поэтому JOIN не размножает строки. Для коллекций результат нужно схлопнуть через `.unique()`.

Чтобы ленивая загрузка не проскочила незаметно, её можно запретить. Тогда обращение к незагруженной связи сразу вызовет ошибку:

```python
from sqlalchemy.orm import raiseload

user = session.scalars(select(User).options(raiseload(User.tasks))).first()
user.tasks  # InvalidRequestError: 'User.tasks' is not available due to lazy='raise'
```

## Многие ко многим

У задачи много меток, у метки много задач. Такая связь хранится в промежуточной таблице:

```python
from sqlalchemy import Column, Table

task_tags = Table(
    'task_tags',
    Base.metadata,
    Column('task_id', ForeignKey('tasks.id'), primary_key=True),
    Column('tag_id', ForeignKey('tags.id'), primary_key=True),
)


class Tag(Base):
    __tablename__ = 'tags'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    tasks: Mapped[list['Task']] = relationship(secondary=task_tags, back_populates='tags')


# в классе Task:
#     tags: Mapped[list['Tag']] = relationship(secondary=task_tags, back_populates='tasks')

task.tags.append(Tag(name='дом'))  # строку в task_tags SQLAlchemy добавит сама
```

## Каскады: что будет с задачами при удалении пользователя

```python
tasks: Mapped[list['Task']] = relationship(back_populates='owner', cascade='all, delete-orphan')
```

- `all` — операции над пользователем (добавление, удаление) применяются и к его задачам;
- `delete-orphan` — задача, убранная из `user.tasks`, удаляется из базы.

Без каскада удаление пользователя с задачами упадёт на внешнем ключе. Второй вариант — каскад в самой базе: `ForeignKey('users.id', ondelete='CASCADE')`, как в [«Задачнике»](../../../practice/projects/tasker/app/models.py). Он срабатывает, даже если удалять строку не через ORM.

## Частые ошибки

- **Связь в цикле без `selectinload`.** Самая частая причина медленных списков. Включите `echo=True` и посчитайте запросы.
- **`joinedload` для большой коллекции.** У пользователя 1000 задач: JOIN повторит данные пользователя в 1000 строках. Для коллекций лучше `selectinload`.
- **Индекс на внешнем ключе.** PostgreSQL не создаёт индекс для `owner_id` сам. Без него `WHERE owner_id = ...` просматривает всю таблицу. Добавьте `index=True`.

## Связанные темы

- [Модели и сессия](basics.md)
- [Асинхронный SQLAlchemy](async.md) — где ленивая загрузка вообще не работает
- [JOIN в SQL](../sql/joins.md)
