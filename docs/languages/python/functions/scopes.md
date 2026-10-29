# Области видимости и замыкания

Как функция находит переменные и что происходит, когда внутренняя функция запоминает переменные внешней. Правило LEGB, операторы `global` и `nonlocal` и замыкания — основа для понимания декораторов.

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

## Связанные темы

- [Аргументы и функции как значения](arguments.md)
- [Декораторы](decorators.md) — замыкание внутри декоратора
- [Основы Python](../basics/README.md)
