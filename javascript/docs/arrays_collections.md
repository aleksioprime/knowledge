# Массивы и коллекции

## Массивы

```js
const numbers = [3, 1, 2]

numbers.push(4)              // изменяет массив
const doubled = numbers.map((n) => n * 2)
const even = numbers.filter((n) => n % 2 === 0)
const firstLarge = numbers.find((n) => n > 2)
const total = numbers.reduce((sum, n) => sum + n, 0)
```

Частые методы:

| Не изменяют исходный массив | Изменяют исходный массив |
|---|---|
| `map`, `filter`, `find`, `slice`, `concat` | `push`, `pop`, `shift`, `unshift`, `splice` |
| `some`, `every`, `includes`, `join` | `sort`, `reverse`, `fill` |
| `toSorted`, `toReversed`, `toSpliced` | — |

Обычный `sort()` сравнивает элементы как строки и изменяет массив:

```js
[10, 2, 1].toSorted((a, b) => a - b) // [1, 2, 10]
```

## `Map`

`Map` хранит пары ключ–значение, допускает ключи любого типа и сохраняет порядок добавления:

```js
const roles = new Map()
roles.set(user, 'admin')
roles.get(user) // 'admin'
roles.has(user) // true
```

Для записей с заранее известными строковыми ключами обычно удобнее объект. Для динамической коллекции и нестроковых ключей — `Map`.

## `Set`

`Set` хранит уникальные значения:

```js
const unique = [...new Set([1, 1, 2, 3])] // [1, 2, 3]
```

Объекты считаются одинаковыми только при совпадении ссылки.

## Перебор

Массивы, строки, Map и Set являются iterable и поддерживают `for...of` и spread. Обычный объект напрямую не iterable:

```js
for (const [key, value] of Object.entries(user)) {
  console.log(key, value)
}
```
