# Деревья

Файловая система, DOM страницы, структура компании — везде, где у объекта есть родитель и дети, данные ложатся в дерево. Знать деревья нужно, чтобы искать в упорядоченных данных быстрее перебора (дерево поиска), доставать минимум из потока без полной сортировки (куча) и уверенно писать рекурсивный обход — он встречается в каждом втором вопросе на собеседовании.

## Минимальный пример

```python run
class TreeNode:
    def __init__(self, value, left=None, right=None):
        self.value = value
        self.left = left
        self.right = right

def height(node):
    if node is None:
        return 0
    return 1 + max(height(node.left), height(node.right))

def leaves(node):
    if node is None:
        return []
    if node.left is None and node.right is None:
        return [node.value]
    return leaves(node.left) + leaves(node.right)

# структура компании: директор → руководители → сотрудник
company = TreeNode('директор',
                   TreeNode('руководитель продаж', TreeNode('менеджер')),
                   TreeNode('руководитель разработки'))
print(height(company))   # 3
print(leaves(company))   # ['менеджер', 'руководитель разработки']
```

## Как это работает

**Дерево** (tree) — иерархическая структура из узлов: у него один **корень** (root), у каждого узла может быть несколько **детей**, а у каждого узла, кроме корня, — ровно один **родитель**.

Циклов в дереве нет. Основные термины: **лист** (leaf) — узел без детей, **глубина** узла, **высота** дерева, **поддерево**.

### Бинарное дерево

В **бинарном дереве** у каждого узла **не более двух детей**: `left` и `right`.

```python run session=trees
class TreeNode:
    def __init__(self, value, left=None, right=None):
        self.value = value
        self.left = left
        self.right = right

# дерево:
#         1
#        / \
#       2   3
#      / \
#     4   5

root = TreeNode(1,
                TreeNode(2, TreeNode(4), TreeNode(5)),
                TreeNode(3))
```

### Обходы дерева

Все обходы работают за `O(n)`. Названия легко запомнить по тому, когда обрабатывается **узел** относительно левого и правого поддеревьев: до (pre), между (in) или после (post).

#### Прямой обход (pre-order, NLR)

Узел → левое поддерево → правое поддерево.

```python run session=trees
def preorder(node):
    if node is None: return
    print(node.value, end=' ')
    preorder(node.left)
    preorder(node.right)

preorder(root)   # 1 2 4 5 3
```

#### Центрированный обход (in-order, LNR)

Левое поддерево → узел → правое поддерево. Для дерева поиска даёт значения **в отсортированном порядке**.

```python run session=trees
def inorder(node):
    if node is None: return
    inorder(node.left)
    print(node.value, end=' ')
    inorder(node.right)

inorder(root)   # 4 2 5 1 3
```

#### Обратный обход (post-order, LRN)

Левое поддерево → правое поддерево → узел. Удобен для удаления дерева: сначала освобождаем детей, потом родителя.

```python run session=trees
def postorder(node):
    if node is None: return
    postorder(node.left)
    postorder(node.right)
    print(node.value, end=' ')

postorder(root)   # 4 5 2 3 1
```

#### Обход по уровням (level-order, BFS)

```python run session=trees
from collections import deque

def level_order(root):
    if not root: return
    q = deque([root])
    while q:
        node = q.popleft()
        print(node.value, end=' ')
        if node.left:  q.append(node.left)
        if node.right: q.append(node.right)

level_order(root)   # 1 2 3 4 5
```

### Бинарное дерево поиска

**Бинарное дерево поиска** (Binary Search Tree, BST) — бинарное дерево, в котором:

- слева от узла лежат значения **меньше** него;
- справа — **больше**.

Это даёт поиск, вставку и удаление за `O(log n)`, если дерево сбалансировано. Если нет (например, данные вставляли уже отсортированными), операции деградируют до `O(n)`.

Поэтому промышленные реализации (`std::map` в C++, `TreeMap` в Java) — **самобалансирующиеся** деревья: АВЛ-дерево (AVL) или красно-чёрное дерево (Red-Black tree).

```python run session=trees
class BST:
    def __init__(self):
        self.root = None

    def insert(self, value):
        self.root = self._insert(self.root, value)

    def _insert(self, node, value):
        if node is None:
            return TreeNode(value)
        if value < node.value:
            node.left = self._insert(node.left, value)
        elif value > node.value:
            node.right = self._insert(node.right, value)
        return node

    def contains(self, value):
        node = self.root
        while node:
            if value == node.value: return True
            node = node.left if value < node.value else node.right
        return False

bst = BST()
for x in [5, 3, 7, 1, 4, 6, 8]:
    bst.insert(x)
print(bst.contains(4), bst.contains(100))   # True False
inorder(bst.root)   # 1 3 4 5 6 7 8 — отсортировано
```

### Куча

**Двоичная куча** (binary heap) — бинарное дерево, в котором:

- в **min-куче** значение каждого узла не больше значений его детей, и в корне лежит минимум;
- в **max-куче** — наоборот, не меньше, и в корне лежит максимум.

Куча хранится **в массиве**: дети узла `i` находятся по индексам `2i+1` и `2i+2`.

Сложность:

- добавление (`push`) — `O(log n)`;
- извлечение минимума или максимума (`pop`) — `O(log n)`;
- просмотр вершины (`peek`) — `O(1)`.

В Python кучу реализует модуль `heapq` (это min-куча).

```python run
import heapq

h = []
for x in [5, 1, 3, 9, 2]:
    heapq.heappush(h, x)

print(h[0])                # просмотр минимума: 1
print(heapq.heappop(h))    # 1
print(heapq.heappop(h))    # 2
print(heapq.heappop(h))    # 3

# превратить готовый список в кучу — O(n)
arr = [5, 1, 3, 9, 2]
heapq.heapify(arr)
print(arr)   # [1, 2, 3, 9, 5]
```

#### Max-куча через инверсию знака

Готовой max-кучи в `heapq` нет, поэтому значения кладут со знаком минус.

```python run
import heapq

h = []
for x in [5, 1, 3, 9, 2]:
    heapq.heappush(h, -x)

print(-heapq.heappop(h))   # 9 — максимум
```

#### Где применяется куча

- Поиск K наибольших или наименьших элементов: `heapq.nlargest(k, arr)`, `heapq.nsmallest(k, arr)`.
- Очередь с приоритетом (priority queue), например в алгоритме Дейкстры.
- Пирамидальная сортировка (heap sort).
- Медиана потока чисел (через две кучи).

### Что спрашивают на собеседовании

- Назовите **три обхода** бинарного дерева. Чем они отличаются?
- Почему центрированный обход BST даёт **отсортированную** последовательность?
- Что произойдёт с BST, если вставлять данные **в отсортированном порядке**? *(Дерево выродится в список, операции станут O(n) — поэтому нужны АВЛ- и красно-чёрные деревья.)*
- Чем **BST** отличается от **кучи**? *(В BST значения упорядочены слева направо. В куче порядок есть только между родителем и детьми, между братьями его нет.)*
- Как реализовать **очередь с приоритетом**?

## Частые ошибки

- Вставка в простое BST уже отсортированных данных → дерево вырождается в цепочку: поиск за `O(n)`, а рекурсивная вставка на десятках тысяч элементов падает с `RecursionError` → перемешать данные перед вставкой, взять самобалансирующееся дерево или `bisect` на отсортированном списке.
- Рекурсивный обход глубокого или вырожденного дерева → `RecursionError: maximum recursion depth exceeded` (лимит около 1000 уровней) → обход на явном стеке или очереди, как в `level_order`.
- Ожидание, что список-куча отсортирован → `print(h)` показывает `[1, 2, 3, 9, 5]`, а `h[1]` оказывается не вторым минимумом → читать только `h[0]`, доставать через `heappop`, для `k` наименьших брать `heapq.nsmallest`.
- В кучу кладут кортежи `(priority, task)`, где `task` — объект без `__lt__` → `TypeError: '<' not supported` при равных приоритетах → добавить счётчик вставки: `(priority, counter, task)`.
- Дубликаты в BST не обработаны → `_insert` молча пропускает повтор (ни влево, ни вправо), `contains` работает, но число элементов расходится с ожидаемым → решить заранее: хранить счётчик в узле или класть равные значения вправо.

## Когда не использовать

Если нужен только поиск по ключу без диапазонов и порядка, дерево лишнее: `dict` и `set` дают `O(1)` вместо `O(log n)`. Если данные отсортированы один раз и больше не меняются, хватит списка и `bisect`. Своё BST без балансировки в рабочем коде не пишут: индексы баз данных и промышленные контейнеры уже реализованы и сбалансированы.

Куча нужна, когда минимум или максимум приходится доставать много раз по ходу работы. Если нужен весь порядок сразу, проще `sorted()`, а если данных мало, разница в сложности вообще не заметна.

## Связанные темы

- [Графы](graphs.md)
- [Рекурсия](recursion.md)
- [Линейные структуры данных](linear_structures.md)
- [Сортировки](sorting.md)
- [Нотация «О большое»](big_o_notation.md)
- [Паттерны для собеседований](interview_patterns.md)
