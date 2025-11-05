Паттерн Одиночка (Синглтон) применяется, когда необходим класс, у которого должен быть единственный экземпляр во всей программе. С помощью паттерна Одиночка могут быть реализованы многие паттерны (абстрактная фабрика, строитель, прототип).

В сборнике рецептов приводится простой класс Singleton, которому любой класс может унаследовать, чтобы стать одиночкой.

```python
class Singleton(object):

    def __new__(cls,*dt,**mp):
        if not hasattr(cls,'_inst'):
            cls._inst = super(Singleton, cls).__new__(cls,dt,mp)
        else:
            def init_pass(self,*dt,**mp):pass
            cls.__init__ = init_pass

        return cls._inst


class A(Singleton):

	def __init__(self):
		"""Super constructor
			There is we can open file or create connection to the database
		"""
		print "A init"


a1 = A()
a2 = A()
```

Применение:
- Когда нужно, чтобы у какого-то сервиса или ресурса в системе был только один объект (например, логгер, пул соединений с базой, кэш, конфиг).
- Позволяет избежать конфликта или дублирования состояний.

### Базовый пример

- **Ограничивает создание объекта**: нельзя создать больше одного экземпляра класса.
- **Глобальная точка доступа**: получить экземпляр можно через статический метод или свойство.

```python
class Singleton:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

# Использование
a = Singleton()
b = Singleton()
print(a is b)  # True — это один и тот же объект
```

### Логгер (Logger)

Частая задача: писать логи из разных частей приложения в один и тот же файл/вывод. Логгер должен быть единственным, чтобы логи не дублировались.

```python
class Logger:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def log(self, message):
        print(f"[LOG]: {message}")

# Использование
logger1 = Logger()
logger2 = Logger()
logger1.log("Приложение запущено")
print(logger1 is logger2)  # True
```
### Конфигуратор (Configuration Manager)

Хранит настройки приложения, которые должны быть общими для всех компонентов.

```python
class Config:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.settings = {}
        return cls._instance

    def set(self, key, value):
        self.settings[key] = value

    def get(self, key):
        return self.settings.get(key)

# Использование
cfg1 = Config()
cfg2 = Config()
cfg1.set("debug", True)
print(cfg2.get("debug"))  # True
```

### Подключение к базе данных (Database Connection)

Чтобы избежать открытия множества соединений, используют один-единственный объект подключения.

```python
class DatabaseConnection:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.connection = cls.connect()
        return cls._instance

    @staticmethod
    def connect():
        print("Соединение с базой данных установлено")
        return "connection_object"

    def query(self, sql):
        print(f"Выполняется запрос: {sql}")

# Использование
db1 = DatabaseConnection()
db2 = DatabaseConnection()
db1.query("SELECT * FROM users")
print(db1 is db2)  # True
```
### Кэш (Cache)

Общий кэш, к которому обращаются разные части программы.

```python
class Cache:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.storage = {}
        return cls._instance

    def set(self, key, value):
        self.storage[key] = value

    def get(self, key):
        return self.storage.get(key)

# Использование
cache1 = Cache()
cache2 = Cache()
cache1.set("user_1", {"name": "Ivan"})
print(cache2.get("user_1"))  # {'name': 'Ivan'}
```

### Управление очередями задач (Task Queue Manager)

Общий диспетчер задач, который обеспечивает однородный интерфейс работы с очередью.

```python
class TaskQueueManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.queue = []
        return cls._instance

    def add_task(self, task):
        self.queue.append(task)

    def get_task(self):
        return self.queue.pop(0) if self.queue else None

# Использование
q1 = TaskQueueManager()
q2 = TaskQueueManager()
q1.add_task("task_1")
print(q2.get_task())  # task_1
```
### Варианты создания 

Singleton через обычный класс

```python
class Singleton:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

a = Singleton()
b = Singleton()
print(a is b)  # True
```

Singleton через декоратор

```python
def singleton(cls):
    instances = {}
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return get_instance

@singleton
class MyClass:
    pass

a = MyClass()
b = MyClass()
print(a is b)  # True
```

Singleton через метакласс

```python
class SingletonMeta(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class MyClass(metaclass=SingletonMeta):
    pass

a = MyClass()
b = MyClass()
print(a is b)  # True
```

Singleton через модуль

```python
# my_singleton.py
value = 42

def get_value():
    return value

def set_value(val):
    global value
    value = val
```

```python
# main.py
import my_singleton

print(my_singleton.get_value())  # 42
my_singleton.set_value(100)
print(my_singleton.get_value())  # 100
```

|Вариант|Где применяется|Преимущества|Недостатки|
|---|---|---|---|
|Класс|Любой проект|Просто, понятно|Может быть обойден|
|Декоратор|Для простых классов|Легко расширить|Не наследуется|
|Метакласс|Для многих классов|Гибко, мощно|Сложнее читается|
|Модуль|Конфиги, ресурсы|Природно для Python|Только для глобальных|
