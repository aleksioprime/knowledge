# Коллекции и перебор

Помимо массивов, JavaScript предоставляет `Map`, `Set`, `WeakMap` и `WeakSet`. Выбор коллекции зависит от того, нужны ли пары ключ–значение, уникальность и слабые ссылки.

## `Map`

`Map` хранит пары ключ–значение, допускает ключи любого типа и сохраняет порядок добавления:

```js
const roles = new Map()
const user = { id: 1 }

roles.set(user, 'admin')
roles.get(user) // 'admin'
roles.has(user) // true
roles.size // 1

roles.delete(user)
roles.clear()
```

`set()` возвращает саму коллекцию, поэтому вызовы можно объединять в цепочку. `get()` возвращает значение или `undefined`, `has()` и `delete()` — boolean.

Для записей с заранее известными строковыми ключами обычно удобнее объект. Для динамической коллекции и нестроковых ключей — `Map`.

### Перебор `Map`

При переборе `Map` сохраняет порядок добавления записей. По умолчанию каждая итерация возвращает пару `[key, value]`, которую удобно сразу деструктурировать.

```js
for (const [key, value] of roles) {
  console.log(key, value)
}

roles.keys()
roles.values()
roles.entries()
```

Сам `Map` и его `entries()` возвращают пары `[key, value]`.

`forEach()` у `Map` получает аргументы `(value, key, map)`, то есть значение идёт раньше ключа:

```js
roles.forEach((value, key) => {
  console.log(key, value)
})
```

## `Set`

`Set` хранит уникальные значения и сохраняет порядок добавления:

```js
const tags = new Set(['js', 'vue', 'js'])

tags.size // 2
tags.has('vue') // true
tags.add('html') // возвращает tags
tags.delete('js')
tags.clear()
```

Объекты считаются одинаковыми только при совпадении ссылки. Частый пример удаления повторяющихся примитивов:

```js
const unique = [...new Set([1, 1, 2, 3])] // Set убирает повторы
unique // [1, 2, 3]
```

`Set` перебирается через `for...of`, `values()`, `keys()` или `forEach()`. Для совместимости с `Map` методы `keys()` и `values()` у `Set` ведут себя одинаково.

## `WeakMap`

`WeakMap` хранит значения по слабым ключам. Ключами могут быть объекты или незарегистрированные symbols, значениями — любые данные.

```js
const metadata = new WeakMap()
let button = document.querySelector('button')

metadata.set(button, { clicks: 0 })
metadata.get(button)
metadata.has(button)
metadata.delete(button)

button = null
```

Методы:

- `set(key, value)` добавляет запись и возвращает коллекцию;
- `get(key)` возвращает значение или `undefined`;
- `has(key)` проверяет наличие записи;
- `delete(key)` удаляет запись и возвращает boolean.

`WeakMap` подходит для метаданных и кешей, время жизни которых не должно превышать время жизни объекта-ключа.

## `WeakSet`

`WeakSet` хранит слабые значения — объекты или незарегистрированные symbols.

```js
const processed = new WeakSet()
let user = { id: 1 }

processed.add(user)
processed.has(user) // true
processed.delete(user)

user = null
```

Методы `add()`, `has()` и `delete()` похожи на соответствующие методы `Set`. `WeakSet` полезен для отметки уже обработанных объектов без продления их времени жизни.

Weak-коллекции нельзя перебирать, у них нет `size` и `clear`: иначе результат зависел бы от непредсказуемого момента сборки мусора. Нельзя узнать, когда именно сборщик удалил запись.

## `Map` и `WeakMap`

| Особенность | `Map` | `WeakMap` |
|---|---|---|
| Ключи | любые значения | объекты и незарегистрированные symbols |
| Перебор | да | нет |
| `size`, `clear()` | есть | нет |
| Влияние на жизнь объекта-ключа | удерживает | не удерживает само по себе |

Используйте `Map`, когда коллекцию нужно просматривать или ключи могут быть примитивами. Используйте `WeakMap` для привязки служебных данных к объектам.

## `Set` и `WeakSet`

| Особенность | `Set` | `WeakSet` |
|---|---|---|
| Значения | любые | объекты и незарегистрированные symbols |
| Перебор | да | нет |
| `size`, `clear()` | есть | нет |
| Влияние на жизнь объекта | удерживает | не удерживает само по себе |

Используйте `Set` для обычной коллекции уникальных значений, `WeakSet` — для временной отметки объектов.

| Коллекция | Содержимое | Перебор | Размер |
|---|---|---:|---:|
| `Map` | ключи и значения любых типов | да | да |
| `Set` | уникальные значения любых типов | да | да |
| `WeakMap` | слабые ключи и любые значения | нет | нет |
| `WeakSet` | слабые значения | нет | нет |

## Iterable и iterator

Массивы, строки, `Map` и `Set` являются iterable и поддерживают `for...of` и spread. Обычный объект напрямую не iterable.

Итерируемый объект предоставляет метод с ключом `Symbol.iterator`. Этот метод возвращает iterator с методом `next()`:

```js
const range = {
  from: 1,
  to: 3,

  *[Symbol.iterator]() {
    for (let value = this.from; value <= this.to; value += 1) {
      yield value
    }
  },
}

[...range] // [1, 2, 3]
```

`next()` возвращает объект `{ value, done }`. Значение `done: true` означает, что перебор закончен.

## Генераторы

Функция `function*` может приостанавливать выполнение через `yield` и продолжать его после `next()`. Вызов генератора возвращает iterator, а не выполняет всё тело сразу.

```js
function* ids() {
  yield 1
  yield 2
}

const iterator = ids()

iterator.next() // { value: 1, done: false }
iterator.next() // { value: 2, done: false }
iterator.next() // { value: undefined, done: true }
```

Генератор одновременно является iterable и iterator, поэтому его можно перебирать через `for...of`.
