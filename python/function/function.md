# Функции, итераторы и генераторы

Заметка о том, как функции видят переменные, принимают аргументы и превращаются в более сложные конструкции: замыкания, декораторы, генераторы, корутины и менеджеры контекста.

## Области видимости

### Правило LEGB

Когда функция обращается к имени, Python ищет его в четырёх областях видимости по порядку:

- **Local** — локальная область текущей функции;
- **Enclosing** — области внешних (объемлющих) функций;
- **Global** — глобальная область модуля;
- **Built-in** — встроенные имена Python (`str`, `len`, `print`).

Используется первое найденное значение. В примере имя `str` по очереди перекрывается на каждом уровне:

```python run
print(str)  # <class 'str'>

str = "global"

def outer():
    str = "enclosing"

    def inner():
        str = "local"
        print(str)  # local

    inner()
    print(str)  # enclosing

outer()
print(str)  # global

# Возвращаем встроенный str, чтобы не сломать остальной код
import builtins
str = builtins.str
```

### Операторы global и nonlocal

Присваивание внутри функции по умолчанию создаёт локальную переменную. Чтобы изменить переменную из другой области, её нужно объявить:

- `global` — переменная из глобальной области модуля;
- `nonlocal` — переменная из ближайшей внешней функции.

```python run
a = 0
b = 0

def outer():
    a = 1
    b = 1

    def inner():
        global a
        a = 2
        nonlocal b
        b = 2

    inner()
    # Локальная a в outer не изменилась, а b изменилась через nonlocal
    print(f"a = {a} b = {b}")  # a = 1 b = 2

outer()
# Глобальная a изменилась через global, а глобальная b осталась прежней
print(f"a = {a} b = {b}")  # a = 2 b = 0
```

## Замыкание

Замыкание (closure) — функция, которая запоминает переменные из внешней области видимости даже после того, как внешняя функция завершила работу.

Например, функция сложения с запомненным слагаемым:

```python run
def add_number(a):
    def add(b):
        return a + b

    return add

# add_number(5) вернула внутреннюю функцию add, которая помнит a = 5
add_five = add_number(5)
print(add_five(2))   # 7
print(add_five(10))  # 15
```

Замыкание может не только читать, но и изменять запомненную переменную — для этого нужен `nonlocal`. Так получается счётчик:

```python run
def make_counter():
    count = 0

    def inner():
        nonlocal count
        count += 1
        return count

    return inner

# make_counter() уже отработала, но inner() помнит переменную count
counter = make_counter()

print(counter())  # 1
print(counter())  # 2
print(counter())  # 3

# Кортеж ячеек (cell), в которых Python хранит захваченные переменные
print(counter.__closure__)
```

## Аргументы функции

### Передача изменяемых объектов

Python передаёт в функцию ссылку на объект, а не его копию. Поэтому функция может изменить переданный список, и изменение будет видно снаружи:

```python run
a = [1, 2, 3]

def some(arg):
    # Аргумент внутри функции — тот же объект, что и снаружи
    print(arg is a)  # True
    arg.append(4)
    return arg

print(some(a))  # [1, 2, 3, 4]
print(a)        # [1, 2, 3, 4] — оригинал тоже изменился
```

### Изменяемое значение по умолчанию

Значение по умолчанию вычисляется один раз — когда Python создаёт функцию. Дальше при каждом вызове используется тот же самый объект, а не новый. Если это список, он будет накапливать значения между вызовами:

```python run
# Как неправильно
def some(a=[]):
    a.append(1)
    return a

print(some())    # [1]
print(some([]))  # [1]
print(some())    # [1, 1] — добавилось к списку из первого вызова
print(some([]))  # [1]

# Как правильно
def some(a=None):
    if a is None:
        a = []
    a.append(1)
    return a

print(some())    # [1]
print(some([]))  # [1]
print(some())    # [1]
print(some([]))  # [1]
```

### *args и **kwargs

Функция может принимать произвольное число аргументов:

- `*args` — позиционные аргументы, собираются в кортеж;
- `**kwargs` — именованные аргументы, собираются в словарь.

```python run
def some(*args, **kwargs):
    print(locals())  # {'args': (1, 2, 3), 'kwargs': {'a': 1, 'b': 2}}

some(1, 2, 3, a=1, b=2)
```

## Функции как значения

### Лямбда-функции

Лямбда-функция (lambda) — короткая безымянная функция из одного выражения. Её удобно передавать туда, где ждут функцию, например в параметр `key`.

Найдём ключ словаря с наибольшим значением: `max` перебирает ключи, а лямбда говорит сравнивать их по значениям.

```python run
a = {
    1: 3,
    2: 2,
    3: 1
}

print(max(a, key=lambda x: a[x]))  # 1
```

### Функции высшего порядка: map и filter

Функция высшего порядка принимает другую функцию как аргумент. Встроенные `map` и `filter` возвращают ленивые итераторы — значения вычисляются, только когда их запрашивают:

- `map` применяет функцию к каждому элементу;
- `filter` оставляет элементы, для которых функция вернула истину.

```python run
a = [i for i in range(5)]

a_map = map(lambda x: x**2, a)
print(a_map)        # <map object at 0x...>
print(list(a_map))  # [0, 1, 4, 9, 16]

a_filter = filter(lambda x: x % 2 == 0, a)
print(a_filter)        # <filter object at 0x...>
print(list(a_filter))  # [0, 2, 4]
```

## Декораторы

### Простой декоратор

Декоратор (decorator) — функция, которая принимает другую функцию и возвращает её обёртку. Обёртка выполняет дополнительные действия до и после вызова исходной функции, не меняя её код.

Внутри декоратора — замыкание: обёртка `wrapper` помнит исходную функцию `func`, пробрасывает в неё все аргументы и возвращает её результат.

```python run
def decorator(func):
    def wrapper(*args, **kwargs):
        print("BEFORE")
        result = func(*args, **kwargs)
        print("AFTER")
        return result

    return wrapper

@decorator
def say_hi(name):
    print(f"Hi, my name is {name}")
    return 1

say_hi('John')
```

### Декоратор с аргументами

Чтобы передать в декоратор параметры, добавляют ещё один внешний слой: `repeat(n)` принимает аргументы и возвращает сам декоратор.

```python run
def repeat(n):
    def decorator(func):
        def wrapper(*args, **kwargs):
            print("BEFORE")
            result = []
            for _ in range(n):
                r = func(*args, **kwargs)
                result.append(r)
            print("AFTER")
            return result

        return wrapper
    return decorator

@repeat(3)
def say_hi(name):
    print(f"Hi, my name is {name}")
    return 1

say_hi("Alex")
```

## Итераторы

### Итерируемый объект

Итерируемый объект (iterable) — объект, по элементам которого можно пройти по очереди. У него есть метод `__iter__`, который возвращает итератор, или метод `__getitem__`, принимающий индексы. Проще говоря, итерируемый объект умеет выдать итератор.

Список — итерируемый объект, но не итератор: метода `__next__` у него нет.

```python run
a = [1, 2, 3]

print(hasattr(a, '__iter__'))     # True
print(hasattr(a, '__getitem__'))  # True
print(hasattr(a, '__next__'))     # False
```

### Итератор

Итератор (iterator) — объект, который запоминает текущее положение и выдаёт элементы один за другим. Он реализует метод `__next__`: тот возвращает следующий элемент или выбрасывает исключение `StopIteration`, если элементы закончились.

Многие встроенные функции возвращают итераторы: `enumerate`, `zip`, `map`. Объект файла, который возвращает `open`, — тоже итератор: он читает файл построчно.

```python run
a = [1, 2, 3]

i = iter(a)
print(hasattr(i, '__iter__'))     # True
print(hasattr(i, '__getitem__'))  # False
print(hasattr(i, '__next__'))     # True

print(next(i))  # 1
print(next(i))  # 2
```

### Свой итератор на классах

Итерируемый объект и итератор можно разделить на два класса. `Range` итерируемый, потому что его метод `__iter__` отдаёт итератор. `RangeIterator` — итератор: его `__next__` выдаёт новые значения, пока не дойдёт до конца диапазона, а затем выбрасывает `StopIteration`.

```python run
class Range:
    def __init__(self, stop_value: int):
        self.current = -1
        self.stop_value = stop_value - 1

    def __iter__(self):
        return RangeIterator(self)

class RangeIterator:
    def __init__(self, container):
        self.container = container

    def __next__(self):
        if self.container.current < self.container.stop_value:
            self.container.current += 1
            return self.container.current
        raise StopIteration

_range = Range(5)
for i in _range:
    print(i, end=' ')  # 0 1 2 3 4
```

Объект может быть итерируемым и итератором одновременно — для этого в классе реализуют оба метода, а `__iter__` возвращает сам объект.

Цикл `for` вызывает `__iter__` и `__next__` автоматически. Здесь то же самое сделано вручную:

```python run
class Range:
    def __init__(self, stop_value: int):
        self.current = -1
        self.stop_value = stop_value - 1

    def __iter__(self):
        return self

    def __next__(self):
        if self.current < self.stop_value:
            self.current += 1
            return self.current
        raise StopIteration

iterable = Range(5)
iterator = iter(iterable)
while True:
    try:
        value = next(iterator)
        print(value, end=' ')  # 0 1 2 3 4
    except StopIteration:
        break
```

Итератор не обязан заканчиваться. `Counter` никогда не выбрасывает `StopIteration`, поэтому в цикле `for` по нему нужен явный `break`:

```python run
class Counter:
    current_value: int

    def __init__(self):
        self.current_value = 0

    def __iter__(self):
        return self

    def __next__(self):
        current_value = self.current_value
        self.current_value += 1
        return current_value

c = Counter()

i = iter(c)
print(next(i))  # 0
print(next(i))  # 1
```

## Генераторы

### Функция-генератор

Генератор (generator) — функция, которая возвращает значения по очереди через `yield` и не хранит в памяти весь набор сразу.

В объекте-генераторе определены методы `__iter__` и `__next__`, то есть он реализует протокол итератора. Поэтому любой генератор в Python — итератор.

Тот же `Range`, что выше, но генератором — кода намного меньше:

```python run
def gen_range(stop_value):
    """Имитирует поведение range(stop_value)"""
    stop_value = stop_value - 1
    current = -1
    while current < stop_value:
        current += 1
        yield current

for x in gen_range(5):
    print(x, end=' ')  # 0 1 2 3 4
```

### Как работает yield

Вызов функции-генератора не выполняет её код, а возвращает объект генератора. Код выполняется по частям при каждом `next()`:

```python run
def some():
    yield 1

obj = some()
print(obj)        # <generator object some at 0x...>
print(next(obj))  # 1
# Значения закончились — следующий next(obj) выбросит StopIteration
```

Если в функции несколько `yield`, генератор запоминает, на каком из них остановился, и при следующем вызове продолжает с этого места:

```python run session=yield
def some():
    print("First yield")
    yield 1
    print("Second yield")
    yield 2
    print("Third yield")
    yield 3

obj = some()
print("Start test yield")
print(next(obj))
print(next(obj))
print(next(obj))
print("Finish test yield")
```

`yield from` передаёт часть генерации другому генератору — здесь генератору `some` из предыдущего примера:

```python run session=yield
def new():
    print("Before yield from")
    yield from some()
    print("After yield from")
    yield 4
    yield 5

obj = new()
for o in obj:
    print(o)
```

### Конструкция yield from

`yield from` делегирует генерацию любому итерируемому объекту — списку или другому генератору. Она заменяет цикл `for item in ...: yield item`:

```python run
numbers = [1, 2, 3]

def func_simple():
    for item in numbers:
        yield item

for item in func_simple():
    print(item)

def func():
    yield from numbers        # делегирование списку numbers
    yield from func_simple()  # делегирование генератору func_simple()

for item in func():
    print(item, end=' ')  # 1 2 3 1 2 3
```

### Генераторное выражение

Генераторное выражение (generator expression) похоже на списковое включение, но записывается в круглых скобках и вычисляет элементы лениво:

```python run
gen = (i for i in range(5) if i % 2 == 0)
print(gen)        # <generator object <genexpr> at 0x...>
print(next(gen))  # 0

# Цикл продолжает с места, где остановился next()
for n in gen:
    print(n)  # 2, затем 4
```

## Корутины на генераторах

Корутина, или сопрограмма (coroutine), — функция, выполнение которой можно приостанавливать и возобновлять, передавая в неё данные в момент возобновления.

До Python 3.5 корутины делали на генераторах (generator-based coroutines). Генератор останавливается на `yield`, ждёт значение, получает его через метод `send()` и продолжает работу с места остановки.

### Передача данных через send

Перед первым `send()` корутину нужно запустить вызовом `next()` — так она дойдёт до первого `yield` и встанет в ожидание.

```python run
def coro():
    # Ждёт значение, отправленное внутрь генератора
    value = yield
    print(value)

print(coro())  # <generator object coro at 0x...>

c = coro()
next(c)  # выполняет код до первого yield
try:
    c.send(10)  # передаёт 10 в корутину, она печатает его и завершается
except StopIteration:
    # После print больше нет yield — генератор закончился,
    # и send() сообщает об этом исключением StopIteration
    print("Корутина завершилась")
c.close()  # для завершённого генератора ничего не делает
```

Чтобы `send()` вернул результат, после приёма значения нужен ещё один `yield`:

```python run
def coro():
    value = yield
    yield value * 2

gen = coro()
next(gen)
# send() передаёт 10 и получает значение из второго yield
print(gen.send(10))  # 20
```

### Исключения и закрытие: throw и close

Метод `throw()` выбрасывает исключение внутри корутины в точке, где она остановилась. Корутина может его перехватить и продолжить работу.

Метод `close()` завершает корутину: внутри неё в точке остановки возникает исключение `GeneratorExit`.

```python run
def coro_with_exception():
    try:
        yield
    except ValueError:
        yield "Исключение ValueError поймано"

c = coro_with_exception()
next(c)
print(c.throw(ValueError))  # Исключение ValueError поймано

def coro_to_close():
    try:
        yield 1
    except GeneratorExit:
        print("Генератор закрывается")

c = coro_to_close()
next(c)
c.close()  # Генератор закрывается
```

### Пример: расчёт вклада

Корутина один раз вычисляет множитель для процентов, а затем в бесконечном цикле принимает суммы вкладов и возвращает итоговые суммы.

В цикле два `yield`: первый принимает вклад, второй отдаёт результат. Поэтому после каждого `send()` вызывается `next()`, чтобы вернуть корутину к ожиданию следующего значения.

```python run
import math

def cash_return_coro(percent, years):
    """Считает сумму вклада с учётом процентов за указанный срок"""
    value = math.pow(1 + percent / 100, years)
    while True:
        try:
            deposit = yield
            yield round(deposit * value, 2)
        except GeneratorExit:
            print('Выход из корутины')
            raise

coro = cash_return_coro(5, 5)
next(coro)
values = [1000, 2000, 5000, 10000, 100000]
for item in values:
    print(coro.send(item))
    next(coro)
coro.close()  # Выход из корутины
```

### Корутины и потоки

Поток (thread) — составная часть процесса, который выполняется в операционной системе. Корутины работают внутри одного потока или пула потоков. Но принцип похож на работу потоков: корутины останавливаются и возобновляются, ждут друг друга и обмениваются данными.

## Менеджеры контекста

### Конструкция with

Менеджер контекста (context manager) даёт доступ к ресурсу внутри блока `with` и гарантирует, что ресурс освободится при выходе из блока — даже если внутри возникла ошибка.

Типичный пример — работа с файлом: после блока `with` файл закрывается автоматически.

```python run
# Создаём файл для примера
with open('data.txt', 'w') as file:
    file.write('apple\nbanana\ncherry')

with open('data.txt', 'r') as file:
    content = file.read()

print(file.closed)  # True
print(content)
```

### Класс-менеджер контекста

Свой менеджер контекста — класс с двумя методами:

- `__enter__` вызывается при входе в блок `with`; то, что он вернёт, попадает в переменную после `as`;
- `__exit__` вызывается при выходе из блока, в том числе при ошибке.

```python run
class Connection:
    def __enter__(self):
        print("Открываю соединение")
        self.connection = 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("Закрываю соединение при выходе или ошибке")
        self.connection = 0

with Connection() as obj:
    print("Внутри контекста:", obj.connection)  # Внутри контекста: 1

print("После выхода:", obj.connection)  # После выхода: 0
```

### Декоратор contextmanager

Менеджер контекста можно написать и функцией-генератором с декоратором `@contextmanager`. Код до `yield` выполняется при входе в блок, значение из `yield` попадает в переменную после `as`, а код в `finally` выполняется при выходе.

```python run
from contextlib import contextmanager

@contextmanager
def connection():
    print("Открываю соединение")
    conn = {"state": 1}
    try:
        yield conn
    finally:
        print("Закрываю соединение")
        conn["state"] = 0

with connection() as conn:
    print("Внутри контекста:", conn["state"])  # Внутри контекста: 1

print("После выхода:", conn["state"])  # После выхода: 0
```

## Связанные темы

- [Модули collections и itertools](extra.md)
- [ООП в Python](../oop/oop.md) — магические методы `__iter__`, `__next__`, `__enter__`, `__exit__`
- [Асинхронность в Python](../multitask/async.md) — современные корутины на `async`/`await`
- [Подсказки типов](../typing/type_hints.md)
