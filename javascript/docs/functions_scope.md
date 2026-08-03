# Функции и области видимости

## Объявление функций

```js
function add(a, b = 0) {
  return a + b
}

const multiply = function (a, b) {
  return a * b
}

const square = (value) => value ** 2
```

Function declaration доступна до строки объявления. Function expression и arrow function становятся доступны после инициализации переменной.

## Rest-параметры и spread

```js
function sum(...numbers) {
  return numbers.reduce((total, number) => total + number, 0)
}

const values = [1, 2, 3]
sum(...values)
```

Rest собирает аргументы в массив, spread раскрывает iterable в отдельные аргументы или элементы.

## Область видимости

`let` и `const` имеют блочную область видимости. Функция видит собственные переменные и внешнее лексическое окружение:

```js
function createCounter() {
  let value = 0

  return () => {
    value += 1
    return value
  }
}

const next = createCounter()
next() // 1
next() // 2
```

Возвращённая функция сохраняет доступ к `value`. Это называется замыканием.

## `this`

У обычной функции `this` определяется способом вызова:

```js
const user = {
  name: 'Alex',
  greet() {
    return `Привет, ${this.name}`
  },
}

user.greet() // this === user
```

Arrow function не создаёт собственный `this`, а берёт его из внешней области. Поэтому её удобно использовать в callback, но обычно не стоит использовать как метод, которому нужен динамический `this`.

```js
const greet = user.greet
greet()                // контекст user потерян
user.greet.bind(user)() // контекст привязан явно
```

Методы `call`, `apply` и `bind` позволяют явно задать `this`; `bind` возвращает новую функцию.
