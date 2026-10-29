# JSON

JSON — текстовый формат обмена данными. Он похож на синтаксис объектов JavaScript, но является отдельным форматом с более строгими правилами.

```json
{
  "id": 42,
  "name": "Alex",
  "active": true,
  "roles": ["user", "admin"],
  "avatar": null
}
```

JSON поддерживает объекты, массивы, строки, конечные числа, boolean и `null`. Ключи и строки записываются только в двойных кавычках. Комментарии, функции, `undefined`, trailing comma и одинарные кавычки не поддерживаются.

## `JSON.stringify()`

Преобразует поддерживаемое JavaScript-значение в JSON-строку:

```js
const json = JSON.stringify({ id: 42, name: 'Alex' })
// '{"id":42,"name":"Alex"}'
```

Сигнатура: `JSON.stringify(value, replacer?, space?)`.

Особенности преобразования:

- свойства объекта со значениями `undefined`, function и `Symbol` пропускаются;
- такие значения внутри массива превращаются в `null`;
- `NaN` и `Infinity` превращаются в `null`;
- `Date` преобразуется в ISO-строку через `toJSON()`;
- `BigInt` без пользовательского преобразования вызывает `TypeError`;
- циклическая ссылка вызывает `TypeError`.

### `replacer`

Массив разрешает оставить только выбранные свойства:

```js
JSON.stringify(user, ['id', 'name'])
```

Функция может преобразовывать или исключать значения. Возврат `undefined` исключает свойство:

```js
const json = JSON.stringify(user, (key, value) => {
  if (key === 'password') return undefined
  return value
})
```

### Форматирование через `space`

Третий аргумент `JSON.stringify()` задаёт отступы и делает результат удобным для чтения человеком.

```js
JSON.stringify(user, null, 2)
```

Третий аргумент добавляет отступы для чтения человеком. Для передачи по сети обычно используют компактный вариант без отступов.

### `toJSON()`

Если у объекта есть метод `toJSON()`, `JSON.stringify()` сериализует возвращённое им значение:

```js
const user = {
  id: 42,
  password: 'secret',

  toJSON() {
    return { id: this.id }
  },
}

JSON.stringify(user) // '{"id":42}'
```

Так работают, например, объекты `Date`. Для безопасности API всё равно лучше формировать публичные данные явно, а не полагаться только на `toJSON()`.

## `JSON.parse()`

Преобразует JSON-строку в JavaScript-значение:

```js
const user = JSON.parse('{"id":42,"name":"Alex"}')
```

Сигнатура: `JSON.parse(text, reviver?)`. Некорректный JSON вызывает `SyntaxError`. Поэтому данные из внешнего источника нельзя считать корректными заранее: возможную ошибку разбора следует обработать на границе получения данных.

Успешный `JSON.parse()` проверяет только синтаксис, но не структуру и типы данных. Результат API всё равно нужно валидировать.

### `reviver`

Функция `reviver(key, value)` вызывается для разобранных значений и может восстановить нужные типы:

```js
const data = JSON.parse(text, (key, value) => {
  if (key === 'createdAt') return new Date(value)
  return value
})
```

Возврат `undefined` удаляет свойство из результата.
