# Паттерны для собеседований

Небольшие приёмы, которые позволяют решать целые классы задач за `O(n)` вместо `O(n²)`. Их часто ждут на собеседовании.

## Два указателя (Two Pointers)

Два индекса идут навстречу друг другу или в одну сторону с разной скоростью.

Где применяется: палиндром, удаление дубликатов из отсортированного массива, сумма двух чисел в отсортированном массиве, контейнер с водой.

### Проверка палиндрома

```python run
def is_palindrome(s):
    left, right = 0, len(s) - 1
    while left < right:
        if s[left] != s[right]:
            return False
        left += 1
        right -= 1
    return True

print(is_palindrome('racecar'))   # True
print(is_palindrome('hello'))     # False
```

### Сумма двух чисел в отсортированном массиве (Two Sum)

В отсортированном массиве сумма крайних элементов подсказывает, какой указатель сдвигать: мала — левый, велика — правый. Получается `O(n)`.

```python run
def two_sum_sorted(arr, target):
    left, right = 0, len(arr) - 1
    while left < right:
        s = arr[left] + arr[right]
        if s == target:
            return [left, right]
        elif s < target:
            left += 1
        else:
            right -= 1
    return None

two_sum_sorted([1, 2, 4, 7, 11, 15], 9)   # [1, 3]
```

### Удаление дубликатов из отсортированного массива на месте

```python run
def remove_duplicates(arr):
    if not arr:
        return 0
    slow = 0
    for fast in range(1, len(arr)):
        if arr[fast] != arr[slow]:
            slow += 1
            arr[slow] = arr[fast]
    return slow + 1   # длина уникальной части

arr = [1, 1, 2, 2, 3, 4, 4, 5]
k = remove_duplicates(arr)
print(k, arr[:k])   # 5 [1, 2, 3, 4, 5]
```

## Хеш-таблица, или словарь (Hash Map)

Самый универсальный паттерн на собеседовании. Идея: пока идёшь по массиву **один раз**, запоминай в словаре полезную информацию об уже виденных элементах. На каждом шаге проверяй словарь за `O(1)` — и весь алгоритм получается `O(n)` вместо `O(n²)`.

Платим за это **дополнительной памятью** `O(n)` — почти всегда выгодная сделка.

Типовые роли словаря:
- **значение → индекс** (для Two Sum и подобных задач на «дополнение»);
- **значение → счётчик** (частоты, поиск самого частого, проверка анаграмм);
- **ключ-категория → список** (группировка анаграмм, задачи с корзинами — bucket);
- **множество посещённых** (`set`) — поиск дубликатов и циклов.

### Паттерн «дополнение»

Задача: найти в массиве два числа с суммой `target`. Наивно — два вложенных цикла, `O(n²)`. Через словарь — один проход, `O(n)`.

**Идея:** идём по массиву, для каждого `num` ищем «дополнение» `target - num` среди уже виденных. Если оно там — нашли пару. Иначе кладём `num` в словарь и идём дальше.

```python run
def two_sum(nums: list[int], target: int) -> list[int]:
    seen = {}                          # значение → индекс
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []

two_sum([2, 7, 11, 15], 9)   # [0, 1]
```

Тот же приём работает для целой россыпи задач:
- найти пару с разностью `k` → ищи `num - k` или `num + k`;
- проверить, что массив содержит число вместе с противоположным (`x` и `-x`);
- посчитать пары с суммой, кратной `m` → ключ = `num % m`.

### Паттерн «подсчёт частот»

Сколько раз встречается каждый элемент. Базовая операция для задач на проверку анаграмм, поиск самого частого элемента (majority element) и `k` самых частых (top-k frequent elements).

Самый частый элемент:

```python run
from collections import Counter

def most_common(arr):
    return Counter(arr).most_common(1)[0][0]

most_common([1, 2, 3, 2, 2, 4, 5, 2])   # 2
```

Анаграммы — слова из одинаковых букв в одинаковом количестве:

```python run
from collections import Counter

def is_anagram(a: str, b: str) -> bool:
    return Counter(a) == Counter(b)

print(is_anagram('listen', 'silent'))   # True
print(is_anagram('hello', 'world'))     # False
```

`k` самых частых элементов:

```python run
from collections import Counter

def top_k_frequent(arr, k):
    return [x for x, _ in Counter(arr).most_common(k)]

top_k_frequent([1, 1, 1, 2, 2, 3], 2)   # [1, 2]
```

### Паттерн «запомнить последнюю позицию»

Когда нужна не просто пара, а **расстояние** между повторами или ближайшее вхождение. В словаре храним «значение → последний индекс».

Задача: есть ли в массиве два одинаковых числа на расстоянии не больше `k`?

```python run
def contains_nearby_duplicate(arr, k):
    last = {}
    for i, x in enumerate(arr):
        if x in last and i - last[x] <= k:
            return True
        last[x] = i
    return False

print(contains_nearby_duplicate([1, 2, 3, 1], 3))     # True
print(contains_nearby_duplicate([1, 0, 1, 1], 1))     # True
print(contains_nearby_duplicate([1, 2, 3, 1, 2], 2))  # False
```

### Паттерн «группировка по ключу» (defaultdict)

Когда нужно разложить элементы по корзинам по общему свойству. Ключ — то, по чему группируем, значение — список или множество элементов.

Группировка анаграмм: ключ — отсортированные буквы слова.

```python run
from collections import defaultdict

def group_anagrams(words):
    groups = defaultdict(list)
    for w in words:
        key = ''.join(sorted(w))
        groups[key].append(w)
    return list(groups.values())

group_anagrams(['eat', 'tea', 'tan', 'ate', 'nat', 'bat'])
# [['eat', 'tea', 'ate'], ['tan', 'nat'], ['bat']]
```

Группировка чисел по остатку от деления — классический трюк:

```python run
from collections import defaultdict

def group_by_mod(arr, m):
    groups = defaultdict(list)
    for x in arr:
        groups[x % m].append(x)
    return dict(groups)

group_by_mod([1, 2, 3, 4, 5, 6, 7, 8], 3)
# {1: [1, 4, 7], 2: [2, 5, 8], 0: [3, 6]}
```

### Паттерн «множество посещённых» (set)

Когда не важно, **сколько** раз встретился элемент, важен только сам факт. `set` проверяет `in` за `O(1)`.

Поиск дубликата за один проход:

```python run
def has_duplicate(arr):
    seen = set()
    for x in arr:
        if x in seen:
            return True
        seen.add(x)
    return False

has_duplicate([1, 2, 3, 4, 2])   # True
```

Самая длинная последовательность подряд идущих чисел (Longest Consecutive Sequence) за `O(n)` — классика LeetCode. Считаем длину только от начала серии, поэтому каждое число просматривается не больше двух раз.

```python run
def longest_consecutive(arr):
    nums = set(arr)
    best = 0
    for x in nums:
        if x - 1 in nums:
            continue                     # x не начало серии
        length = 1
        while x + length in nums:
            length += 1
        best = max(best, length)
    return best

longest_consecutive([100, 4, 200, 1, 3, 2])   # 4 ([1, 2, 3, 4])
```

### Когда выбирать паттерн «словарь»

Если в задаче:
- спрашивают про **пары или тройки** с условием на сумму, разность или произведение;
- надо **найти дубликат** или сравнить вхождения;
- нужна **частота** или **самый частый** элемент;
- надо **группировать** по общему ключу;
- нужен **подмассив с суммой `k`** (префиксные суммы + `dict`),

то почти всегда правильный ход — пройти массив один раз и накопить нужное в `dict`/`set`/`Counter`/`defaultdict`.

## Скользящее окно (Sliding Window)

Окно фиксированной или переменной длины двигается по массиву. Сумму не пересчитываем с нуля: добавляем правый элемент и вычитаем левый.

Где применяется: максимальная/минимальная сумма подмассива длины `k`, длиннейшая подстрока без повторов, минимальная подстрока, содержащая все символы.

### Максимальная сумма подмассива длины `k`

```python run
def max_subarray_sum(arr, k):
    if len(arr) < k:
        return None
    window = sum(arr[:k])
    best = window
    for i in range(k, len(arr)):
        window += arr[i] - arr[i - k]   # окно сдвинулось вправо
        best = max(best, window)
    return best

max_subarray_sum([2, 1, 5, 1, 3, 2], 3)   # 9 ([5, 1, 3])
```

### Самая длинная подстрока без повторяющихся символов

Правая граница идёт вперёд. Если символ уже есть в окне, левая граница прыгает сразу за его прошлое появление.

```python run
def longest_unique_substring(s):
    seen = {}
    left = 0
    best = 0
    for right, ch in enumerate(s):
        if ch in seen and seen[ch] >= left:
            left = seen[ch] + 1     # сдвигаем левую границу
        seen[ch] = right
        best = max(best, right - left + 1)
    return best

longest_unique_substring('abcabcbb')   # 3 ('abc')
```

## Префиксные суммы (Prefix Sum)

`prefix[i]` — сумма всех элементов с индексами от `0` до `i-1`. Массив префиксов строится за `O(n)`, после этого сумма любого отрезка `[l, r]` считается за `O(1)` как `prefix[r+1] - prefix[l]`.

Где применяется: суммы на отрезках (range sum query), подмассивы с заданной суммой, поиск равных частей.

```python run
def build_prefix(arr):
    prefix = [0]
    for x in arr:
        prefix.append(prefix[-1] + x)
    return prefix

def range_sum(prefix, l, r):
    return prefix[r + 1] - prefix[l]

arr = [3, 1, 4, 1, 5, 9, 2, 6]
p = build_prefix(arr)
range_sum(p, 2, 5)   # 4+1+5+9 = 19
```

### Подмассив с заданной суммой (префиксы + словарь)

Если раньше встречалась префиксная сумма `prefix_sum - k`, то между той позицией и текущей сумма элементов равна `k`. Словарь хранит, сколько раз встречалась каждая префиксная сумма.

```python run
def subarray_sum_equals_k(arr, k):
    """Количество подмассивов с суммой = k."""
    count = 0
    prefix_sum = 0
    seen = {0: 1}   # пустой префикс
    for x in arr:
        prefix_sum += x
        count += seen.get(prefix_sum - k, 0)
        seen[prefix_sum] = seen.get(prefix_sum, 0) + 1
    return count

subarray_sum_equals_k([1, 1, 1], 2)   # 2
```

## Битовые операции (Bit Manipulation)

Пригодятся, если попадётся задача про числа или множества.

| Операция | Что делает |
|---|---|
| `a & b` | AND (битовое И) |
| `a \| b` | OR (битовое ИЛИ) |
| `a ^ b` | XOR (исключающее ИЛИ) |
| `~a` | NOT (инверсия) |
| `a << k` | сдвиг влево (× 2^k) |
| `a >> k` | сдвиг вправо (// 2^k) |

### Полезные трюки

```python run
# Проверить чётность
print(7 & 1)   # 1 — нечётное
print(8 & 1)   # 0 — чётное

# Степень двойки?
def is_power_of_two(n):
    return n > 0 and (n & (n - 1)) == 0
print(is_power_of_two(16))   # True
print(is_power_of_two(18))   # False

# Сколько единичных битов
print(bin(13).count('1'))   # 3 (1101)

# Найти единственное непарное число в массиве (все остальные парные)
from functools import reduce
import operator
arr = [1, 2, 3, 2, 1]
print(reduce(operator.xor, arr))   # 3
```

## Чек-лист для собеседования

1. **Уточнить условия**: размер входа, диапазон значений, отсортированы ли данные, могут ли быть отрицательные числа.
2. **Разобрать пример** вручную, чтобы убедиться, что задача понята.
3. **Назвать наивное решение и его сложность** (часто `O(n²)`).
4. **Подумать о структурах и приёмах**: словарь, куча, два указателя, скользящее окно, стек, динамическое программирование.
5. **Сначала идея, потом код**. Объяснить план интервьюеру.
6. **Проверить крайние случаи** (edge cases): пустой ввод, один элемент, дубликаты, переполнение.
7. **Назвать итоговую сложность** — по времени **и** по памяти.

## Связанные темы

- [Хеш-таблицы](hash_table.md)
- [Поиск в массиве](searching.md)
- [Сортировки](sorting.md)
- [Big O Notation](big_o_notation.md)
