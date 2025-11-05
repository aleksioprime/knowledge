Декоратор `wraps` из модуля `functools` используется при написании **декораторов** в Python. Он помогает **сохранить метаданные** оригинальной функции (например, её имя, документацию и аннотации), когда она оборачивается другой функцией.

```python
import functools

def my_decorator(func):
    def wrapper(*args, **kwargs):
        print("До вызова функции")
        result = func(*args, **kwargs)
        print("После вызова функции")
        return result
    return wrapper  # Возвращаем обёрнутую функцию

@my_decorator
def say_hello():
    """Эта функция говорит "Привет"."""
    print("Привет!")

print(say_hello.__name__)  # Выведет "wrapper", а не "say_hello"
print(say_hello.__doc__)   # Исчезает документация
```

После декорирования, `say_hello.__name__` теперь `"wrapper"`, а `say_hello.__doc__` становится `None`. Это мешает, например, автодокументации.

Функция `wraps` копирует:

- `__name__` (имя функции),
- `__doc__` (документацию),
- `__annotations__` (аннотации аргументов),
- `__module__` (модуль, в котором функция объявлена).

```python
import functools

def my_decorator(func):
    @functools.wraps(func)  # Сохраняем метаданные оригинальной функции
    def wrapper(*args, **kwargs):
        print("До вызова функции")
        result = func(*args, **kwargs)
        print("После вызова функции")
        return result
    return wrapper  # Возвращаем обёрнутую функцию

@my_decorator
def say_hello():
    """Эта функция говорит "Привет"."""
    print("Привет!")

print(say_hello.__name__)  # Теперь "say_hello"
print(say_hello.__doc__)   # Документация восстановлена
```

Где используется:

- **Декораторы логирования**, кэширования и аутентификации.
- **Обёртки над API** (например, Flask-декораторы `@app.route`).
- **Совместимость с introspection** (когда нужно узнать `__name__`, `__doc__`, `help()`).