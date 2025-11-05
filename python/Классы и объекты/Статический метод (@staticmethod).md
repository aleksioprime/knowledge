Статический метод в Python реализуется с использованием декоратора `@staticmethod`. Этот декоратор позволяет определить метод, который не привязан ни к экземпляру класса, ни к самому классу. Такие методы могут быть вызваны как через экземпляр класса, так и через сам класс, и они не имеют доступа к атрибутам экземпляра или класса.

```python
class MyClass:
    @staticmethod
    def my_method(x, y):
        return x + y

print(MyClass.my_method(5, 7))  # Выведет: 12

obj = MyClass()
print(obj.my_method(3, 4))       # Выведет: 7
```

Здесь `my_method()` - это статический метод, который принимает два аргумента `x` и `y` и возвращает их сумму. Метод можно вызвать как через класс `MyClass.my_method(5, 7)`, так и через экземпляр класса `obj.my_method(3, 4)`.

Примеры использования

Утилитная функция внутри класса

```python
class MathUtils:
    @staticmethod
    def add(a, b):
        return a + b

# Метод `add` — просто функция, но логически относится к MathUtils
print(MathUtils.add(3, 5))  # 8
```

Проверка данных

```python
class User:
    def __init__(self, username):
        self.username = username

    @staticmethod
    def is_valid_username(username):
        return username.isalnum() and len(username) >= 3
        
# Проверка не зависит ни от объекта, ни от класса, но относится к пользователям
print(User.is_valid_username("vasya123"))  # True
print(User.is_valid_username("!!"))        # False
```

Вызов из экземпляра и класса

```python
class Converter:
    @staticmethod
    def km_to_miles(km):
        return km * 0.621371


# Можно вызывать как через класс, так и через объект

print(Converter.km_to_miles(10))  # 6.21371

c = Converter()
print(c.km_to_miles(10))          # 6.21371
```

Сравнение с classmethod

```python
class Example:
    @staticmethod
    def sm():
        print("Static method")

    @classmethod
    def cm(cls):
        print("Class method, class is", cls)

# Статический метод ничего не знает о классе, а classmethod получает ссылку на класс
Example.sm()   # Static method
Example.cm()   # Class method, class is <class '__main__.Example'>
```