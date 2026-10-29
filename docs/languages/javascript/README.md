# JavaScript

**JavaScript** — динамический язык программирования, основной язык браузера. Он также выполняется вне браузера, например в Node.js, Deno и Bun. Стандарт языка называется ECMAScript, а DOM, `fetch`, таймеры и файловая система относятся к API конкретной среды выполнения.

## Содержание

- [Основы синтаксиса](basics.md) — переменные, операторы и управляющие конструкции
- [Типы и преобразования](types.md) — примитивы, объекты, сравнение и truthy/falsy
- [Функции и области видимости](functions.md) — hoisting, замыкания, `this` и функции высшего порядка
- [Массивы и методы массивов](arrays.md)
- [Коллекции и перебор](collections.md) — Map, Set, weak-коллекции, iterable и генераторы
- [Деструктуризация, spread и rest](destructuring.md) — массивы, объекты, копирование и параметры функций
- [JSON](json.md) — stringify, parse, replacer, reviver и ограничения
- [Регулярные выражения](regexp.md) — синтаксис, флаги, группы и методы
- [Объекты](objects.md) — свойства, методы `Object`, копирование, Proxy и память
- [Прототипы и прототипное наследование](prototypes.md)
- [Классы и ООП](classes.md) — поля, методы, наследование, `super`, примеси и композиция
- [Асинхронность](async.md) — Promise, async/await и event loop
- [HTTP-запросы: Fetch и Axios](requests.md)
- [WebSocket](websocket.md) — постоянное двустороннее соединение с сервером
- [Модули](modules.md) — import/export и организация кода
- [DOM](dom.md) — дерево документа, поиск, навигация и изменение элементов
- [События в браузере](events.md) — обработчики, распространение, делегирование и CustomEvent
- [JavaScript в браузере](browser.md) — таймеры, планирование и хранилища
- [Ошибки и отладка](errors.md)

## Быстрый пример

```js
const users = [
  { id: 1, name: 'Анна', active: true },
  { id: 2, name: 'Иван', active: false },
]

const activeNames = users
  .filter((user) => user.active)
  .map((user) => user.name)

console.log(activeNames) // ['Анна']
```

## Связанные разделы

- [Vue.js](../vue/README.md) — компонентный frontend-фреймворк
- [HTTP](../../backend/web/http/README.md) — протокол, используемый `fetch` и другими клиентами
- [Веб-безопасность](../../backend/web/security/README.md) — XSS, CSRF, CORS и защитные заголовки
