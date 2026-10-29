# Менеджеры контекста

Конструкция `with` гарантирует освобождение ресурса при выходе из блока, даже при ошибке. Свой менеджер контекста можно написать классом с `__enter__` и `__exit__` или генератором с декоратором `@contextmanager`.

## Конструкция with

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

## Класс-менеджер контекста

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

## Декоратор contextmanager

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

- [Итераторы и генераторы](iterators_generators.md) — генераторы и `yield`
- [Декораторы](decorators.md)
- [ООП в Python](../oop/README.md) — магические методы `__enter__` и `__exit__`
- [Асинхронность в Python](../concurrency/async.md)
