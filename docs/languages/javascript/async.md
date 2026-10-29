# Асинхронность

Запрос к серверу или таймер занимают время, а JavaScript выполняет код в одном стеке вызовов: если ждать ответа «на месте», интерфейс замрёт. Асинхронность (asynchrony) позволяет начать операцию сейчас, продолжить работу и получить результат позже — через callback, Promise или `async/await`. Здесь разобраны все три способа и очередь задач event loop, которая определяет порядок их выполнения.

## Минимальный пример

```js
function delay(milliseconds, value) {
  return new Promise((resolve) => setTimeout(() => resolve(value), milliseconds))
}

async function loadTask(id) {
  const task = await delay(100, { id, title: 'Купить хлеб' })
  return task.title
}

console.log('запрос отправлен')
loadTask(1).then((title) => console.log(title))
console.log('код после вызова')

// запрос отправлен
// код после вызова
// Купить хлеб
```

## Как это работает

### Что означает асинхронное действие

Асинхронная операция начинается сейчас, а завершается позже. Пока браузер ждёт таймер, ответ сервера или действие пользователя, JavaScript может выполнять другой код.

```js
console.log('Начало')

setTimeout(() => {
  console.log('Таймер завершён')
}, 1000)

console.log('Конец')

// Начало
// Конец
// Таймер завершён
```

Асинхронность не означает обязательное параллельное выполнение JavaScript-кода. Она позволяет не блокировать стек вызовов во время ожидания внешней операции.

### Callback

Callback — функция, которую передают другой функции, чтобы та вызвала её в нужный момент:

```js
function greet(name, callback) {
  console.log(`Привет, ${name}`)
  callback()
}

greet('Анна', () => {
  console.log('Приветствие завершено')
})
```

Callback не обязательно асинхронный. Например, callback метода `map` выполняется синхронно, а callback `setTimeout` — позже.

В старых и некоторых серверных API часто используется соглашение error-first callback: первым аргументом приходит ошибка, вторым — результат.

```js
loadUser(42, (error, user) => {
  if (error) {
    console.error(error)
    return
  }

  console.log(user)
})
```

#### Callback hell

Если каждая следующая операция зависит от предыдущей, callbacks начинают глубоко вкладываться друг в друга:

```js
loadUser(42, (userError, user) => {
  if (userError) {
    handleError(userError)
    return
  }

  loadPosts(user.id, (postsError, posts) => {
    if (postsError) {
      handleError(postsError)
      return
    }

    saveReport(posts, (reportError, report) => {
      if (reportError) {
        handleError(reportError)
        return
      }

      showReport(report)
    })
  })
})
```

Это называют callback hell: код уходит вправо, обработка ошибок повторяется, а порядок действий трудно читать и изменять. Вложенность можно уменьшить именованными функциями, но для последовательных асинхронных операций обычно удобнее Promise и `async/await`.

### Promise

Promise — объект, представляющий будущий результат асинхронной операции. Он находится в одном из состояний:

- `pending` — ожидание;
- `fulfilled` — операция успешно завершена;
- `rejected` — операция завершена ошибкой.

`fulfilled` и `rejected` вместе называют `settled`. После перехода из `pending` состояние и результат Promise уже не меняются. Обычного публичного свойства вроде `promise.state` для синхронного чтения состояния нет.

#### Создание Promise

Конструктор `Promise` принимает функцию executor. Она вызывается синхронно и получает две функции: `resolve` для успешного результата и `reject` для ошибки.

```js
function delay(milliseconds) {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve('Время вышло')
    }, milliseconds)
  })
}

delay(1000).then((message) => console.log(message))
```

Полная форма выглядит так:

```js
const promise = new Promise((resolve, reject) => {

  if (operationSucceeded) {
    resolve(result)
  } else {
    reject(new Error('Не удалось выполнить операцию'))
  }
})
```

- `new Promise(...)` сразу возвращает созданный Promise;
- значение, возвращённое самим executor через `return`, игнорируется;
- синхронный `throw` внутри executor превращается в отклонение Promise;
- учитывается только первый вызов `resolve` или `reject`;
- если передать в `resolve` другой Promise, результат будет ожидаться.

Не оборачивайте в `new Promise` функцию, которая уже возвращает Promise: обычно её результат можно вернуть напрямую.

#### Промисификация

Промисификация — преобразование API с callback в функцию, возвращающую Promise:

```js
function loadUserAsync(id) {
  return new Promise((resolve, reject) => {
    loadUser(id, (error, user) => {
      if (error) {
        reject(error)
        return
      }

      resolve(user)
    })
  })
}
```

Промисифицировать имеет смысл только API, которое само ещё не возвращает Promise. В Node.js для стандартного error-first соглашения также существует `util.promisify`.

#### `then`, `catch` и `finally`

Эти методы создают цепочку обработки Promise: `then()` принимает успешный результат, `catch()` перехватывает ошибку, а `finally()` выполняет завершающее действие при любом исходе.

```js
loadUsers()
  .then((users) => normalizeUsers(users))
  .then((users) => console.log(users))
  .catch((error) => console.error(error))
  .finally(() => hideLoader())
```

- `then(onFulfilled, onRejected)` обрабатывает успех и, необязательно, ошибку;
- `catch(onRejected)` обрабатывает ошибку и равнозначен `then(undefined, onRejected)`;
- `finally(onFinally)` выполняется после любого исхода и обычно используется для общей очистки: скрыть индикатор, закрыть соединение и так далее.

`finally` не получает результат операции. Обычно он пропускает прежний результат или ошибку дальше. Но если callback в `finally` бросит ошибку или вернёт отклонённый Promise, цепочка завершится этой новой ошибкой.

Каждый из этих методов возвращает новый Promise, не изменяя исходный. Это позволяет строить цепочки.

#### Цепочка Promise

Результат одного обработчика передаётся следующему:

```js
loadUser()
  .then((user) => loadPosts(user.id))
  .then((posts) => renderPosts(posts))
  .catch((error) => showError(error))
```

Правила цепочки:

- обычное возвращённое значение становится успешным результатом следующего Promise;
- возвращённый Promise ожидается;
- `throw` превращается в отклонение следующего Promise;
- если нужный обработчик пропущен, значение или ошибка проходят дальше без изменения;
- `catch` может восстановить цепочку, если вернёт обычное значение.

```js
Promise.resolve(2)
  .then((number) => number * 3)
  .then((number) => delay(1000).then(() => number + 1))
  .then((number) => console.log(number)) // 7
  .catch((error) => console.error(error))
```

Если забыть `return` перед асинхронной операцией внутри `then`, следующая часть цепочки не будет её ждать:

```js
loadUser()
  .then((user) => {
    loadPosts(user.id) // Ошибка: Promise не возвращён.
  })
  .then((posts) => {
    console.log(posts) // undefined
  })

// Правильно:
loadUser()
  .then((user) => loadPosts(user.id))
  .then((posts) => console.log(posts))
```

#### Статические методы Promise

| Метод | Результат |
| --- | --- |
| `Promise.resolve(value)` | создаёт успешно завершённый Promise; если передан Promise, принимает его итоговый результат |
| `Promise.reject(error)` | создаёт отклонённый Promise |

`resolve()` и `reject()` полезны, когда нужно явно получить уже завершённый Promise. Методы для одновременной работы с несколькими Promise рассматриваются ниже вместе со сценариями их применения.

### `async` и `await`

`async/await` — синтаксис для работы с Promise. Он позволяет записывать последовательный асинхронный код почти как обычный синхронный.

#### Для чего нужен `async`

Ключевое слово `async` объявляет асинхронную функцию. Такая функция всегда возвращает Promise:

```js
async function getNumber() {
  return 42
}

getNumber().then((number) => console.log(number)) // 42
```

Обычное возвращённое значение становится fulfilled Promise, а выброшенная ошибка — rejected Promise:

```js
async function fail() {
  throw new Error('Не удалось получить данные')
}

fail().catch((error) => console.error(error.message))
```

Вызов `async`-функции начинается синхронно и выполняется до первого встреченного `await`. Само слово `async` не переносит тяжёлые вычисления в другой поток и не защищает интерфейс от блокировки.

#### Для чего нужен `await`

`await` приостанавливает выполнение текущей `async`-функции до получения результата, но не блокирует весь JavaScript и event loop:

```js
async function showProfile() {
  const profile = await loadProfile()
  renderProfile(profile)
}
```

Если Promise успешно завершён, выражение `await` возвращает его значение. Если Promise отклонён, `await` выбрасывает причину отклонения — её можно перехватить через `try...catch`.

#### Что может стоять справа от `await`

Справа может находиться любое выражение:

```js
const user = await loadUser()
const value = await 42
const result = await getThenable() // thenable — любой объект с методом then()
```

Обычное значение ведёт себя как `Promise.resolve(value)`. Поэтому ожидать его разрешено, но обычно бессмысленно. Чаще всего справа стоит вызов функции, возвращающей Promise.

`await` используется внутри `async`-функции. На верхнем уровне он также доступен в JavaScript-модулях, но не в обычном классическом скрипте.

### Параллельное выполнение

Если операции не зависят друг от друга, их можно запустить вместе:

```js
const [users, roles] = await Promise.all([
  fetchUsers(),
  fetchRoles(),
])
```

`Promise.all` сохраняет порядок входных элементов независимо от порядка завершения. Пустой набор даёт `[]`. При первой ошибке итоговый Promise отклоняется, но уже запущенные операции автоматически не отменяются.

Когда важен результат каждой операции, включая ошибки, используют `Promise.allSettled`:

```js
const results = await Promise.allSettled([
  loadUser(),
  loadPosts(),
])

// Элементы имеют вид:
// { status: 'fulfilled', value: ... }
// { status: 'rejected', reason: ... }
```

`Promise.race` принимает результат или ошибку первого завершившегося участника. Например, с его помощью можно ограничить время ожидания:

```js
const timeout = new Promise((resolve, reject) => {
  setTimeout(() => reject(new Error('Превышено время ожидания')), 3000)
})

const data = await Promise.race([
  loadData(),
  timeout,
])
```

`race` не отменяет проигравшие операции. Более того, `Promise.race([])` навсегда остаётся в состоянии `pending`.

`Promise.any` похож на гонку только успешных результатов: отклонения пропускаются, пока остаётся шанс на успех. Если все участники отклонены или набор пуст, итогом будет `AggregateError`.

Независимые операции не следует без причины ожидать последовательно.

### Event loop

После завершения текущего синхронного кода выполняются microtasks (`Promise.then`, продолжение после `await`), затем среда может взять следующую задачу, например таймер или событие:

```js
console.log('A')
setTimeout(() => console.log('B'), 0)
Promise.resolve().then(() => console.log('C'))
console.log('D')

// A, D, C, B
```

`queueMicrotask(callback)` явно добавляет callback в очередь микрозадач:

```js
queueMicrotask(() => console.log('microtask'))
```

Не создавайте бесконечную цепочку микрозадач: она не даст браузеру перейти к обработке событий и отрисовке.

Долгие синхронные вычисления блокируют интерфейс. Их разбивают на части, переносят в Web Worker или выполняют на сервере.

## Частые ошибки

- Забытый `return` перед Promise внутри `then` → следующий `then` получает `undefined` и не ждёт операцию → возвращать Promise из обработчика или писать стрелку без фигурных скобок.
- Забытый `await` перед вызовом `async`-функции → в переменной лежит Promise вместо данных, `user.name` равен `undefined`, а отклонение не попадает в `try...catch` → ставить `await` или явно обрабатывать Promise через `.then()` и `.catch()`.
- Последовательное ожидание независимых операций (`await loadUsers(); await loadRoles()`) → общее время равно сумме, а не максимуму → запускать вместе через `Promise.all()`.
- Promise без обработчика ошибки → `Unhandled promise rejection` в консоли, приложение не узнаёт о сбое → завершать цепочку `.catch()` или оборачивать `await` в `try...catch`.
- `new Promise` вокруг функции, которая уже возвращает Promise → лишняя обёртка, в которой легко потерять `reject` → возвращать существующий Promise напрямую.
- Долгое синхронное вычисление внутри `async`-функции → интерфейс всё равно замирает, `async` не переносит работу в другой поток → разбить вычисление на части или вынести в Web Worker.

## Когда не использовать

Если функция не ждёт внешнюю операцию — таймер, сеть, файл, событие, — делать её `async` незачем: она станет возвращать Promise, и каждому вызывающему придётся писать `await`. Синхронные вычисления и преобразования данных остаются обычными функциями.

Для тяжёлых вычислений асинхронность не помогает: `await` не освобождает стек от работы, которая уже идёт. Такие задачи переносят в Web Worker или на сервер. Для потока событий — клики, сообщения WebSocket, — одиночный Promise не подходит, потому что завершается один раз: нужны обработчики [событий](events.md) или `EventTarget`.

## Связанные темы

- [HTTP-запросы: Fetch и Axios](requests.md) — `fetch` как основной источник Promise
- [Ошибки и отладка](errors.md) — обработка отклонённых Promise и забытый `await`
- [Функции и области видимости](functions.md) — callbacks и замыкания, на которых строится асинхронный код
- [WebSocket](websocket.md) — поток событий вместо одиночного ответа
