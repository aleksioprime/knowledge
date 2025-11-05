Модуль **`operator`** в Python содержит функции, которые выполняют стандартные операции (например, сложение, умножение, сравнения, доступ по индексу и т.д.) как функции.

Позволяет использовать арифметические и логические операции как объекты-функции (например, `operator.add(a, b)` вместо `a + b`).

Удобен, когда нужно передавать операцию как аргумент в другие функции (например, в `map`, `reduce`, сортировки).

Таким образом, вместо lambda x, y: x + y можно использовать уже готовую функцию operator.add и т.д.

Применение арифметики в reduce без лямбды

```python
from functools import reduce
import operator

numbers = [2, 3, 4]
product = reduce(operator.add, numbers)
print(product)  # 9
# То же самое, что: (2 + 3) + 4
```

Сортировка списка словарей по разным полям

```python
import operator

users = [
    {"username": "masha", "age": 21},
    {"username": "petya", "age": 19},
    {"username": "vasya", "age": 25},
]

# Сортировка по возрасту
sorted_by_age = sorted(users, key=operator.itemgetter("age"))
print(sorted_by_age)
# [{'username': 'petya', 'age': 19}, {'username': 'masha', 'age': 21}, {'username': 'vasya', 'age': 25}]

# Сортировка по имени пользователя
sorted_by_username = sorted(users, key=operator.itemgetter("username"))
print(sorted_by_username)
# [{'username': 'masha', 'age': 21}, {'username': 'petya', 'age': 19}, {'username': 'vasya', 'age': 25}]
```