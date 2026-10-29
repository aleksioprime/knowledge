# Сортировки

В рабочем коде достаточно вызвать `sorted()`, но на собеседовании обычно спрашивают, как устроены классические сортировки:

- что такое **стабильность** сортировки;
- какова сложность по времени и памяти;
- какие сортировки работают за `O(n²)`, какие за `O(n log n)`, а какие вообще не сравнивают элементы.

**Стабильная сортировка** сохраняет относительный порядок равных элементов.

## Сравнительная таблица

| Алгоритм | Время (в среднем) | Время (в худшем) | Память | Стабильна? |
|---|---|---|---|---|
| Пузырьковая (bubble sort) | O(n²) | O(n²) | O(1) | да |
| Выбором (selection sort) | O(n²) | O(n²) | O(1) | нет |
| Вставками (insertion sort) | O(n²) | O(n²) | O(1) | да |
| Слиянием (merge sort) | O(n log n) | O(n log n) | O(n) | да |
| Быстрая (quick sort) | O(n log n) | O(n²) | O(log n) | нет |
| Пирамидальная (heap sort) | O(n log n) | O(n log n) | O(1) | нет |
| Timsort (Python) | O(n log n) | O(n log n) | O(n) | да |

## Пузырьковая сортировка

Проходим по массиву и меняем местами соседей, стоящих в неправильном порядке. После `i`-го прохода последние `i` элементов уже на своих местах.

```python run
def bubble_sort(arr):
    arr = arr.copy()
    n = len(arr)
    for i in range(n):
        for j in range(n - 1 - i):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr

bubble_sort([64, 25, 12, 22, 11])
```

## Сортировка выбором

На каждом шаге находим минимум в оставшейся части и ставим его в начало.

```python run
def selection_sort(arr):
    arr = arr.copy()
    n = len(arr)
    for i in range(n):
        min_idx = i
        for j in range(i + 1, n):
            if arr[j] < arr[min_idx]:
                min_idx = j
        arr[i], arr[min_idx] = arr[min_idx], arr[i]
    return arr

selection_sort([64, 25, 12, 22, 11])
```

## Сортировка вставками

Как карты в руке: берём следующий элемент и вставляем его на нужное место среди уже отсортированных.

Это лучшая из `O(n²)`-сортировок для **почти отсортированных** массивов: в лучшем случае она работает за `O(n)`.

```python run
def insertion_sort(arr):
    arr = arr.copy()
    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1
        # сдвигаем бо́льшие элементы вправо, пока не найдём место для key
        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = key
    return arr

insertion_sort([64, 25, 12, 22, 11])
```

## Сортировка слиянием

Принцип «разделяй и властвуй» (divide and conquer): делим массив пополам, рекурсивно сортируем каждую половину, затем сливаем.

Сортировка **стабильна** и гарантированно работает за `O(n log n)`, но ей нужна дополнительная память `O(n)`.

```python run
def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)

def merge(left, right):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i]); i += 1
        else:
            result.append(right[j]); j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result

merge_sort([64, 25, 12, 22, 11, 90, 33])
```

## Быстрая сортировка

Тоже «разделяй и властвуй»: выбираем **опорный элемент** (pivot), делим массив на элементы меньше и больше него и рекурсивно сортируем обе части.

В среднем это `O(n log n)`. Если опорный элемент выбирается неудачно (например, крайний на уже отсортированных данных), сложность падает до `O(n²)`.

```python run
def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]   # средний элемент надёжнее крайнего
    left  = [x for x in arr if x < pivot]
    mid   = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + mid + quick_sort(right)

quick_sort([64, 25, 12, 22, 11, 90, 33])
```

### Быстрая сортировка на месте

Тот же алгоритм, но без создания новых списков: массив переставляется на месте (in-place), и дополнительная память — только стек рекурсии, `O(log n)`.

```python run
def quick_sort_inplace(arr, low=0, high=None):
    if high is None:
        high = len(arr) - 1
    if low < high:
        p = partition(arr, low, high)
        quick_sort_inplace(arr, low, p - 1)
        quick_sort_inplace(arr, p + 1, high)
    return arr

def partition(arr, low, high):
    pivot = arr[high]
    i = low - 1
    for j in range(low, high):
        if arr[j] <= pivot:
            i += 1
            arr[i], arr[j] = arr[j], arr[i]
    arr[i + 1], arr[high] = arr[high], arr[i + 1]
    return i + 1

quick_sort_inplace([64, 25, 12, 22, 11, 90, 33])
```

## Timsort — сортировка внутри Python

Встроенные `sorted()` и `list.sort()` используют **Timsort** — гибрид сортировки слиянием и сортировки вставками. Его свойства:

- стабилен;
- адаптивен: использует уже отсортированные участки, поэтому на почти отсортированных данных может работать за `O(n)`;
- в худшем случае — `O(n log n)`.

Стабильность видна при сортировке по ключу: Alice и Cara одного возраста и остаются в исходном порядке.

```python run
data = [{'name': 'Alice', 'age': 30}, {'name': 'Bob', 'age': 25}, {'name': 'Cara', 'age': 30}]

print(sorted(data, key=lambda x: x['age']))                # по одному ключу
print(sorted(data, key=lambda x: (x['age'], x['name'])))   # по нескольким полям
```

## Что спрашивают на собеседовании

- В чём разница между **стабильной** и **нестабильной** сортировкой?
- Какая сортировка лучше для **почти отсортированных** данных? *(Вставками или Timsort.)*
- Можно ли отсортировать **за O(n)**? *(Можно: сортировка подсчётом, поразрядная, блочная — counting, radix, bucket sort. Но они не сравнивают элементы и работают только на ограниченных типах данных.)*
- Когда выбирать **сортировку слиянием**, а когда **быструю**? *(Слиянием — когда важна стабильность и есть память. Быструю — когда память дорога.)*

## Связанные темы

- [Нотация «О большое»](big_o_notation.md)
- [Поиск в массиве](searching.md)
- [Рекурсия](recursion.md)
- [Деревья](trees.md)
