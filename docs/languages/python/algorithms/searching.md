# Поиск в массиве

Найти элемент в массиве — самая частая задача на собеседовании. Два алгоритма нужно знать наизусть: линейный поиск и бинарный.

## Линейный поиск — O(n)

Перебираем все элементы подряд. Работает на любых данных.

```python run
def linear_search(arr, target):
    for i, x in enumerate(arr):
        if x == target:
            return i
    return -1

linear_search([4, 7, 1, 9, 3], 9)   # 3
```

## Бинарный поиск — O(log n)

**Бинарный поиск** (binary search) работает **только на отсортированном массиве**. Смотрим на середину, сравниваем с искомым значением и продолжаем в нужной половине. На каждом шаге отбрасываем половину элементов.

```python run
def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1

binary_search([1, 3, 4, 7, 9, 11, 15], 9)   # 4
```

### Подводные камни

- `mid = (left + right) // 2` в Python безопасно: переполнения целых нет. В C или Java пишут `mid = left + (right - left) / 2`, чтобы избежать переполнения.
- Условие цикла — `left <= right`, со знаком равенства.
- Границы сужаются только через `mid + 1` и `mid - 1`, иначе цикл может стать бесконечным.

## Рекурсивный бинарный поиск

```python run
def binary_search_rec(arr, target, left=0, right=None):
    if right is None:
        right = len(arr) - 1
    if left > right:
        return -1
    mid = (left + right) // 2
    if arr[mid] == target:
        return mid
    if arr[mid] < target:
        return binary_search_rec(arr, target, mid + 1, right)
    return binary_search_rec(arr, target, left, mid - 1)

binary_search_rec([1, 3, 4, 7, 9, 11, 15], 11)
```

## Модуль bisect

В рабочем коде удобнее не писать бинарный поиск руками, а взять стандартный модуль `bisect`. Он возвращает индекс, куда нужно вставить значение, чтобы сохранить сортировку.

```python run
import bisect

arr = [1, 3, 4, 7, 9, 11, 15]

print(bisect.bisect_left(arr, 7))   # 3 (позиция самого 7)
print(bisect.bisect_right(arr, 7))  # 4 (позиция сразу за 7)

bisect.insort(arr, 8)   # вставка с сохранением порядка
print(arr)   # [1, 3, 4, 7, 8, 9, 11, 15]
```

## Когда что использовать

- **Неотсортированный массив** — линейный поиск. Если искать придётся часто, массив лучше один раз отсортировать.
- **Отсортированный массив** — бинарный поиск (`bisect`).
- **Поиск по ключу** — хеш-таблица `dict`, `O(1)`.
- **Поиск ближайшего значения** — бинарный поиск: `bisect` подскажет позицию.

## Связанные темы

- [Нотация «О большое»](big_o_notation.md)
- [Сортировки](sorting.md)
- [Хеш-таблицы](hash_table.md)
