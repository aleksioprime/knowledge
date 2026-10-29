# JSON

Объект нужно отправить на сервер, сохранить в `localStorage` или записать в файл — а всё это принимает только текст. JSON превращает объект в строку и обратно, но по дороге теряет даты, `undefined` и методы, а некорректная строка из внешнего источника роняет программу с `SyntaxError`. Здесь правила формата, `JSON.stringify()` с `replacer` и `toJSON()`, `JSON.parse()` с `reviver` и то, что остаётся проверить после разбора.

## Минимальный пример

```js
const task = {
  id: 7,
  title: 'Сдать отчёт',
  done: false,
  createdAt: new Date('2026-01-15T10:00:00Z'),
  notes: undefined,
}

const json = JSON.stringify(task)
console.log(json)
// {"id":7,"title":"Сдать отчёт","done":false,"createdAt":"2026-01-15T10:00:00.000Z"}

const restored = JSON.parse(json)
console.log(restored.title) // Сдать отчёт
console.log(typeof restored.createdAt) // string — дата вернулась строкой
console.log('notes' in restored) // false — undefined пропущен при сериализации
```

## Как это работает

JSON (JavaScript Object Notation) — текстовый формат обмена данными. Он похож на синтаксис объектов JavaScript, но является отдельным форматом с более строгими правилами:

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

### `JSON.stringify()`

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

#### `replacer`

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

#### Форматирование через `space`

Третий аргумент `JSON.stringify()` задаёт отступы и делает результат удобным для чтения человеком.

```js
JSON.stringify(user, null, 2)
```

Третий аргумент добавляет отступы для чтения человеком. Для передачи по сети обычно используют компактный вариант без отступов.

#### `toJSON()`

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

### `JSON.parse()`

Преобразует JSON-строку в JavaScript-значение:

```js
const user = JSON.parse('{"id":42,"name":"Alex"}')
```

Сигнатура: `JSON.parse(text, reviver?)`. Некорректный JSON вызывает `SyntaxError`. Поэтому данные из внешнего источника нельзя считать корректными заранее: возможную ошибку разбора следует обработать на границе получения данных.

Успешный `JSON.parse()` проверяет только синтаксис, но не структуру и типы данных. Результат API всё равно нужно валидировать.

#### `reviver`

Функция `reviver(key, value)` вызывается для разобранных значений и может восстановить нужные типы:

```js
const data = JSON.parse(text, (key, value) => {
  if (key === 'createdAt') return new Date(value)
  return value
})
```

Возврат `undefined` удаляет свойство из результата.

## Частые ошибки

- `Date` сериализован и прочитан обратно без `reviver` → после `JSON.parse()` поле стало строкой, `createdAt.getFullYear()` даёт `TypeError` → восстанавливать дату через `reviver` или `new Date(value)` на границе получения данных.
- `JSON.parse()` вызван на ответе сервера без обработки ошибок → при HTML-странице с ошибкой вместо JSON программа падает с `SyntaxError` → оборачивать разбор в `try...catch` и проверять `Content-Type`.
- В JSON-строке одинарные кавычки, комментарий или запятая после последнего элемента → `SyntaxError`, хотя как объект JavaScript это выглядело корректно → помнить, что JSON строже литерала объекта: только двойные кавычки, без комментариев и trailing comma.
- Объект с циклической ссылкой (например, задача ссылается на проект, проект — на список задач) передан в `JSON.stringify()` → `TypeError: Converting circular structure to JSON` → формировать плоский объект для передачи или исключать поле через `replacer`.
- Успешный `JSON.parse()` принят за проверку данных → в коде дальше `user.id` оказывается строкой или отсутствует, ошибка всплывает далеко от места получения → валидировать структуру и типы после разбора.

## Когда не использовать

JSON не подходит как способ глубокого копирования объекта: `JSON.parse(JSON.stringify(obj))` теряет даты, `undefined`, `Map`, `Set` и методы. Для копии берите `structuredClone()`.

Для хранения в коде и настройках, где нужны комментарии, trailing comma и многострочные строки, JSON неудобен — для этого есть YAML или TOML. А если данные бинарные или их очень много, текстовый JSON раздувает трафик: там уместнее специализированные бинарные форматы или `FormData` для файлов.

## Связанные темы

- [Объекты](objects.md) — что именно превращается в JSON, а что теряется
- [HTTP-запросы: Fetch и Axios](requests.md) — `response.json()` и отправка JSON в `fetch()`
- [Ошибки и отладка](errors.md) — обработка `SyntaxError` при разборе
