# Декораторы

Декоратор оборачивает функцию, добавляя действия до и после её вызова без изменения исходного кода. Здесь простой декоратор и декоратор с параметрами — обе конструкции строятся на замыканиях.

## Простой декоратор

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

## Декоратор с аргументами

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

## Связанные темы

- [Области видимости и замыкания](scopes.md) — замыкание, на котором построен декоратор
- [Аргументы и функции как значения](arguments.md) — `*args` и `**kwargs` в обёртке
- [Менеджеры контекста](context_managers.md) — декоратор `@contextmanager`
- [ООП в Python](../oop/README.md)
