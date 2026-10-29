# Генераторы коллекций и перебор

Короткие примеры конструкций для работы с коллекциями: comprehensions для списка, множества и словаря, а также перебор с `range`, `enumerate` и `zip`.

## Генераторы коллекций (comprehensions)

```python run
# Списка
list_ = [i for i in range(5) if i % 2 == 0]
print(list_)  # [0, 2, 4]

# Множества
set_ = {i for i in range(5) if i % 2 == 0}
print(set_)  # {0, 2, 4}

# Словаря
dict_ = {i: i**2 for i in range(5) if i % 2 == 0}
print(dict_)  # {0: 0, 2: 4, 4: 16}
```

## Перебор с `range`, `enumerate`, `zip`

```python run
num = 3

# range — последовательность чисел: от 1 до num (не включая) с шагом 2
for n in range(1, num, 2):
    print(f"Значение: {n}")

fruits = ["apple", "banana", "cherry"]

# enumerate — элементы вместе с индексами
for index, fruit in enumerate(fruits):
    print(index, fruit)

a = [1, 2, 3]
b = [4, 5, 6, 7]
c = [8, 9]

# zip — параллельный перебор; останавливается на самой короткой коллекции
for i in zip(a, b, c):
    print(i)
```

## Связанные темы

- [Сравнение, проверка типов и копирование](comparison_and_copies.md)
- [Обработка исключений](exceptions.md)
- [Рекурсия](../algorithms/recursion.md)
- [Функции в Python](../functions/README.md)
