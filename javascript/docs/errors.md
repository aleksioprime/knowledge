# Ошибки и отладка

## Обработка ошибок

```js
class ValidationError extends Error {
  constructor(message, field) {
    super(message)
    this.name = 'ValidationError'
    this.field = field
  }
}

try {
  const user = await loadUser(id)
  renderUser(user)
} catch (error) {
  if (error instanceof ValidationError) {
    showFieldError(error.field, error.message)
  } else {
    console.error(error)
    showGenericError()
  }
} finally {
  hideLoader()
}
```

Перехватывайте ошибку там, где можете восстановиться, добавить полезный контекст или показать корректное состояние интерфейса. Не оставляйте пустой `catch`: он скрывает причину сбоя.

## Синхронные и асинхронные ошибки

```js
try {
  await riskyOperation()
} catch (error) {
  // обработает rejected Promise
}
```

Если забыть `await`, окружающий `try...catch` не перехватит позднее отклонение Promise. Promise нужно вернуть, ожидать или явно обработать через `.catch()`.

## Отладка

- изучайте stack trace с первой относящейся к проекту строки;
- используйте breakpoints и пошаговое выполнение в DevTools;
- смотрите вкладки Network, Console и Sources;
- применяйте `console.table` для коллекций и `console.trace` для стека;
- воспроизводите ошибку на минимальном наборе входных данных;
- не выводите пароли, токены и персональные данные в production-логи.

## Частые источники ошибок

- обращение к свойству `null` или `undefined`;
- потеря контекста `this`;
- изменение общего объекта или массива;
- забытый `await`;
- последовательное ожидание независимых операций;
- сравнение объектов по ссылке вместо сравнения нужных полей;
- использование пользовательских данных в `innerHTML`.
