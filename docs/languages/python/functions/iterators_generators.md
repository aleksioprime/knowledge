# Итераторы и генераторы

Цикл `for` проходит по списку, файлу, словарю и собственному классу одинаково — за этим стоит протокол итерации. Понимать его нужно, когда данные не помещаются в память целиком, когда хочется выдавать результат по мере вычисления или когда нужно сделать свой объект пригодным для `for`. Здесь — чем итерируемый объект отличается от итератора, как написать итератор на классах и как генератор с `yield` делает то же самое короче; также `yield from` и генераторные выражения.

## Минимальный пример

```python run
def overdue_tasks(tasks, today):
    for task in tasks:
        if not task['done'] and task['deadline'] < today:
            yield task['title']

tasks = [
    {'title': 'Купить хлеб', 'deadline': 3, 'done': False},
    {'title': 'Позвонить маме', 'deadline': 4, 'done': False},
    {'title': 'Оплатить счёт', 'deadline': 2, 'done': True},
    {'title': 'Сдать отчёт', 'deadline': 9, 'done': False},
]

overdue = overdue_tasks(tasks, today=5)
print(overdue)        # <generator object overdue_tasks at 0x...>
print(next(overdue))  # Купить хлеб
print(list(overdue))  # ['Позвонить маме'] — продолжил с места остановки
print(list(overdue))  # [] — генератор исчерпан

titles = (task['title'].upper() for task in tasks)
print(next(titles))  # КУПИТЬ ХЛЕБ
```

## Как это работает

### Итераторы

#### Итерируемый объект

Итерируемый объект (iterable) — объект, по элементам которого можно пройти по очереди. У него есть метод `__iter__`, который возвращает итератор, или метод `__getitem__`, принимающий индексы. Проще говоря, итерируемый объект умеет выдать итератор.

Список — итерируемый объект, но не итератор: метода `__next__` у него нет.

```python run
a = [1, 2, 3]

print(hasattr(a, '__iter__'))     # True
print(hasattr(a, '__getitem__'))  # True
print(hasattr(a, '__next__'))     # False
```

#### Итератор

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

#### Свой итератор на классах

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

### Генераторы

#### Функция-генератор

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

#### Как работает yield

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

#### Конструкция yield from

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

#### Генераторное выражение

Генераторное выражение (generator expression) похоже на списковое включение, но записывается в круглых скобках и вычисляет элементы лениво:

```python run
gen = (i for i in range(5) if i % 2 == 0)
print(gen)        # <generator object <genexpr> at 0x...>
print(next(gen))  # 0

# Цикл продолжает с места, где остановился next()
for n in gen:
    print(n)  # 2, затем 4
```

## Частые ошибки

- Генератор или итератор перебирают второй раз → второй цикл не выполняется ни разу, `list()` даёт `[]` → для повторного прохода создать генератор заново или сохранить результат в список.
- `len(gen)` или `gen[0]` у генератора → `TypeError: object of type 'generator' has no len()` → если нужны длина и индексы, собрать `list(gen)`; для первого элемента — `next(gen)`.
- `__iter__` в классе-итераторе не возвращает `self` (или возвращает новый объект без `__next__`) → `TypeError: iter() returned non-iterator` в цикле `for` → в итераторе `__iter__` возвращает `self`, в итерируемом объекте — отдельный итератор.
- В функции-генераторе написали `return value`, ожидая его в цикле → значение молча теряется, оно попадает только в `StopIteration.value` → отдавать результат через `yield`.
- `next(gen)` без обработки конца → необработанный `StopIteration`, а внутри другого генератора он превращается в `RuntimeError` → использовать `next(gen, None)` или цикл `for`.

## Когда не использовать

Если данных мало и они нужны целиком — для сортировки, подсчёта длины, обращения по индексу или нескольких проходов, — генератор только добавляет шаг `list(...)`. Списковое включение в таких случаях короче и понятнее генераторного выражения.

Свой итератор на классах имеет смысл, когда объекту нужно хранить состояние между проходами или поддерживать другие методы помимо итерации. Для простого «выдать элементы по очереди» функция-генератор всегда короче, а для перебора коллекции внутри класса достаточно `__iter__` с `yield` или `return iter(self.items)`.

## Связанные темы

- [Корутины на генераторах](coroutines.md) — `send`, `throw` и `close` у генератора
- [Менеджеры контекста](context_managers.md) — генератор под декоратором `@contextmanager`
- [Аргументы и функции как значения](arguments.md) — `map` и `filter` возвращают итераторы
- [Модули collections и itertools](extra.md)
- [ООП в Python](../oop/README.md) — магические методы `__iter__` и `__next__`
- [Память в Python](../advanced/memory.md)
