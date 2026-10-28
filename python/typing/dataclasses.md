# dataclasses

Классы, которые просто хранят данные, требуют много однообразного кода: `__init__`, чтобы сохранить поля, `__repr__`, чтобы объект нормально печатался, `__eq__`, чтобы два одинаковых объекта были равны. Декоратор `@dataclass` пишет всё это сам по подсказкам типов.

## Минимальный пример

```python
from dataclasses import dataclass


@dataclass
class Task:
    title: str
    done: bool = False


a = Task('Купить хлеб')
b = Task('Купить хлеб')

print(a)       # Task(title='Купить хлеб', done=False)
print(a == b)  # True
```

Без декоратора то же самое заняло бы около 15 строк, а `print(a)` вывел бы что-то вроде `<__main__.Task object at 0x10…>`, а `a == b` вернул бы `False`.

## Как это работает

`@dataclass` читает аннотации полей класса и генерирует методы:

- `__init__` — принимает поля в том порядке, в каком они объявлены;
- `__repr__` — показывает имя класса и значения полей;
- `__eq__` — сравнивает объекты по полям, а не по адресу в памяти.

Типы при этом **не проверяются**: `Task(title=42)` создастся без ошибок. Если нужна проверка данных, смотрите [Pydantic](pydantic.md).

## Полезные возможности

**Изменяемые значения по умолчанию — через `field`.** Иначе все объекты делили бы один список. Dataclass не даёт ошибиться и падает сразу:

```python
from dataclasses import dataclass, field


@dataclass
class Task:
    title: str
    tags: list[str] = field(default_factory=list)  # у каждой задачи свой список

# А `tags: list[str] = []` даст ошибку:
# ValueError: mutable default <class 'list'> for field tags is not allowed: use default_factory
```

**Проверка и нормализация — в `__post_init__`.** Метод вызывается сразу после `__init__`:

```python
@dataclass
class Task:
    title: str

    def __post_init__(self):
        self.title = self.title.strip()
        if not self.title:
            raise ValueError('Название задачи не может быть пустым')


Task('  Позвонить маме  ')  # Task(title='Позвонить маме')
Task('   ')                 # ValueError: Название задачи не может быть пустым
```

**Неизменяемые объекты — `frozen=True`.** Подходят для значений, которые не должны меняться случайно: деньги, координаты, настройки. Такие объекты можно класть в `set` и использовать как ключи словаря.

```python
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Money:
    amount: int
    currency: str = 'RUB'


price = Money(100)
price.amount = 200            # FrozenInstanceError: cannot assign to field 'amount'
replace(price, amount=200)    # Money(amount=200, currency='RUB') — новый объект
```

**Сортировка — `order=True`.** Объекты сравниваются по полям по очереди, как кортежи:

```python
@dataclass(order=True)
class Version:
    major: int
    minor: int


sorted([Version(1, 10), Version(1, 2), Version(0, 9)])
# [Version(major=0, minor=9), Version(major=1, minor=2), Version(major=1, minor=10)]
```

**Только именованные аргументы — `kw_only=True`.** Защищает от путаницы, когда полей много:

```python
@dataclass(kw_only=True)
class User:
    name: str
    is_admin: bool = False


User(name='Анна', is_admin=True)
User('Анна')  # TypeError: User.__init__() takes 1 positional argument but 2 were given
```

**Экономия памяти — `slots=True`.** Объект использует [`__slots__`](../master/memory.md) и занимает меньше места, но новые атрибуты добавить нельзя.

**Превращение в словарь — `asdict`.** Удобно перед сохранением в JSON:

```python
from dataclasses import asdict

asdict(Task('Отчёт'))  # {'title': 'Отчёт'}
```

## Частые ошибки

- **Ждать проверки типов.** `@dataclass` использует аннотации только чтобы узнать имена полей. Данные из внешнего мира (JSON, формы, API) лучше проверять Pydantic.
- **Поле без значения по умолчанию после поля со значением.** `title: str = ''` и затем `done: bool` дадут `TypeError`: необязательные аргументы не могут стоять перед обязательными. Переставьте поля или используйте `kw_only=True`.
- **Менять «замороженный» объект через вложенный список.** `frozen=True` запрещает присваивать поля, но список внутри поля по-прежнему можно изменить.

## Когда не использовать

- Данные приходят снаружи и их нужно проверять и преобразовывать — берите [Pydantic](pydantic.md).
- У класса сложное поведение и мало данных — обычный класс будет понятнее.
- Нужна только пара значений на один раз — хватит кортежа или `NamedTuple`.

## Связанные темы

- [Подсказки типов](type_hints.md)
- [Pydantic](pydantic.md)
- [ООП в Python](../oop/oop.ipynb)
