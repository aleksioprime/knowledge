# ООП в Python

Объектно-ориентированное программирование (ООП) собирает данные и функции, которые с ними работают, в одном объекте. В заметке — как устроены классы в Python: методы и атрибуты, уровни доступа, магические методы, принципы ООП и более глубокие механизмы вроде метаклассов и дескрипторов.

## Классы и объекты

### Справка по классу

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

### Слоты

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

## Методы

### Метод объекта

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

### Метод класса

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

### Статический метод

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

## Атрибуты

### Уровни доступа: public, protected, private

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

### Где хранятся атрибуты и методы

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

### Атрибуты класса и объекта

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

### Декоратор property

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

## Магические методы

### Разница между `__new__` и `__init__`

При создании объекта Python вызывает два метода по очереди:

- `__new__` создаёт объект и возвращает его;
- `__init__` получает готовый объект и заполняет его атрибутами.

```python run
class A:
    def __new__(cls, *args, **kwargs):
        print("New")
        obj = super().__new__(cls, *args, **kwargs)
        return obj

    def __init__(self):
        print("Init")
        self.some = 1

a = A()
```

### Разница между `__str__` и `__repr__`

- `__repr__` — формальное техническое представление объекта, удобное разработчику;
- `__str__` — представление для пользователя, его использует `print()`.

Если `__str__` нет, используется `__repr__`. Если нет и `__repr__`, Python выводит стандартное представление с адресом объекта.

```python run
class Cat:
    name: str

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"Cat(name='{self.name}')"

    def __str__(self):
        return f"It is my cat {self.name}"

cat = Cat("Barsik")
print(cat)        # It is my cat Barsik
print(repr(cat))  # Cat(name='Barsik')
```

## Принципы ООП

### Наследование

Наследник получает весь функционал родительского класса и может расширять его.

```python run
class A:
    a = 1

    def a_method(self):
        print("A instance method")

class B(A):
    b = 2

    def b_method(self):
        print("B instance method")

b = B()

print(b.a)  # 1
print(b.b)  # 2

b.a_method()  # A instance method
b.b_method()  # B instance method
```

### Функция super()

`super()` обращается к методам родительского класса. Чаще всего так вызывают родительский `__init__`, чтобы он инициализировал свою часть атрибутов.

```python run
class A:
    def __init__(self, a):
        self.a = a

class B(A):
    def __init__(self, a, b):
        # Родительский __init__ сам заполнит атрибут a
        super().__init__(a)
        self.b = b

b = B(1, 2)
print(b.a, b.b)  # 1 2
```

### Наследование, композиция и агрегация

Это три способа использовать один класс внутри другого:

- **наследование** — класс получает весь функционал родителя; эта связь задаётся при объявлении класса, и поменять её потом нельзя;
- **композиция** — класс сам создаёт объект другого класса и хранит его в атрибуте; компонент можно заменить на другой класс;
- **агрегация** — класс получает уже готовый объект другого класса снаружи, например в `__init__`.

```python
class A:
    pass

class B(A):
    # Наследование
    pass

class C:
    # Композиция
    def __init__(self):
        self.a = A()

class D:
    # Агрегация
    def __init__(self, a: A):
        self.a = a
```

### Инкапсуляция

Инкапсуляция — объединение данных и функций одной цели в одном классе и сокрытие реализации за понятным интерфейсом. Здесь баланс хранится в приватном атрибуте, а снаружи доступен через свойство, которое не даёт сделать его отрицательным.

```python run
class BankAccount:
    def __init__(self, balance):
        self.__balance = balance

    @property
    def balance(self):
        return self.__balance

    @balance.setter
    def balance(self, value):
        if value >= 0:
            self.__balance = value
        else:
            print("Баланс не может быть отрицательным")

account = BankAccount(1000)

print(account.balance)  # 1000
account.balance = 2000
print(account.balance)  # 2000

account.balance = -100  # Баланс не может быть отрицательным
```

### Полиморфизм

Полиморфизм — возможность работать с объектами разных типов через один интерфейс. В Python различают два вида:

- **параметрический** — одна функция одинаково работает с объектами разных классов, если у них есть нужный метод;
- **ad-hoc** — функция или оператор ведёт себя по-разному в зависимости от типа аргумента: проверки `isinstance` или перегрузка операторов.

```python run
class A:
    def hi(self):
        print(f"Hi from A")

class B:
    def hi(self):
        print(f"Hi from B")

# Параметрический полиморфизм: функции важно только наличие метода hi
def some(obj):
    obj.hi()

a = A()
some(a)  # Hi from A

b = B()
some(b)  # Hi from B

# Ad-hoc полиморфизм: поведение зависит от типа аргумента
def to_json(value):
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, list):
        return '[' + ','.join(to_json(x) for x in value) + ']'

print(to_json([1, 2.5, "a"]))  # [1,2.5,"a"]

# Ad-hoc полиморфизм: перегрузка операторов
class Vector:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def __add__(self, other):
        return Vector(self.x + other.x, self.y + other.y)

v1 = Vector(1, 2)
v2 = Vector(3, 4)
v3 = v1 + v2  # работает благодаря __add__
print(v3.x, v3.y)  # 4 6
```

### Абстрактный класс

Абстрактный класс определяет обязательный интерфейс для потомков. Создать объект абстрактного класса нельзя, а потомок обязан реализовать все его абстрактные методы.

```python run
from abc import ABC, abstractmethod

class Animal(ABC):

    @abstractmethod
    def say_something(self):
        pass

# a = Animal()  # TypeError: нельзя создать объект абстрактного класса

class Cat(Animal):

    def say_something(self):
        print("Meaw")

c = Cat()
c.say_something()  # Meaw
```

## Продвинутые приёмы

### Monkey patching

Monkey patching — изменение поведения кода во время выполнения: метод или атрибут существующего класса или объекта заменяют или добавляют динамически, за пределами объявления класса.

```python run
class MyBaseClass:
    def my_method(self):
        print('Hello from MyBaseClass')

def monkey_patch():
    def new_method(self):
        print('Hello from new_method')
    MyBaseClass.my_method = new_method

monkey_patch()
obj = MyBaseClass()
obj.my_method()  # Hello from new_method
```

### Миксин

Миксин (mixin) — небольшой класс с узкой порцией функциональности, которую подмешивают в другие классы через наследование. Объекты самого миксина не создают.

```python
class Document:
    # Обработка документа
    pass

class S3FileUploadMixin:
    # Загрузка файла в хранилище S3
    pass

class CSVDocument(Document, S3FileUploadMixin):
    # Работа с CSV: обработка документа плюс подмешанная загрузка в S3
    pass
```

### Метаклассы

Метакласс — «класс для классов». Он управляет созданием самих классов: например, может проверить, что класс соответствует определённым требованиям.

```python run
class MyMeta(type):
    def __new__(cls, name, bases, attrs):
        print(f"Создаётся класс: {name}")
        return super().__new__(cls, name, bases, attrs)

# Сообщение печатается уже при объявлении класса, а не при создании объекта
class MyClass(metaclass=MyMeta):
    pass
```

### Порядок разрешения методов (MRO)

Когда у объекта вызывают метод, Python ищет его сначала в самом классе, затем в родительских классах в порядке, который задаёт MRO (Method Resolution Order, порядок разрешения методов).

Поиск идёт слева направо и снизу вверх, при этом сохраняется порядок, уже построенный в MRO родителей. Если метод есть в нескольких классах, используется тот, чей класс стоит в MRO раньше.

```python run
class O: ...

class A(O): ...
class B(O): ...
class C(O): ...
class D(O): ...
class E(O): ...

class K1(A, B, C): ...
class K2(B, D): ...
class K3(C, D, E): ...

class Z(K1, K2, K3): ...

print(*[cls.__name__ for cls in Z.__mro__], sep=" -> ")
```

### Дескрипторы

Дескриптор (descriptor) — объект, который определяет, что происходит при обращении к атрибуту другого объекта: «когда обращаются к этому атрибуту — делай вот это».

Простейший дескриптор реализует только `__get__`:

```python run
class Descriptor:
    def __get__(self, instance, owner):
        print("get")
        return 42

class A:
    x = Descriptor()
    y = 41

a = A()
print(a.x, a.y)  # a.x не читает поле, а вызывает Descriptor.__get__
```

Полноценный дескриптор умеет ещё и проверять значение при записи. Методы срабатывают в разные моменты:

- `__set_name__` — один раз при создании класса `Product`: дескриптор узнаёт, под каким именем он объявлен;
- `__set__` — при каждом присваивании атрибута, в том числе в `__init__`;
- `__get__` — при каждом чтении атрибута.

```python run
class Item:
    def __set_name__(self, owner, name):
        print(f"Устанавливаем имя атрибута: {name} для класса {owner.__name__}")
        self.public_name = name
        self.private_name = "_" + name

    def __get__(self, obj, objtype=None):
        value = getattr(obj, self.private_name, None)
        print(f"Получаем значение {self.public_name}: {value}")
        return value

    def __set__(self, obj, value):
        if not isinstance(value, str):
            raise ValueError("Аргумент должен быть строкой")
        print(f"Устанавливаем значение {self.public_name}: {value}")
        setattr(obj, self.private_name, value)

class Product:
    name = Item()  # здесь вызывается Item.__set_name__(Product, "name")

    def __init__(self, name):
        self.name = name  # Item.__set__

product = Product("Book")
product.name = "Notebook"  # Item.__set__
print(product.name)        # Item.__get__
```

## Связанные темы

- [dataclasses](../typing/dataclasses.md) — классы для хранения данных без шаблонного кода
- [Функции, итераторы и генераторы](../function/function.md) — декораторы и протокол итератора
- [Подсказки типов](../typing/type_hints.md)
- [Pydantic](../typing/pydantic.md)
