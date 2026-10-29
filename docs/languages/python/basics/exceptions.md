# Обработка исключений

Конструкция `try`/`except`/`else`/`finally`, порядок блоков `except`, повторный выброс ошибки, группы исключений и собственные классы исключений. Это нужно, чтобы программа предсказуемо реагировала на ошибки, а не падала или молча глотала их.

```python run
a = 10
b = 0

try:
    # код, который может завершиться ошибкой
    result = a / b
except ZeroDivisionError:
    # выполняется, если в try возникла указанная ошибка (блоков except может быть несколько)
    result = None  # резервное значение
else:
    # выполняется, если в try ошибок не было
    ...
finally:
    # выполняется в любом случае
    ...

print(result)  # None
```

## Несколько блоков `except`

Срабатывает первый подходящий блок `except`, поэтому более конкретные исключения ставят выше общих.

```python run
try:
    raise ValueError(1)
except ValueError:
    print("ValueError")  # сработает этот блок
except Exception:
    # если поставить этот блок первым, сработает он: Exception — базовый класс для ValueError
    print("Exception")
```

В одном `except` можно перечислить несколько типов кортежем. Если исключение не подошло ни под один `except`, его обработает интерпретатор — программа завершится с ошибкой.

```python run
try:
    raise TypeError(1)
except (ValueError, TypeError):
    print("Value or Type Error")
except SyntaxError:
    print("SyntaxError")
```

`except` без типа ловит всё, включая исключения, которые не наследуют `Exception`, а наследуют напрямую `BaseException` — например, `GeneratorExit`, `KeyboardInterrupt`, `SystemExit`.

```python run
try:
    raise GeneratorExit
except Exception:
    print("Exception")
except:
    print("Base Exception")
```

## Повторный выброс исключения (re-raise)

Если внутренний обработчик поймал ошибку, внешний её уже не увидит. Чтобы передать ошибку дальше, во внутреннем обработчике пишут `raise` без аргументов.

```python run
try:
    try:
        raise ValueError(1)
    except Exception:
        print("INNER")
        raise  # без этой строки OUTER не напечатается
except Exception:
    print("OUTER")
```

## Группы исключений

В Python 3.11 появились `ExceptionGroup` и `BaseExceptionGroup`. Они позволяют выбросить сразу несколько исключений — например, из задач, которые работали параллельно в `asyncio`.

```python run
# Блок except перехватывает всю группу целиком
try:
    eg = ExceptionGroup(
        "exception group",
        [
            TypeError("Некорректный тип"),
            ValueError("Неверное значение"),
        ]
    )
    raise eg
except ExceptionGroup as e:
    print("Полностью пойманная группа исключений:")
    print(e)

# Синтаксис except* обрабатывает отдельные типы исключений из группы
try:
    eg = ExceptionGroup(
        "exception group",
        [
            TypeError("Некорректный тип"),
            ValueError("Неверное значение"),
        ]
    )
    raise eg
except* TypeError as e:
    print("\nОбработка TypeError:")
    print(e)
except* ValueError as e:
    print("\nОбработка ValueError:")
    print(e)
```

## Свой тип исключения

Собственный класс исключения делает сообщения об ошибках информативнее и позволяет передать с ошибкой дополнительные данные. Пример ниже специально завершается ошибкой `Custom: My Error`.

```python run
class Custom(Exception):
    def __init__(self, value, message="Default message"):
        self.value = value
        self.message = message
        super().__init__(self.message)

raise Custom(500, message="My Error")
```

## Связанные темы

- [Генераторы коллекций и перебор](iteration.md)
- [Сопоставление с образцом (match-case)](match_case.md)
- [Функции в Python](../functions/README.md)
