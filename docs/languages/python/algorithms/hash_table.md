# Хеш-таблицы

Искать элемент в списке перебором — `O(n)`: на каждом запросе проходим весь список. Если искать по ключу приходится часто — сумма заказов по пользователю, проверка «уже видели этот элемент», подсчёт частот, — нужна структура, которая находит значение за `O(1)`. Это **хеш-таблица** (hash table, hash map); в Python это встроенные `dict` и `set`, и большинство задач на собеседовании решается именно через них.

## Минимальный пример

Сумма заказов по каждому пользователю и набор уникальных пользователей — без единого вложенного цикла.

```python run
orders = [('anna', 300), ('boris', 150), ('anna', 200), ('vera', 90), ('boris', 50)]

total_by_user = {}
for user, amount in orders:
    total_by_user[user] = total_by_user.get(user, 0) + amount

print(total_by_user)            # {'anna': 500, 'boris': 200, 'vera': 90}
print(total_by_user['anna'])    # 500 — по ключу, без перебора
print('oleg' in total_by_user)  # False

users = {user for user, _ in orders}   # set — та же хеш-таблица без значений
print(len(users))               # 3
```

## Как это работает

1. **Хеш-функция** превращает ключ в число: `hash(key) → int`.
2. От этого числа берут остаток от деления на размер таблицы: `index = hash(key) % capacity`.
3. Значение кладут в **корзину** (bucket) с этим индексом.

Если два разных ключа дают один индекс, возникает **коллизия**. Её решают двумя способами:

- **Метод цепочек** (chaining): в каждой корзине хранится список пар.
- **Открытая адресация** (open addressing): ищется следующий свободный слот — линейным, квадратичным или другим пробированием (probing).

Python использует открытую адресацию с псевдослучайным пробированием.

### Сложность операций

| Операция | В среднем | В худшем |
|---|---|---|
| `d[k]` (получение) | O(1) | O(n) |
| `d[k] = v` (запись) | O(1) | O(n) |
| `del d[k]` | O(1) | O(n) |
| `k in d` | O(1) | O(n) |

Худший случай наступает, когда у всех ключей одинаковый хеш: например, ключи специально подобраны для атаки на хеш-функцию.

### Что может быть ключом

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

### Типичные задачи на хеш-таблицу

#### Найти дубликаты в массиве

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

#### Пара чисел с заданной суммой (Two Sum) за O(n)

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

#### Подсчёт частот

```python run
from collections import Counter

Counter('mississippi')   # Counter({'i': 4, 's': 4, 'p': 2, 'm': 1})
```

#### Группировка анаграмм

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

### Простая хеш-таблица с методом цепочек

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

### Что спрашивают на собеседовании

- В чём разница между `dict` и `set`?
- Почему `list` нельзя использовать как ключ? *(Он изменяемый, у него нет `__hash__`.)*
- Что такое **коллизия** и как с ней борются?
- Какие гарантии порядка у `dict`? *(С Python 3.7 порядок вставки гарантирован.)*
- Когда `O(1)` превращается в `O(n)`? *(При плохой хеш-функции и большом числе коллизий.)*

## Частые ошибки

- Список или словарь в роли ключа → `TypeError: unhashable type: 'list'` → превратить ключ в `tuple` или `frozenset`, либо собрать строковый ключ.
- Проверка `x in list_of_seen` вместо `x in set_of_seen` → код правильный, но работает за `O(n²)` и «зависает» на больших данных → хранить увиденные элементы в `set`.
- Обращение `d[key]` к отсутствующему ключу → `KeyError` на данных, которых не было в тестах → `d.get(key, default)`, `collections.defaultdict` или проверка `key in d`.
- Изменение словаря во время перебора (`del d[k]` внутри `for k in d`) → `RuntimeError: dictionary changed size during iteration` → перебирать копию `list(d)` или собрать новый словарь через включение.
- Свой класс как ключ с переопределённым `__eq__`, но без `__hash__` → объект становится нехешируемым, либо равные объекты попадают в разные корзины → определять `__hash__` вместе с `__eq__` по тем же полям или использовать `@dataclass(frozen=True)`.

## Когда не использовать

Хеш-таблица не хранит порядок по ключу: нельзя быстро взять «все ключи от 10 до 20» или наименьший ключ. Для диапазонных запросов, поиска ближайшего значения и упорядоченного обхода нужны отсортированный список с `bisect` или сбалансированное дерево.

Если данных мало (единицы и десятки элементов) и поиск нужен один раз, обычный список и линейный поиск проще и не медленнее. Если нужно только «последний добавленный» или «первый в очереди», берите стек на `list` или `collections.deque`: словарь здесь лишний.

## Связанные темы

- [Нотация «О большое»](big_o_notation.md)
- [Поиск в массиве](searching.md)
- [Линейные структуры данных](linear_structures.md)
- [Деревья](trees.md)
