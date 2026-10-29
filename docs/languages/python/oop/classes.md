# Классы, методы и атрибуты

Класс нужен, когда данные и действия над ними ходят вместе: у задачи есть название и статус, её можно завершить или создать из строки файла. Чтобы такой код не превращался в набор словарей и функций, важно понимать, чем метод объекта отличается от метода класса и статического, где живут атрибуты, как обозначают уровни доступа и когда вместо поля нужен `property` или слоты.

## Минимальный пример

```python run
class Task:
    count = 0  # атрибут класса: общий для всех задач

    def __init__(self, title, done=False):
        self.title = title  # атрибут объекта: у каждой задачи свой
        self.done = done
        Task.count += 1

    def complete(self):
        self.done = True

    @property
    def status(self):
        return 'готово' if self.done else 'в работе'

    @classmethod
    def from_line(cls, line):
        title, done = line.split(';')
        return cls(title, done == '1')


task = Task.from_line('Купить хлеб;0')
task.complete()
print(task.title, task.status)  # Купить хлеб готово
print(Task.count)  # 1
```

## Как это работает

### Классы и объекты

#### Справка по классу

Функция `help()` показывает справку о классе объекта: его методы, атрибуты и строки документации. Функция `dir()` возвращает список всех атрибутов и методов объекта или класса, включая унаследованные.

```python run
class Person:
    name: str

    def __init__(self, name):
        self.name = name

    def say_hi(self):
        print(f"Hi, my name is {self.name}")

p = Person("Mike")

help(p)

dir(p)
```

#### Слоты

Обычно атрибуты объекта хранятся в словаре `__dict__`:

```python run
class User:
    def __init__(self, name: str):
        self.name = name

u = User("Alice")
print(u.__dict__)  # {'name': 'Alice'}
```

Если объявить `__slots__`, Python вместо `__dict__` выделит фиксированные ячейки под перечисленные атрибуты. Это экономит память и ускоряет доступ, но запрещает добавлять произвольные атрибуты.

```python run
class User:
    __slots__ = ('name',)

    def __init__(self, name: str):
        self.name = name

u = User("Alex")
print(u.__slots__)  # ('name',)
# print(u.__dict__)  # AttributeError: 'User' object has no attribute '__dict__'
# u.age = 30         # AttributeError: 'User' object has no attribute 'age'
```

### Методы

#### Метод объекта

Обычный метод вызывается у объекта. Первым параметром он получает `self` — ссылку на текущий объект.

```python run
class Person:

    def __init__(self, name):
        self.name = name

    def say_hi(self):
        print(f"Hi, my name is {self.name}")

p = Person("Mike")
p.say_hi()  # Hi, my name is Mike
```

#### Метод класса

Метод класса (`@classmethod`) можно вызвать без создания объекта. Первым параметром он получает `cls` — ссылку на текущий класс.

```python run
class Person:
    workplace = "My Company"

    @classmethod
    def get_my_workplace(cls):
        return cls.workplace

print(Person.get_my_workplace())  # My Company

p = Person()
print(p.get_my_workplace())  # My Company
```

#### Статический метод

Статический метод (`@staticmethod`) не принимает ни `self`, ни `cls`. Это обычная функция, которая логически относится к классу. Вызывать её можно и через класс, и через объект.

```python run
from datetime import datetime

class A:
    @staticmethod
    def get_current_datetime():
        return datetime.now()

print(A.get_current_datetime())  # текущие дата и время

a = A()
print(a.get_current_datetime())
```

### Атрибуты

#### Уровни доступа: public, protected, private

В Python нет модификаторов доступа к атрибутам и методам. Уровни доступа обозначают соглашением об именах:

- `public` — без подчёркивания, доступен всем;
- `_protected` — одно подчёркивание: «внутреннее, снаружи не трогать», но Python этого не запрещает;
- `__private` — два подчёркивания: Python меняет имя на `_ИмяКласса__имя` (name mangling), поэтому по исходному имени снаружи атрибут не найти.

```python run
class A:
    public = 123
    _protected = 123
    __private = 123

a = A()
# print(a.__private)  # AttributeError: 'A' object has no attribute '__private'
# Но через изменённое имя доступ есть
print(a._A__private)  # 123
```

#### Где хранятся атрибуты и методы

Атрибуты класса и все его методы — обычные, классовые и статические — лежат в словаре класса `__dict__`. Видно и изменённое имя приватного атрибута `_A__private`.

```python run
class A:
    public = 123
    _protected = 123
    __private = 123

    def some(self):
        print("Instance method")

    @classmethod
    def some_classmethod(cls):
        print("Class method")

    @staticmethod
    def some_staticmethod():
        print("Static method")

print(A.__dict__)
```

#### Атрибуты класса и объекта

Атрибут класса объявляется в теле класса и общий для всех объектов. Атрибут объекта задаётся через `self` и у каждого объекта свой.

```python run
class A:
    class_attr = 1

    def __init__(self, attr):
        self.instance_attr = attr

a = A(2)
print(a.class_attr)     # 1
print(a.instance_attr)  # 2
```

#### Декоратор property

Декоратор `@property` превращает метод в вычисляемый атрибут: его читают как поле, без скобок. Вместе с сеттером (`@имя.setter`) можно управлять и присваиванием — например, проверять новое значение.

```python run
class Person:
    first_name: str
    last_name: str

    def __init__(self, first_name: str, last_name: str):
        self.first_name = first_name
        self.last_name = last_name

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @full_name.setter
    def full_name(self, value):
        name = value.split()
        self.first_name = name[0]
        self.last_name = name[1]

p = Person("Mike", "Jagger")
print(p.full_name)  # Mike Jagger

p.full_name = "John Walker"
print(p.full_name)  # John Walker
```

## Частые ошибки

- Изменяемый атрибут класса как значение по умолчанию (`tags = []` в теле класса) → список общий для всех объектов, добавили тег одной задаче — он появился у всех → создавать список в `__init__`: `self.tags = []`.
- Метод объявлен без `self` → `TypeError: complete() takes 0 positional arguments but 1 was given` → первым параметром метода объекта всегда `self`, у метода класса — `cls`, иначе ставить `@staticmethod`.
- Обращение к `property` со скобками или к методу без скобок → `TypeError: 'str' object is not callable` либо в выводе `<bound method ...>` → свойство читают как поле (`task.status`), метод вызывают (`task.complete()`).
- Наследник класса со `__slots__` сам не объявляет `__slots__` → у объектов наследника снова появляется `__dict__`, экономии памяти нет → объявить `__slots__` в каждом классе цепочки, хотя бы пустой кортеж.
- Сеттер `property` присваивает атрибут с тем же именем (`self.name = value` внутри `name.setter`) → бесконечная рекурсия, `RecursionError` → хранить значение под другим именем, например `self._name`.

## Когда не использовать

Класс не нужен, если у него только `__init__` и один метод: это обычная функция, которая принимает данные аргументами. Если объект только хранит поля без поведения, проще взять [dataclass](../typing/dataclasses.md) или `NamedTuple` — они сами сгенерируют `__init__`, `__repr__` и сравнение.

Слоты и приватные атрибуты тоже не стоит применять заранее. `__slots__` окупается на сотнях тысяч однотипных объектов, а в обычном коде только мешает добавлять атрибуты и использовать `__dict__`. Двойное подчёркивание усложняет наследование и тестирование; для «внутреннего» атрибута достаточно одного подчёркивания.

## Связанные темы

- [Магические методы](magic_methods.md) — `__new__`, `__init__`, `__str__` и `__repr__`
- [Принципы ООП](principles.md) — наследование, инкапсуляция, полиморфизм, абстракция
- [Продвинутые приёмы ООП](advanced.md) — monkey patching, миксины, метаклассы, MRO, дескрипторы
- [dataclasses](../typing/dataclasses.md) — классы для хранения данных без шаблонного кода
- [Подсказки типов](../typing/type_hints.md)
