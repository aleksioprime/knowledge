Метод класса в Python реализуется с использованием декоратора `@classmethod`. Этот декоратор позволяет определить метод, который принимает первым аргументом класс (`cls` по соглашению) вместо экземпляра объекта. Это позволяет методу работать с атрибутами класса, а не с атрибутами экземпляра. Метод класса в Python реализуется с использованием декоратора @classmethod. Этот декоратор позволяет определить метод, который принимает первым аргументом класс (cls по соглашению) вместо экземпляра объекта. Это позволяет методу работать с атрибутами класса, а не с атрибутами экземпляра.

```python
class MyClass:
    count = 0
    
    def __init__(self):
        MyClass.count += 1
        
    @classmethod
    def instance_count(cls):
        return cls.count

print(MyClass.instance_count())  # Выведет: 0

a = MyClass()
print(MyClass.instance_count())  # Выведет: 1

b = MyClass()
print(MyClass.instance_count())  # Выведет: 2
```

Здесь `instance_count()` - это метод класса, который возвращает количество созданных экземпляров класса `MyClass`.

Применение:

##### **Работа с классом, а не с конкретным объектом**

- **Обычный метод** работает с конкретным экземпляром (`self`), т.е. с уже созданным объектом.
- **Метод класса** работает с самим классом (`cls`), даже если объекта ещё нет.

##### **Фабричные методы — альтернативные способы создания объектов**

Иногда нужно создавать объект не через стандартный `__init__`, а из других данных (например, из строки, файла, БД, других объектов).  Если сделать это обычным методом — для вызова нужен уже существующий объект, что нелогично.

```python
class User:
    def __init__(self, username):
        self.username = username

    @classmethod
    def from_full_name(cls, full_name):
        username = full_name.lower().replace(' ', '_')
        return cls(username)

user = User.from_full_name("Иван Иванов")
print(user.username)  # иван_иванов

# Если бы `from_full_name` был обычным методом, пришлось бы создавать «пустой» объект, чтобы его вызвать, что нелогично.
```

##### **Поддержка наследования и расширяемость**

Если использовать classmethod, то при наследовании твой фабричный метод всегда будет возвращать объект именно текущего класса-наследника, а не базового!  
Это очень удобно для больших проектов и позволяет писать расширяемый код.

```python
class Animal:
    @classmethod
    def from_name(cls, name):
        return cls(name)

class Dog(Animal):
    def __init__(self, name):
        self.name = name

dog = Dog.from_name("Шарик")
print(type(dog))  # <class '__main__.Dog'>
```

##### **Работа с атрибутами класса**

Иногда нужно изменить или получить общий для всех объектов параметр класса (например, счётчик объектов, кэш, настройки и т.д.).

```python
class Connection:
    total_connections = 0

    def __init__(self):
        type(self).total_connections += 1

    @classmethod
    def get_total_connections(cls):
        return cls.total_connections

print(Connection.get_total_connections())  # 0
c1 = Connection()
print(Connection.get_total_connections())  # 1
```

##### **Удобство: не нужно создавать объект ради метода**

Если действие логически относится ко всему классу, а не к конкретному объекту — лучше использовать classmethod.

Например:
- Создать объект из файла (User.from_file("users.json"))
- Получить общее число созданных объектов
- Создать разные объекты через разные конструкторы (User.from_email, User.from_id, User.from_json и т.д.)