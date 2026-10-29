# Линейные структуры данных

Связный список, стек, очередь и дек — самые базовые структуры данных. На них строятся обходы графов, отмена действий в редакторах, очереди задач и многое другое.

## Односвязный список

В **односвязном списке** (singly linked list) каждый узел хранит значение и ссылку на следующий узел.

Сложность:

- вставка и удаление в начале — `O(1)`;
- вставка и удаление в конце — `O(n)` (нужно дойти до конца) или `O(1)`, если хранить ссылку на хвост `tail`;
- поиск и доступ по индексу — `O(n)`.

```python run session=linked
class Node:
    def __init__(self, value):
        self.value = value
        self.next = None

class LinkedList:
    def __init__(self):
        self.head = None

    def append(self, value):
        node = Node(value)
        if self.head is None:
            self.head = node
            return
        current = self.head
        while current.next:
            current = current.next
        current.next = node

    def prepend(self, value):
        node = Node(value)
        node.next = self.head
        self.head = node

    def remove(self, value):
        if self.head is None:
            return
        if self.head.value == value:
            self.head = self.head.next
            return
        current = self.head
        while current.next:
            if current.next.value == value:
                current.next = current.next.next
                return
            current = current.next

    def to_list(self):
        result, cur = [], self.head
        while cur:
            result.append(cur.value); cur = cur.next
        return result

ll = LinkedList()
for x in [1, 2, 3]:
    ll.append(x)
ll.prepend(0)
ll.remove(2)
ll.to_list()   # [0, 1, 3]
```

## Двусвязный список

В **двусвязном списке** (doubly linked list) каждый узел ссылается и на следующий, и на предыдущий. Поэтому вставлять и удалять элементы с обоих концов можно за `O(1)`. На нём основаны **очередь** и **дек**.

## Стек

**Стек** (stack) работает по принципу **LIFO** (Last In, First Out — «последним пришёл, первым ушёл»). Как стопка тарелок: кладём и забираем сверху.

Применения: стек вызовов функций, отмена и повтор действий (undo/redo), проверка скобок, обход в глубину.

На обычном `list` все операции стека выполняются за `O(1)`:

```python run
stack = []
stack.append(1)    # push
stack.append(2)
stack.append(3)
print(stack[-1])   # peek: 3
print(stack.pop()) # 3
print(stack)       # [1, 2]
```

### Задача: проверка сбалансированности скобок

Открывающие скобки кладём в стек. Каждая закрывающая должна совпасть по типу с верхней скобкой в стеке.

```python run
def is_balanced(s):
    pairs = {')': '(', ']': '[', '}': '{'}
    stack = []
    for ch in s:
        if ch in '([{':
            stack.append(ch)
        elif ch in ')]}':
            if not stack or stack.pop() != pairs[ch]:
                return False
    return not stack

print(is_balanced('({[]})'))   # True
print(is_balanced('({[})'))    # False
```

## Очередь

**Очередь** (queue) работает по принципу **FIFO** (First In, First Out — «первым пришёл, первым ушёл»): кто встал в очередь первым, того первым и обслужат.

На `list` очередь делать не стоит: `pop(0)` работает за `O(n)`. Нужен двусвязный список или `collections.deque`.

```python run
from collections import deque

queue = deque()
queue.append(1)        # enqueue, O(1)
queue.append(2)
queue.append(3)
print(queue.popleft()) # dequeue, O(1): 1
print(queue)           # deque([2, 3])
```

### Очередь на двусвязном списке

Реализация вручную: храним ссылки на голову и хвост, добавляем в хвост, забираем из головы.

```python run
class _Node:
    def __init__(self, value):
        self.value = value
        self.prev = None
        self.next = None

class Queue:
    def __init__(self):
        self.head = None
        self.tail = None

    def enqueue(self, value):       # O(1)
        node = _Node(value)
        if self.tail is None:
            self.head = self.tail = node
        else:
            node.prev = self.tail
            self.tail.next = node
            self.tail = node

    def dequeue(self):              # O(1)
        if self.head is None:
            raise IndexError('queue is empty')
        node = self.head
        self.head = node.next
        if self.head is None:
            self.tail = None
        else:
            self.head.prev = None
        return node.value

q = Queue()
for x in [1, 2, 3]:
    q.enqueue(x)
print(q.dequeue(), q.dequeue(), q.dequeue())  # 1 2 3
```

## Дек

**Дек** (deque, double-ended queue — двусторонняя очередь) позволяет вставлять и удалять элементы с обоих концов за `O(1)`. В Python это `collections.deque`. Внутри он устроен как двусвязный список из блоков фиксированного размера.

```python run
from collections import deque

d = deque([1, 2, 3])
d.appendleft(0)   # deque([0, 1, 2, 3])
d.append(4)       # deque([0, 1, 2, 3, 4])
print(d.popleft())  # 0
print(d.pop())      # 4
print(d)            # deque([1, 2, 3])
```

## Что спрашивают на собеседовании

- Чем `list` в Python отличается от связного списка? *(`list` — массив с запасом места: доступ по индексу за O(1). Связный список — доступ по индексу за O(n), зато вставка в начало за O(1).)*
- Как эффективно сделать **очередь** в Python? *(`collections.deque`.)*
- Как **развернуть** односвязный список?
- Как обнаружить **цикл** в связном списке? *(Алгоритм Флойда «черепаха и заяц».)*
- Когда нужен **стек**, а когда **очередь**? *(Классика — DFS и BFS.)*

### Разворот односвязного списка

Идём по списку и перенаправляем каждую ссылку `next` на предыдущий узел. Пример использует классы `Node` и `LinkedList` из начала заметки.

```python run session=linked
def reverse(head):
    prev = None
    cur = head
    while cur:
        nxt = cur.next
        cur.next = prev
        prev = cur
        cur = nxt
    return prev

ll = LinkedList()
for x in [1, 2, 3, 4]:
    ll.append(x)
ll.head = reverse(ll.head)
ll.to_list()   # [4, 3, 2, 1]
```

### Обнаружение цикла: черепаха и заяц

Медленный указатель делает один шаг, быстрый — два. Если в списке есть цикл, быстрый рано или поздно догонит медленный.

```python run session=linked
def has_cycle(head):
    slow = fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        if slow is fast:
            return True
    return False

a, b, c = Node(1), Node(2), Node(3)
a.next = b
b.next = c
print(has_cycle(a))   # False
c.next = a            # замыкаем список в кольцо
print(has_cycle(a))   # True
```

## Связанные темы

- [Хеш-таблицы](hash_table.md)
- [Деревья](trees.md)
- [Графы](graphs.md)
- [Нотация «О большое»](big_o_notation.md)
