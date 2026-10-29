# Графы

Дороги между городами, друзья в соцсети, зависимости между задачами — всё это связи между объектами. **Граф** (graph) — множество **вершин** (vertices, nodes) и **рёбер** (edges) между ними.

Виды графов:

- **ориентированный** (directed) — у рёбер есть направление;
- **неориентированный** (undirected) — направления нет;
- **взвешенный** (weighted) — у каждого ребра есть вес или стоимость;
- **циклический** или **ациклический**; ориентированный ациклический граф называют DAG (Directed Acyclic Graph);
- **связный** или **несвязный**.

## Способы представления

Пусть `V` — число вершин, `E` — число рёбер.

| Способ | Память | Поиск ребра | Соседи вершины |
|---|---|---|---|
| Список смежности (adjacency list) | O(V + E) | O(V) | O(deg(v)) |
| Матрица смежности (adjacency matrix) | O(V²) | O(1) | O(V) |
| Список рёбер (edge list) | O(E) | O(E) | O(E) |

На собеседовании в 90% случаев используют список смежности на `dict`.

### Список смежности

```python run
# Неориентированный граф
graph = {
    'A': ['B', 'C'],
    'B': ['A', 'D'],
    'C': ['A', 'D'],
    'D': ['B', 'C'],
}

# Ориентированный граф
directed = {
    'A': ['B', 'C'],
    'B': ['D'],
    'C': [],
    'D': [],
}

# Взвешенный ориентированный граф: (сосед, вес)
weighted = {
    'A': [('B', 5), ('C', 2)],
    'B': [('D', 4)],
    'C': [('D', 7)],
    'D': [],
}
```

### Матрица смежности

```python run
vertices = ['A', 'B', 'C']
idx = {v: i for i, v in enumerate(vertices)}
n = len(vertices)

matrix = [[0] * n for _ in range(n)]
edges = [('A', 'B'), ('A', 'C'), ('B', 'C')]
for u, v in edges:
    i, j = idx[u], idx[v]
    matrix[i][j] = 1
    matrix[j][i] = 1   # граф неориентированный — ребро в обе стороны

for row in matrix: print(row)
```

## Поиск в ширину (BFS)

**Поиск в ширину** (Breadth-First Search, BFS) обходит граф **слоями** от стартовой вершины: сначала все соседи, потом соседи соседей. Использует **очередь**.

Сложность: `O(V + E)`.

Применения:

- кратчайший путь в **невзвешенном** графе (по числу рёбер);
- проверка достижимости;
- обход дерева по уровням;
- поиск компонент связности.

```python run session=graphs
from collections import deque

def bfs(graph, start):
    visited = {start}
    queue = deque([start])
    order = []
    while queue:
        v = queue.popleft()
        order.append(v)
        for neighbor in graph[v]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return order

graph = {
    'A': ['B', 'C'],
    'B': ['D', 'E'],
    'C': ['F'],
    'D': [], 'E': [], 'F': [],
}
bfs(graph, 'A')   # ['A', 'B', 'C', 'D', 'E', 'F']
```

### Кратчайший путь через BFS

Вместе с вершиной храним путь до неё. Первый найденный путь до цели — кратчайший по числу рёбер.

```python run session=graphs
from collections import deque

def shortest_path(graph, start, end):
    if start == end:
        return [start]
    visited = {start}
    queue = deque([(start, [start])])
    while queue:
        v, path = queue.popleft()
        for neighbor in graph[v]:
            if neighbor in visited:
                continue
            new_path = path + [neighbor]
            if neighbor == end:
                return new_path
            visited.add(neighbor)
            queue.append((neighbor, new_path))
    return None

shortest_path(graph, 'A', 'F')   # ['A', 'C', 'F']
```

## Поиск в глубину (DFS)

**Поиск в глубину** (Depth-First Search, DFS) идёт по графу как можно глубже, а упёршись в тупик, откатывается назад. Использует **стек** — явный или стек вызовов рекурсии.

Сложность: `O(V + E)`.

Применения:

- топологическая сортировка;
- проверка графа на ацикличность;
- поиск сильно связных компонент;
- задачи с перебором и возвратом: лабиринт, судоку.

```python run session=graphs
def dfs_recursive(graph, start, visited=None, order=None):
    if visited is None:
        visited, order = set(), []
    visited.add(start)
    order.append(start)
    for neighbor in graph[start]:
        if neighbor not in visited:
            dfs_recursive(graph, neighbor, visited, order)
    return order

dfs_recursive(graph, 'A')   # ['A', 'B', 'D', 'E', 'C', 'F']
```

### DFS на явном стеке

Соседей кладём в стек в обратном порядке, чтобы обходить их в том же порядке, что и рекурсивная версия.

```python run session=graphs
def dfs_iterative(graph, start):
    visited = set()
    stack = [start]
    order = []
    while stack:
        v = stack.pop()
        if v in visited:
            continue
        visited.add(v)
        order.append(v)
        for neighbor in reversed(graph[v]):
            if neighbor not in visited:
                stack.append(neighbor)
    return order

dfs_iterative(graph, 'A')   # ['A', 'B', 'D', 'E', 'C', 'F']
```

## Сравнение BFS и DFS

| | BFS | DFS |
|---|---|---|
| Структура | очередь | стек или рекурсия |
| Порядок обхода | по слоям | вглубь, потом назад |
| Кратчайший путь (невзвешенный граф) | да | нет |
| Топологическая сортировка | нет | да |
| Память | O(ширины) | O(глубины) |

## Алгоритм Дейкстры

**Алгоритм Дейкстры** (Dijkstra) находит кратчайшие пути во взвешенном графе с **неотрицательными** весами.

На каждом шаге из непосещённых вершин берём ту, до которой известное расстояние минимально (её достаём из **min-кучи**), и **релаксируем** её рёбра — пытаемся улучшить расстояния до соседей.

Сложность с кучей: `O((V + E) · log V)`.

```python run
import heapq

def dijkstra(graph, start):
    """
    graph: {node: [(neighbor, weight), ...]}
    Возвращает: {node: min_distance}
    """
    distances = {node: float('inf') for node in graph}
    distances[start] = 0
    heap = [(0, start)]   # (distance, node)

    while heap:
        d, u = heapq.heappop(heap)
        if d > distances[u]:
            continue                # устаревшая запись
        for v, w in graph[u]:
            new_d = d + w
            if new_d < distances[v]:
                distances[v] = new_d
                heapq.heappush(heap, (new_d, v))
    return distances

weighted_graph = {
    'A': [('B', 5), ('C', 2)],
    'B': [('D', 4)],
    'C': [('B', 1), ('D', 7)],
    'D': [],
}
dijkstra(weighted_graph, 'A')   # {'A': 0, 'B': 3, 'C': 2, 'D': 7}
```

### Почему Дейкстра не работает с отрицательными весами

Алгоритм опирается на то, что **уже посещённую вершину пересматривать не нужно**. Если в графе есть отрицательное ребро, путь через уже «закрытую» вершину может оказаться короче, но алгоритм его пропустит.

Для отрицательных весов используют **алгоритм Беллмана — Форда** (Bellman-Ford), `O(V·E)`.

## Топологическая сортировка

**Топологическая сортировка** применима только к DAG. Она упорядочивает вершины так, что для любого ребра `u → v` вершина `u` идёт раньше `v`.

Применения: порядок сборки, разрешение зависимостей, расписания.

Ниже — алгоритм Кана: считаем для каждой вершины число входящих рёбер, затем по очереди забираем вершины, в которые ничего не входит.

```python run
from collections import deque

def topological_sort(graph):
    # граф ориентированный: graph[u] = [v1, v2, ...]
    in_degree = {v: 0 for v in graph}
    for u in graph:
        for v in graph[u]:
            in_degree[v] = in_degree.get(v, 0) + 1

    queue = deque([v for v, d in in_degree.items() if d == 0])
    order = []
    while queue:
        u = queue.popleft()
        order.append(u)
        for v in graph.get(u, []):
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)

    if len(order) != len(in_degree):
        raise ValueError('Цикл в графе')
    return order

tasks = {
    'wake_up': ['breakfast'],
    'breakfast': ['work'],
    'shower': ['breakfast', 'work'],
    'work': [],
}
topological_sort(tasks)   # ['wake_up', 'shower', 'breakfast', 'work']
```

## Что спрашивают на собеседовании

- Чем **BFS** отличается от **DFS** и где что применять?
- Как **обнаружить цикл** в графе? *(В неориентированном — DFS с проверкой повторного посещения, не считая родителя. В ориентированном — DFS с тремя состояниями вершин: белая, серая, чёрная.)*
- Когда применять **Дейкстру**, а когда **Беллмана — Форда**?
- Как определить **порядок выполнения задач** с зависимостями? *(Топологической сортировкой.)*
- Чем **список смежности** отличается от **матрицы смежности** и когда что выбирать?

## Связанные темы

- [Деревья](trees.md)
- [Линейные структуры данных](linear_structures.md)
- [Динамическое программирование](dynamic_programming.md)
- [Рекурсия](recursion.md)
