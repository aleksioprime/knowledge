# Сопоставление с образцом (match-case)

Оператор `match` сравнивает значение с несколькими образцами и выполняет ветку первого совпадения. Это замена длинных цепочек `if`/`elif` при разборе значений.

```python run
def process_value(value):
    match value:
        case 1:
            print("Value is 1")
        case 2 | 3 | 4:
            print("Value is 2 or 3 or 4")
        case _:
            print("Value is not 1 or 2 or 3 or 4")

process_value(1)  # Value is 1
process_value(3)  # Value is 2 or 3 or 4
```

## Связанные темы

- [Обработка исключений](exceptions.md)
- [Сравнение, проверка типов и копирование](comparison_and_copies.md)
