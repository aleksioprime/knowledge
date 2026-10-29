# Продвинутые приёмы ООП

Помимо классов и наследования, Python позволяет менять поведение кода во время выполнения и вмешиваться в создание классов и доступ к атрибутам. В заметке — monkey patching, миксины, метаклассы, порядок разрешения методов и дескрипторы: эти механизмы стоят за ORM, валидаторами и фреймворками.

## Monkey patching

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

## Миксин

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

## Метаклассы

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

## Порядок разрешения методов (MRO)

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

## Дескрипторы

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

- [Классы, методы и атрибуты](classes.md) — слоты и декоратор `property` как частный случай дескриптора
- [Магические методы](magic_methods.md) — `__new__` и `__init__`
- [Принципы ООП](principles.md) — наследование и `super()`
- [Функции, итераторы и генераторы](../functions/README.md) — декораторы и протокол итератора
- [Pydantic](../typing/pydantic.md) — валидация полей, похожая на проверку в дескрипторе
