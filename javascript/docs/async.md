# Асинхронность

JavaScript выполняет пользовательский код в одном стеке вызовов. Среда выполнения обрабатывает таймеры, сеть и другие операции, а готовые callbacks ставит в очереди event loop.

## Promise

Promise находится в одном из состояний: pending, fulfilled или rejected.

```js
fetch('/api/users')
  .then((response) => {
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    return response.json()
  })
  .then((users) => console.log(users))
  .catch((error) => console.error(error))
  .finally(() => hideLoader())
```

## `async` и `await`

`async`-функция всегда возвращает Promise. `await` приостанавливает только эту функцию, а не весь поток:

```js
async function loadUsers() {
  const response = await fetch('/api/users')

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }

  return response.json()
}
```

`fetch` отклоняет Promise при сетевой ошибке или отмене, но не из-за статуса `404` или `500`, поэтому `response.ok` нужно проверять отдельно.

## Параллельное выполнение

```js
const [users, roles] = await Promise.all([
  fetchUsers(),
  fetchRoles(),
])
```

- `Promise.all` завершается ошибкой при первом отклонении;
- `Promise.allSettled` ждёт все результаты;
- `Promise.race` возвращает первый завершившийся Promise;
- `Promise.any` возвращает первый успешно выполненный Promise.

Независимые операции не следует без причины ожидать последовательно.

## Event loop

После завершения текущего синхронного кода выполняются microtasks (`Promise.then`, продолжение после `await`), затем среда может взять следующую задачу, например таймер или событие:

```js
console.log('A')
setTimeout(() => console.log('B'), 0)
Promise.resolve().then(() => console.log('C'))
console.log('D')

// A, D, C, B
```

Долгие синхронные вычисления блокируют интерфейс. Их разбивают на части, переносят в Web Worker или выполняют на сервере.

## Отмена

```js
const controller = new AbortController()

fetch('/api/report', { signal: controller.signal })
controller.abort()
```

`AbortSignal` стоит передавать по цепочке вызываемых функций, чтобы отмена действительно доходила до операции.
