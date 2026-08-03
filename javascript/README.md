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
- [Функции и области видимости](docs/functions_scope.md) — функции, замыкания и `this`
- [Массивы и коллекции](docs/arrays_collections.md) — Array, Map и Set
- [Объекты, прототипы и классы](docs/objects_classes.md)
- [Асинхронность](docs/async.md) — Promise, async/await и event loop
- [HTTP-запросы: Fetch и Axios](docs/http_requests.md)
- [Модули](docs/modules.md) — import/export и организация кода
- [JavaScript в браузере](docs/browser.md) — DOM, события, fetch и хранилища
- [Ошибки и отладка](docs/errors.md)

## Связанные разделы

- [Vue.js](../vuejs/README.md) — компонентный frontend-фреймворк
- [HTTP](../web/http/README.md) — протокол, используемый `fetch` и другими клиентами
- [Веб-безопасность](../web/security/README.md) — XSS, CSRF, CORS и защитные заголовки
