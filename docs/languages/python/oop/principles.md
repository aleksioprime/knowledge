# Принципы ООП

Четыре принципа объектно-ориентированного программирования — наследование, инкапсуляция, полиморфизм и абстракция — объясняют, зачем вообще собирать данные и функции в классы. В заметке каждый принцип показан на коротком примере, а также разобраны `super()`, композиция и агрегация как альтернативы наследованию.

## Наследование

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

## Функция super()

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

## Наследование, композиция и агрегация

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

## Инкапсуляция

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

## Полиморфизм

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

## Абстрактный класс

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

## Связанные темы

- [Классы, методы и атрибуты](classes.md) — уровни доступа и декоратор `property`, на которых строится инкапсуляция
- [Магические методы](magic_methods.md) — `__new__`, `__init__`, `__str__` и `__repr__`
- [Продвинутые приёмы ООП](advanced.md) — миксины и порядок разрешения методов при множественном наследовании
- [Принципы проектирования](../../../backend/design/principles.md)
- [dataclasses](../typing/dataclasses.md) — классы для хранения данных без шаблонного кода
