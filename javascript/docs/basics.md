# Основы синтаксиса

## Переменные

```js
const name = 'Alex' // нельзя переназначить переменную
let count = 0       // значение можно переназначать

count += 1
```

По умолчанию используйте `const`, а `let` — когда требуется переназначение. `const` не делает объект неизменяемым:

```js
const user = { name: 'Alex' }
user.name = 'Anna' // допустимо
// user = {}       // TypeError
```

`var` имеет область видимости функции, допускает повторное объявление и поднимается иначе, чем `let` и `const`. В современном коде он обычно не нужен.

## Условия

```js
if (score >= 90) {
  console.log('Отлично')
} else if (score >= 60) {
  console.log('Зачёт')
} else {
  console.log('Нужно повторить')
}

const label = active ? 'Активен' : 'Отключён'
```

Для сравнения обычно используют строгие операторы `===` и `!==`, которые не выполняют неявное приведение типов.

## Циклы

```js
for (const user of users) {
  console.log(user.name) // значения iterable-объекта
}

for (const key in user) {
  console.log(key) // перечисляемые ключи объекта
}
```

Для массивов часто выразительнее `map`, `filter`, `find`, `some` и `every`. `forEach` не умеет прерываться через `break` и не ожидает асинхронный callback.

## Полезные операторы

```js
const city = user.address?.city          // optional chaining
const title = value ?? 'Без названия'    // только для null и undefined
const fallback = value || 'По умолчанию' // для любого falsy-значения

const copy = { ...user, active: true }
const [first, ...rest] = items
const { id, name: displayName } = user
```

`??` сохраняет допустимые значения `0`, `false` и `''`, тогда как `||` заменяет их правым операндом.

## `switch`

```js
switch (status) {
  case 'pending':
    startPolling()
    break
  case 'done':
    showResult()
    break
  default:
    showUnknownStatus()
}
```

Без `break`, `return` или `throw` выполнение продолжится в следующей ветке.
