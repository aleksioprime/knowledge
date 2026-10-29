# Модули collections и itertools

Подсчитать, сколько задач у каждого пользователя, сгруппировать заказы по дате, перебрать все пары кандидатов — такие задачи на обычных словарях и циклах превращаются в десяток строк с проверками `if key not in d`. В стандартной библиотеке для них есть готовые инструменты: модуль `collections` даёт специализированные контейнеры, а `itertools` — функции для работы с итераторами.

## Минимальный пример

```python run
from collections import Counter, defaultdict
from itertools import groupby

tasks = [
    {'title': 'Купить хлеб', 'user': 'alice', 'done': True},
    {'title': 'Позвонить маме', 'user': 'bob', 'done': False},
    {'title': 'Оплатить счёт', 'user': 'alice', 'done': False},
]

print(Counter(task['user'] for task in tasks))  # Counter({'alice': 2, 'bob': 1})

by_user = defaultdict(list)
for task in tasks:
    by_user[task['user']].append(task['title'])
print(dict(by_user))  # {'alice': ['Купить хлеб', 'Оплатить счёт'], 'bob': ['Позвонить маме']}

by_done = sorted(tasks, key=lambda task: task['done'])
for done, group in groupby(by_done, key=lambda task: task['done']):
    print(done, [task['title'] for task in group])
# False ['Позвонить маме', 'Оплатить счёт']
# True ['Купить хлеб']
```

## Как это работает

### Модуль collections

#### defaultdict

`defaultdict` — словарь со значением по умолчанию. Если обратиться к ключу, которого ещё нет, словарь не выбросит `KeyError`, а создаст значение, вызвав переданную функцию: `int()` даёт `0`, `list()` — пустой список, `set()` — пустое множество.

```python run
from collections import defaultdict

d = defaultdict(int)
print(d['apple'])  # 0

d = defaultdict(list)
print(d['apple'])  # []

d = defaultdict(set)
print(d['apple'])  # set()
```

#### Counter

`Counter` подсчитывает, сколько раз встречается каждый элемент в списке или другом итерируемом объекте. Результат работает как словарь: ключи — элементы, значения — число их вхождений.

```python run
from collections import Counter

cnt = Counter(['red', 'blue', 'red', 'green', 'blue', 'blue'])
print(cnt)        # Counter({'blue': 3, 'red': 2, 'green': 1})
print(dict(cnt))  # {'red': 2, 'blue': 3, 'green': 1}
```

#### namedtuple

`namedtuple` создаёт именованный кортеж с заданными полями. Он удобен для данных со структурой, ради которых не хочется писать отдельный класс. К полям можно обращаться и по имени, и по индексу, как в обычном кортеже.

```python run
from collections import namedtuple

Point = namedtuple("Point", "x y")
print(issubclass(Point, tuple))  # True

point = Point(2, 4)
print(point)  # Point(x=2, y=4)

print(point.x)  # 2
print(point.y)  # 4

print(point[0])  # 2
print(point[1])  # 4
```

### Модуль itertools

#### chain

`chain` объединяет несколько итерируемых объектов в один итератор: сначала выдаёт все элементы первого, затем второго и так далее.

```python run
from itertools import chain

chained = chain('ab', [33])
print(next(chained))  # a
print(next(chained))  # b
print(next(chained))  # 33

for i in chain('1', [1, 2, 3], {3, 4}):
    print(i)
```

#### groupby

`groupby` группирует элементы итерируемого объекта по ключу. Ключ задаётся функцией, которая получает элемент и возвращает значение для группировки.

`groupby` объединяет в группу только идущие подряд элементы с одинаковым ключом. Поэтому данные обычно заранее сортируют по тому же ключу.

```python run
from itertools import groupby

grouper = lambda item: item['country']

data = [
    {'city': 'Москва', 'country': 'Россия'},
    {'city': 'Новосибирск', 'country': 'Россия'},
    {'city': 'Пекин', 'country': 'Китай'},
]

for key, group in groupby(data, key=grouper):
    print(key, *group)
```

#### combinations и permutations

Обе функции перебирают наборы из заданного числа элементов:

- `combinations` — сочетания: порядок не важен, `('1', '2')` и `('2', '1')` — один и тот же набор;
- `permutations` — размещения: порядок важен, это разные наборы.

```python run
from itertools import combinations

print(list(combinations('123', 2)))  # [('1', '2'), ('1', '3'), ('2', '3')]
```

```python run
from itertools import permutations

print(list(permutations('123', 2)))
```

## Частые ошибки

- `groupby` без предварительной сортировки по тому же ключу → одинаковые ключи попадают в несколько отдельных групп → сначала `sorted(data, key=grouper)`, потом `groupby(..., key=grouper)`.
- Группа из `groupby` сохраняется в список «на потом» (`groups = [g for _, g in groupby(...)]`) → при чтении группы пусты, потому что итератор уже ушёл дальше → превращать каждую группу в список сразу: `list(group)`.
- Чтение `defaultdict` для проверки (`if d[key]:`) → ключ создаётся побочным эффектом, словарь растёт → проверять через `key in d` или `d.get(key)`.
- `defaultdict(list())` или `defaultdict([])` вместо `defaultdict(list)` → `TypeError: first argument must be callable` → передавать функцию-фабрику без скобок.
- Результат `chain`, `combinations` или `permutations` перебирают дважды → второй проход пуст, итератор исчерпан → обернуть в `list()`, если нужно несколько проходов.

## Когда не использовать

Если словарь нужен один раз и ключей мало, `dict.setdefault(key, []).append(...)` или `d.get(key, 0) + 1` читаются не хуже `defaultdict` и `Counter`, а наружу не отдают объект, который сам создаёт ключи при чтении. `namedtuple` проигрывает `dataclass`, когда полям нужны значения по умолчанию, подсказки типов или методы, — именованный кортеж неизменяем и остаётся кортежем со всеми его сравнениями и распаковкой.

`itertools` даёт ленивые итераторы, и это их сила на больших данных. Но для списка из десяти элементов `chain(a, b)` ничем не лучше `a + b`, а вместо `groupby` с обязательной сортировкой часто проще один цикл с `defaultdict(list)`. Полный перебор `combinations` и `permutations` растёт взрывообразно: для сотен элементов нужен другой алгоритм.

## Связанные темы

- [Функции в Python](README.md)
- [Итераторы и генераторы](iterators_generators.md) — функции `itertools` возвращают итераторы
- [Аргументы и функции как значения](arguments.md) — лямбды в параметре `key`
- [Хеш-таблицы](../algorithms/hash_table.md) — как устроены словари, на которых построены `defaultdict` и `Counter`
- [Основы Python](../basics/README.md)
