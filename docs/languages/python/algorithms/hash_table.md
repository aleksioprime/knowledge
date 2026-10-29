# Хеш-таблицы

Искать элемент в списке перебором — `O(n)`. **Хеш-таблица** (hash table, hash map) хранит пары `ключ → значение` и находит значение по ключу в среднем за `O(1)`.

В Python это встроенные `dict` и `set`. Большинство задач на собеседовании решается именно через них.

## Как это работает

1. **Хеш-функция** превращает ключ в число: `hash(key) → int`.
2. От этого числа берут остаток от деления на размер таблицы: `index = hash(key) % capacity`.
3. Значение кладут в **корзину** (bucket) с этим индексом.

Если два разных ключа дают один индекс, возникает **коллизия**. Её решают двумя способами:

- **Метод цепочек** (chaining): в каждой корзине хранится список пар.
- **Открытая адресация** (open addressing): ищется следующий свободный слот — линейным, квадратичным или другим пробированием (probing).

Python использует открытую адресацию с псевдослучайным пробированием.

## Сложность операций

| Операция | В среднем | В худшем |
|---|---|---|
| `d[k]` (получение) | O(1) | O(n) |
| `d[k] = v` (запись) | O(1) | O(n) |
| `del d[k]` | O(1) | O(n) |
| `k in d` | O(1) | O(n) |

Худший случай наступает, когда у всех ключей одинаковый хеш: например, ключи специально подобраны для атаки на хеш-функцию.

## Что может быть ключом

Только **хешируемые** объекты (с методом `__hash__`), то есть неизменяемые:

- можно: `int`, `float`, `str`, `bytes`, `tuple` из хешируемых элементов, `frozenset`;
- нельзя: `list`, `dict`, `set` — они изменяемые.

Пример ниже намеренно вызывает `TypeError`, чтобы показать ошибку:

```python run
d = {(1, 2): 'point'}        # tuple — можно
print(d[(1, 2)])

try:
    d[[1, 2]] = 'fail'       # list — TypeError
except TypeError as e:
    print('TypeError:', e)
```

## Типичные задачи на хеш-таблицу

### Найти дубликаты в массиве

```python run
def has_duplicates(arr):
    seen = set()
    for x in arr:
        if x in seen:
            return True
        seen.add(x)
    return False

has_duplicates([1, 2, 3, 4, 2])   # True
```

### Пара чисел с заданной суммой (Two Sum) за O(n)

Для каждого числа проверяем, встречалось ли раньше дополнение до суммы.

```python run
def two_sum(arr, target):
    seen = {}                # значение → индекс
    for i, x in enumerate(arr):
        if target - x in seen:
            return [seen[target - x], i]
        seen[x] = i
    return None

two_sum([2, 7, 11, 15], 9)   # [0, 1]
```

### Подсчёт частот

```python run
from collections import Counter

Counter('mississippi')   # Counter({'i': 4, 's': 4, 'p': 2, 'm': 1})
```

### Группировка анаграмм

У анаграмм одинаковый набор букв, поэтому отсортированные буквы слова — общий ключ группы.

```python run
from collections import defaultdict

def group_anagrams(words):
    groups = defaultdict(list)
    for w in words:
        key = ''.join(sorted(w))
        groups[key].append(w)
    return list(groups.values())

group_anagrams(['eat', 'tea', 'tan', 'ate', 'nat', 'bat'])
```

## Простая хеш-таблица с методом цепочек

```python run
class HashMap:
    def __init__(self, capacity=16):
        self.capacity = capacity
        self.buckets = [[] for _ in range(capacity)]
        self.size = 0

    def _index(self, key):
        return hash(key) % self.capacity

    def put(self, key, value):
        bucket = self.buckets[self._index(key)]
        for i, (k, _) in enumerate(bucket):
            if k == key:
                bucket[i] = (key, value)
                return
        bucket.append((key, value))
        self.size += 1

    def get(self, key):
        for k, v in self.buckets[self._index(key)]:
            if k == key:
                return v
        raise KeyError(key)

    def remove(self, key):
        bucket = self.buckets[self._index(key)]
        for i, (k, _) in enumerate(bucket):
            if k == key:
                bucket.pop(i)
                self.size -= 1
                return
        raise KeyError(key)

m = HashMap()
m.put('a', 1); m.put('b', 2); m.put('a', 10)
print(m.get('a'), m.get('b'), m.size)   # 10 2 2
```

## Что спрашивают на собеседовании

- В чём разница между `dict` и `set`?
- Почему `list` нельзя использовать как ключ? *(Он изменяемый, у него нет `__hash__`.)*
- Что такое **коллизия** и как с ней борются?
- Какие гарантии порядка у `dict`? *(С Python 3.7 порядок вставки гарантирован.)*
- Когда `O(1)` превращается в `O(n)`? *(При плохой хеш-функции и большом числе коллизий.)*

## Связанные темы

- [Нотация «О большое»](big_o_notation.md)
- [Поиск в массиве](searching.md)
- [Линейные структуры данных](linear_structures.md)
