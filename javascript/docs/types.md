# Типы и преобразования

## Примитивы

В JavaScript семь примитивных типов:

- `string` — строки;
- `number` — числа с плавающей точкой, включая `NaN` и `Infinity`;
- `bigint` — целые числа произвольной точности;
- `boolean` — `true` и `false`;
- `undefined` — значение не задано;
- `null` — явное отсутствие значения;
- `symbol` — уникальный идентификатор.

Все остальные значения — объекты, включая массивы, функции, даты и регулярные выражения.

```js
typeof 'hello'      // 'string'
typeof 42           // 'number'
typeof undefined    // 'undefined'
typeof (() => {})   // 'function'
typeof null         // 'object' — историческая особенность

Array.isArray([])   // true
```

## Значение и ссылка

Примитивы присваиваются по значению. Для объектов копируется ссылка:

```js
const original = { count: 1 }
const same = original
same.count = 2

console.log(original.count) // 2
```

Spread создаёт только поверхностную копию. Вложенные объекты остаются общими. Для поддерживаемых данных глубокую копию можно сделать через `structuredClone(value)`.

## Сравнение

```js
0 === false              // false
0 == false               // true — произошло приведение типов
Number.isNaN(NaN)        // true
Object.is(NaN, NaN)      // true
{} === {}                // false — разные объекты
```

Используйте `===` и `!==`. Нестрогое сравнение полезно редко и требует знания правил приведения.

## Truthy и falsy

Falsy-значения: `false`, `0`, `-0`, `0n`, `''`, `null`, `undefined` и `NaN`. Все объекты truthy, включая пустые массивы и объекты.

```js
Boolean([]) // true
Boolean({}) // true
```

## Явное преобразование

```js
Number('42')       // 42
Number('')         // 0
Number('unknown')  // NaN
String(42)         // '42'
Boolean(0)         // false
parseInt('42px', 10) // 42
```

Проверять число лучше через `Number.isNaN` и `Number.isFinite`, потому что глобальные `isNaN` и `isFinite` сначала приводят аргумент к числу.
