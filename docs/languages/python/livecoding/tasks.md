# Задачи для live coding

Типовые задачи с собеседований для программирования в реальном времени (live coding). У каждой — условие, а под ним спрятано решение: идея в двух словах, сложность и код.

Как тренироваться: прочитайте условие и, не раскрывая решение, попробуйте написать его сами за 10–15 минут. Проговаривайте вслух, что делаете, — на собеседовании это ценят не меньше результата.

## 1. Объединение интервалов

Дан список интервалов `[start, end]`. Объедините пересекающиеся и верните список непересекающихся.

::: details Решение
**Идея:** отсортировать по началу. Тогда пересечься текущий интервал может только с последним добавленным в результат.

**Сложность:** O(n log n) из-за сортировки.

```python run
def merge_intervals(intervals):
    intervals.sort()  # по началу, при равенстве — по концу

    result = []

    for interval in intervals:
        if not result:
            result.append(interval)
        else:
            last = result[-1]

            if interval[0] <= last[1]:
                last[1] = max(last[1], interval[1])
            else:
                result.append(interval)

    return result

intervals = [[2, 6], [1, 3], [8, 10], [15, 18]]
print(merge_intervals(intervals))  # [[1, 6], [8, 10], [15, 18]]
```
:::

## 2. Бинарный поиск

Найдите индекс элемента в отсортированном списке или верните `-1`.

::: details Решение
**Идея:** сравниваем с серединой и отбрасываем половину, где искомого быть не может.

**Сложность:** O(log n).

```python run
def binary_search(arr, target):
    left = 0
    right = len(arr) - 1

    while left <= right:
        mid = (left + right) // 2

        if arr[mid] == target:
            return mid

        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1

    return -1

arr = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
target = 3
print(binary_search(arr, target))  # 2
```
:::

## 3. Группировка анаграмм

Сгруппируйте слова, состоящие из одних и тех же букв.

::: details Решение
**Идея:** у анаграмм одинаковый набор букв, значит, одинаковая отсортированная строка. Её и берём ключом словаря.

**Сложность:** O(n · k log k), где k — длина слова.

```python run
from collections import defaultdict

def group_anagrams(words: list[str]) -> list[list[str]]:
    groups = defaultdict(list)
    for word in words:
        groups[''.join(sorted(word))].append(word)
    return list(groups.values())

print(group_anagrams(['кот', 'ток', 'отк', 'нос', 'сон', 'рука']))
```
:::

## 4. Правильная скобочная последовательность

Проверьте, что скобки `()[]{}` в строке закрываются в правильном порядке.

::: details Решение
**Идея:** стек. Открывающую кладём, на закрывающей снимаем верхнюю и проверяем пару. В конце стек должен быть пустым.

**Сложность:** O(n).

```python run
def is_valid(text: str) -> bool:
    pairs = {')': '(', ']': '[', '}': '{'}
    stack = []
    for char in text:
        if char in '([{':
            stack.append(char)
        elif char in pairs:
            if not stack or stack.pop() != pairs[char]:
                return False
    return not stack

for text in ['([]{})', '([)]', '((', 'print(items[0])']:
    print(text, is_valid(text))
```
:::

## 5. Два числа с заданной суммой

Найдите индексы двух чисел, которые в сумме дают `target`.

::: details Решение
**Идея:** перебор всех пар — O(n²). Быстрее запоминать увиденные числа в словаре и для каждого проверять, встречалось ли `target - число`.

**Сложность:** O(n) по времени и памяти.

```python run
def two_sum(numbers: list[int], target: int) -> tuple[int, int] | None:
    seen = {}
    for i, number in enumerate(numbers):
        if target - number in seen:
            return seen[target - number], i
        seen[number] = i
    return None

print(two_sum([2, 7, 11, 15], 9))
print(two_sum([3, 2, 4], 6))
print(two_sum([1, 2], 10))
```
:::

## 6. Палиндром без учёта знаков и регистра

Проверьте, читается ли фраза одинаково в обе стороны, если не считать пробелы, знаки препинания и регистр.

::: details Решение
**Идея:** два указателя с концов строки идут навстречу и пропускают всё, что не буквы и не цифры. Отдельная очищенная строка не нужна.

**Сложность:** O(n) по времени, O(1) по памяти.

```python run
def is_palindrome(text: str) -> bool:
    left, right = 0, len(text) - 1
    while left < right:
        if not text[left].isalnum():
            left += 1
        elif not text[right].isalnum():
            right -= 1
        elif text[left].lower() != text[right].lower():
            return False
        else:
            left += 1
            right -= 1
    return True

print(is_palindrome('А роза упала на лапу Азора'))
print(is_palindrome('Купить хлеб'))
```
:::

## 7. Самая длинная подстрока без повторов

Найдите длину самой длинной подстроки, в которой символы не повторяются.

::: details Решение
**Идея:** скользящее окно. Правая граница идёт вперёд; если символ уже есть в окне, левая граница прыгает сразу за его прошлое появление.

**Сложность:** O(n).

```python run
def longest_unique(text: str) -> int:
    last_seen = {}
    start = best = 0
    for i, char in enumerate(text):
        if last_seen.get(char, -1) >= start:
            start = last_seen[char] + 1
        last_seen[char] = i
        best = max(best, i - start + 1)
    return best

print(longest_unique('abcabcbb'))  # 3 ('abc')
print(longest_unique('bbbbb'))     # 1 ('b')
print(longest_unique('pwwkew'))    # 3 ('wke')
```
:::

## 8. Самые частые слова

Верните `k` самых частых слов в тексте.

::: details Решение
**Идея:** `Counter` считает и сразу умеет отдавать самые частые.

**Сложность:** O(n log k).

```python run
import re
from collections import Counter

def top_words(text: str, k: int) -> list[tuple[str, int]]:
    words = re.findall(r'\w+', text.lower())
    return Counter(words).most_common(k)

text = 'Купить хлеб. Купить молоко. Хлеб свежий, молоко свежее, хлеб!'
print(top_words(text, 2))
```
:::

## 9. Сжатие строки

Сожмите строку: `'aaabccdddd'` → `'a3b1c2d4'`.

::: details Решение
**Идея:** `itertools.groupby` разбивает строку на группы одинаковых символов, идущих подряд.

**Сложность:** O(n).

```python run
from itertools import groupby

def compress(text: str) -> str:
    return ''.join(f'{char}{len(list(group))}' for char, group in groupby(text))

print(compress('aaabccdddd'))
print(repr(compress('')))
```
:::

## 10. Удалить дубликаты с сохранением порядка

Уберите из списка повторы, сохранив порядок первых вхождений: `[3, 1, 3, 2, 1]` → `[3, 1, 2]`.

::: details Решение
**Идея:** `set` теряет порядок. А словарь начиная с Python 3.7 хранит ключи в порядке добавления, поэтому `dict.fromkeys` убирает повторы и порядок сохраняет.

**Сложность:** O(n).

```python run
def unique(items: list) -> list:
    return list(dict.fromkeys(items))

print(unique([3, 1, 3, 2, 1]))
print(list(set([3, 1, 3, 2, 1])))  # порядок не гарантирован
```
:::

## 11. Разбить на части по n элементов

Разбейте список на части по `n` элементов (последняя может быть короче). Например, чтобы отправлять задачи в API пачками по 100.

::: details Решение
**Идея:** генератор отдаёт срезы и не создаёт весь список частей заранее. В Python 3.12 есть готовый `itertools.batched`.

**Сложность:** O(n).

```python run
def chunks(items: list, size: int):
    for start in range(0, len(items), size):
        yield items[start:start + size]

print(list(chunks([1, 2, 3, 4, 5, 6, 7], 3)))

from itertools import batched  # Python 3.12+

print(list(batched([1, 2, 3, 4, 5, 6, 7], 3)))
```
:::

## 12. Развернуть вложенный список

Превратите список произвольной вложенности в плоский: `[1, [2, [3, 4]], 5]` → `[1, 2, 3, 4, 5]`.

::: details Решение
**Идея:** рекурсия. Если элемент — список, разворачиваем его тем же способом. `yield from` передаёт наружу всё, что отдал вложенный вызов.

**Сложность:** O(n), где n — общее число элементов.

```python run
def flatten(items: list):
    for item in items:
        if isinstance(item, list):
            yield from flatten(item)
        else:
            yield item

print(list(flatten([1, [2, [3, 4]], 5, []])))
```
:::

## 13. Первый неповторяющийся символ

Найдите первый символ строки, который встречается в ней ровно один раз, или верните `None`.

::: details Решение
**Идея:** два прохода: сначала посчитать символы, затем найти первый с количеством 1.

**Сложность:** O(n).

```python run
from collections import Counter

def first_unique(text: str) -> str | None:
    counts = Counter(text)
    for char in text:
        if counts[char] == 1:
            return char
    return None

print(first_unique('swiss'))
print(first_unique('aabb'))
```
:::

## 14. LRU-кэш

Реализуйте кэш на `capacity` элементов с методами `get` и `put`. При переполнении удаляется элемент, к которому дольше всего не обращались (Least Recently Used).

::: details Решение
**Идея:** `OrderedDict` хранит порядок и умеет за O(1) переносить ключ в конец (`move_to_end`) и удалять первый (`popitem(last=False)`). Начало словаря — самый «старый» ключ.

**Сложность:** O(1) на операцию. Для кэширования функций в реальном коде есть готовый `functools.lru_cache`.

```python run
from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.data = OrderedDict()

    def get(self, key):
        if key not in self.data:
            return None
        self.data.move_to_end(key)
        return self.data[key]

    def put(self, key, value) -> None:
        self.data[key] = value
        self.data.move_to_end(key)
        if len(self.data) > self.capacity:
            self.data.popitem(last=False)

cache = LRUCache(2)
cache.put('a', 1)
cache.put('b', 2)
cache.get('a')       # 'a' стал самым свежим
cache.put('c', 3)    # вытесняется 'b'
print(list(cache.data))
```
:::

## 15. Декоратор повторных попыток

Напишите декоратор, который повторяет вызов функции, если она упала, — например, при сетевой ошибке.

::: details Решение
**Идея:** обёртка вызывает функцию в цикле и перехватывает исключение. После последней попытки исключение пробрасывается дальше. `functools.wraps` сохраняет имя и документацию исходной функции.

```python run
import functools

def retry(times: int):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except ConnectionError as error:
                    print(f'Попытка {attempt} не удалась: {error}')
                    if attempt == times:
                        raise
        return wrapper
    return decorator

calls = 0

@retry(times=3)
def send_reminder() -> str:
    global calls
    calls += 1
    if calls < 3:
        raise ConnectionError('SMTP недоступен')
    return 'отправлено'

print(send_reminder())
```
:::

## Связанные темы

- [Паттерны для собеседований](../algorithms/interview_patterns.md)
- [Хеш-таблицы](../algorithms/hash_table.md)
- [Поиск в массиве](../algorithms/searching.md)
- [Рекурсия](../algorithms/recursion.md)
