# JavaScript

**JavaScript** — динамический язык программирования, основной язык браузера. Он также выполняется вне браузера, например в Node.js, Deno и Bun. Стандарт языка называется ECMAScript, а DOM, `fetch`, таймеры и файловая система относятся к API конкретной среды выполнения.

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

## Содержание

- [Основы синтаксиса](docs/basics.md) — переменные, операторы и управляющие конструкции
- [Типы и преобразования](docs/types.md) — примитивы, объекты, сравнение и truthy/falsy
- [Функции и области видимости](docs/functions.md) — hoisting, замыкания, `this` и функции высшего порядка
- [Массивы и методы массивов](docs/arrays.md)
- [Коллекции и перебор](docs/collections.md) — Map, Set, weak-коллекции, iterable и генераторы
- [Деструктуризация, spread и rest](docs/destructuring.md) — массивы, объекты, копирование и параметры функций
- [JSON](docs/json.md) — stringify, parse, replacer, reviver и ограничения
- [Регулярные выражения](docs/regexp.md) — синтаксис, флаги, группы и методы
- [Объекты](docs/objects.md) — свойства, методы `Object`, копирование, Proxy и память
- [Прототипы и прототипное наследование](docs/prototypes.md)
- [Классы и ООП](docs/classes.md) — поля, методы, наследование, `super`, примеси и композиция
- [Асинхронность](docs/async.md) — Promise, async/await и event loop
- [HTTP-запросы: Fetch и Axios](docs/requests.md)
- [WebSocket](docs/websocket.md) — постоянное двустороннее соединение с сервером
- [Модули](docs/modules.md) — import/export и организация кода
- [DOM](docs/dom.md) — дерево документа, поиск, навигация и изменение элементов
- [События в браузере](docs/events.md) — обработчики, распространение, делегирование и CustomEvent
- [JavaScript в браузере](docs/browser.md) — таймеры, планирование и хранилища
- [Ошибки и отладка](docs/errors.md)

## Связанные разделы

- [Vue.js](../vuejs/README.md) — компонентный frontend-фреймворк
- [HTTP](../web/http/README.md) — протокол, используемый `fetch` и другими клиентами
- [Веб-безопасность](../web/security/README.md) — XSS, CSRF, CORS и защитные заголовки
