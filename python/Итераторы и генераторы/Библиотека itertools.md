**Библиотека `itertools`** — это стандартный модуль Python, который предоставляет набор быстрых, эффективных инструментов для работы с итераторами.  
Её основная задача — упростить создание и обработку сложных последовательностей, не загружая их полностью в память.
### Зачем нужна `itertools`?

- **Генерация и обработка последовательностей:** Позволяет легко создавать комбинаторные, повторяющиеся и фильтрующие итераторы.
- **Экономия памяти:** Все функции возвращают итераторы, которые выдают значения по мере необходимости (лениво).
- **Ускорение и упрощение кода:** Модуль содержит готовые инструменты для типовых задач с последовательностями.
## Инструменты библиотеки:

- **`itertools.count` - c**оздаёт итератор, который бесконечно генерирует последовательность чисел, начиная с указанного стартового значения.

```python
import itertools

counter = itertools.count(start=0, step=2)
for num in counter:
	if num > 10:
		break
	print(num)  # 0, 2, 4, 6, 8, 10
```

- **`itertools.cycle` - c**оздаёт бесконечный итератор, который циклически повторяет элементы переданной итерации.

```python
import itertools

cycler = itertools.cycle(['A', 'B', 'C'])
for _ in range(7):
	print(next(cycler))  # A, B, C, A, B, C, A
```

- **`itertools.repeat` - c**оздаёт итератор, который повторяет указанный объект заданное количество раз. Если количество не указано, повторяет бесконечно.

```python
import itertools

repeater = itertools.repeat('Hello', 3)
for item in repeater:
	print(item)  # Hello, Hello, Hello
```

- **`itertools.chain` - о**бъединяет несколько итераций в одну последовательную итерацию.

```python
import itertools

chain = itertools.chain([1, 2, 3], ['a', 'b', 'c'])
print(list(chain))  # [1, 2, 3, 'a', 'b', 'c']
```

- **`itertools.islice` - с**оздаёт итератор, который возвращает указанный срез элементов из переданной итерации.

```python
import itertools

sliced = itertools.islice(range(10), 2, 8, 2)
print(list(sliced))  # [2, 4, 6]
```

- **`itertools.compress` - с**оздаёт итератор, возвращающий элементы из первой итерации для которых соответствующий элемент из второй итерации (булев) является истиной.

```python
import itertools

data = ['A', 'B', 'C', 'D']
selectors = [1, 0, 1, 0]
compressed = itertools.compress(data, selectors)
print(list(compressed))  # ['A', 'C']
```

- **`itertools.permutations` - с**оздаёт итератор, возвращающий все возможные перестановки элементов заданной длины.

```python
import itertools

perms = itertools.permutations([1, 2, 3], 2)
print(list(perms))  # [(1, 2), (1, 3), (2, 1), (2, 3), (3, 1), (3, 2)]
```

- **`itertools.combinations` - с**оздаёт итератор, возвращающий все возможные комбинации элементов заданной длины.

```python
import itertools

combs = itertools.combinations([1, 2, 3], 2)
print(list(combs))  # [(1, 2), (1, 3), (2, 3)]
```

- **`itertools.product` - с**оздаёт итератор, возвращающий декартово произведение входных итераций.

```python
import itertools

prod = itertools.product([1, 2], ['A', 'B'])
print(list(prod))  # [(1, 'A'), (1, 'B'), (2, 'A'), (2, 'B')]
```

- **`itertools.groupby` - с**оздаёт итератор, который возвращает ключ и группы по ключу из отсортированной итерации.

```python
import itertools

data = [{'name': 'A', 'age': 20}, {'name': 'B', 'age': 20}, {'name': 'C', 'age': 25}]
data.sort(key=lambda x: x['age'])
grouped = itertools.groupby(data, key=lambda x: x['age'])

for key, group in grouped:
	print(key, list(group))
	# 20 [{'name': 'A', 'age': 20}, {'name': 'B', 'age': 20}]
	# 25 [{'name': 'C', 'age': 25}]
```

- **`itertools.tee` - создаёт несколько независимых итераторов из одного исходного итератора.**

```python
import itertools

data = [1, 2, 3, 4]
iter1, iter2 = itertools.tee(data, 2)
print(list(iter1))  # [1, 2, 3, 4]
print(list(iter2))  # [1, 2, 3, 4]
```

- **`itertools.starmap` - с**оздаёт итератор, который применяет функцию к каждому элементу итерации (кортежу аргументов).

```python
import itertools
import math

data = [(0, 2), (1, 2), (2, 2)]
starmapped = itertools.starmap(math.pow, data)
print(list(starmapped))  # [1.0, 2.0, 4.0]
```

- **`itertools.accumulate` -** Создаёт итератор, который возвращает накопленные суммы (или результаты другой бинарной функции) элементов итерации.

```python
import itertools
import operator

data = [1, 2, 3, 4]
acc = itertools.accumulate(data, operator.add)
print(list(acc))  # [1, 3, 6, 10]
    ```